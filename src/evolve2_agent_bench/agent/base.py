"""LangChain ReAct coding agent for SWE-bench tasks.

Uses ``langchain.agents.create_agent`` with workspace-scoped tools
(shell, read_file, write_file). All LLM calls, tool invocations, and agent
lifecycle events are recorded to both JSONL traces and MLflow spans.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from evolve2_agent_bench.agent.callbacks import AgentTraceCallback
from evolve2_agent_bench.agent.tools import make_workspace_tools
from evolve2_agent_bench.config import OpenRouterConfig
from evolve2_agent_bench.mlflow_tracing import mlflow_span, truncate_for_span
from evolve2_agent_bench.trace import RunTraces

SYSTEM_PROMPT = """You are a SWE-bench coding agent working inside a checked-out git repository.

Your goal: fix the reported issue with the smallest correct patch.

Strategy:
1. Understand the issue thoroughly by reading the problem statement.
2. Search the codebase to locate relevant files and understand the code structure.
3. Read the specific files and functions involved.
4. Make targeted edits to fix the issue.
5. Run existing tests to verify your fix does not break anything.
6. When confident, stop working.

Guidelines:
- Prefer rg (ripgrep) for code search — it is fast and precise.
- Use sed or python scripts for targeted edits rather than rewriting whole files.
- Run focused tests related to your change, not the entire test suite.
- Keep your patch minimal: change only what is necessary to fix the issue.
- Inspect before editing. Read the code you plan to modify.
- If tests fail after your edit, read the failure output carefully and iterate.
"""

LLM_MAX_RETRIES = 6


@dataclass(frozen=True)
class AgentResult:
    summary: str
    iterations: int


class ReActCodingAgent:
    """LangGraph ReAct agent with workspace tools and full observability."""

    def __init__(
        self,
        config: OpenRouterConfig,
        traces: RunTraces,
        max_tokens: int | None,
    ) -> None:
        self.config = config
        self.traces = traces
        model_kwargs: dict[str, Any] = {}
        if max_tokens is not None:
            model_kwargs["max_tokens"] = max_tokens
        self.llm = ChatOpenAI(
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
            temperature=0,
            max_retries=LLM_MAX_RETRIES,
            default_headers={
                "HTTP-Referer": "http://localhost/evolve2",
                "X-Title": "evolve2-agent-bench",
            },
            **model_kwargs,
        )

    def run(self, workspace: Path, task: dict[str, Any], max_iterations: int) -> AgentResult:
        callback = AgentTraceCallback(traces=self.traces)
        tools = make_workspace_tools(root=workspace, traces=self.traces)

        agent = create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
        )

        user_message = (
            f"SWE-bench task:\n"
            f"instance_id: {task['instance_id']}\n"
            f"repo: {task['repo']}\n"
            f"problem_statement:\n{task['problem_statement']}"
        )

        with mlflow_span(
            "coding_agent_session",
            "WORKFLOW",
            attributes={
                "instance_id": task["instance_id"],
                "repo": task["repo"],
                "base_commit": task.get("base_commit", ""),
            },
        ) as root_span:
            if root_span is not None:
                root_span.set_inputs(
                    truncate_for_span(
                        {
                            "workspace": str(workspace),
                            "problem_statement": task["problem_statement"],
                            "max_iterations": max_iterations,
                        }
                    )
                )

            self.traces.append_agent(
                "agent_start",
                {
                    "workspace": str(workspace),
                    "instance_id": task["instance_id"],
                    "max_iterations": max_iterations,
                    "input": {
                        "repo": task["repo"],
                        "base_commit": task["base_commit"],
                        "problem_statement": task["problem_statement"],
                    },
                },
            )

            started = time.monotonic()
            config = {
                "recursion_limit": max_iterations * 2,
                "callbacks": [callback],
            }

            try:
                result = agent.invoke(
                    {"messages": [HumanMessage(content=user_message)]},
                    config=config,
                )
                messages = result.get("messages", [])
                final_content = messages[-1].content if messages else ""
                final_summary = (
                    final_content[:2000] if isinstance(final_content, str) else str(final_content)[:2000]
                )
            except Exception as exc:
                final_summary = f"Agent error: {type(exc).__name__}: {exc}"
                self.traces.append_agent("agent_error", {"error": final_summary})

            elapsed = time.monotonic() - started
            iterations = callback.iteration

            self.traces.append_agent(
                "agent_finish",
                {
                    "iterations": iterations,
                    "summary": final_summary,
                    "elapsed_seconds": round(elapsed, 3),
                },
            )

            if root_span is not None:
                root_span.set_outputs(
                    truncate_for_span(
                        {
                            "summary": final_summary,
                            "iterations": iterations,
                            "elapsed_seconds": round(elapsed, 3),
                        }
                    )
                )

            return AgentResult(summary=final_summary, iterations=iterations)
