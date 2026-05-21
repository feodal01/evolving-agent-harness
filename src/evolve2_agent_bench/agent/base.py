from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from evolve2_agent_bench.agent.actions import (
    AgentAction,
    FinishArgs,
    ReadFileArgs,
    ShellArgs,
    WriteFileArgs,
)
from evolve2_agent_bench.agent.tools import WorkspaceTools
from evolve2_agent_bench.config import OpenRouterConfig
from evolve2_agent_bench.mlflow_tracing import mlflow_span, truncate_for_span
from evolve2_agent_bench.trace import RunTraces

# OpenRouter / proxies occasionally return truncated or non-JSON bodies; LangChain's
# HTTP stack surfaces that as JSONDecodeError inside ChatOpenAI.invoke before our
# action parser runs. Retry here so long benchmark runs are not aborted by one bad chunk.
LLM_TRANSPORT_MAX_ATTEMPTS = 8
LLM_TRANSPORT_BACKOFF_CAP_S = 8.0


def _exception_chain_contains(exc: BaseException, target: type | tuple[type, ...]) -> bool:
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, target):
            return True
        cur = cur.__cause__ or cur.__context__
    return False


def _is_retryable_llm_transport(exc: BaseException) -> bool:
    if _exception_chain_contains(exc, json.JSONDecodeError):
        return True
    try:
        import httpx
    except ImportError:
        httpx = None  # type: ignore[assignment]
    if httpx is not None:
        if _exception_chain_contains(
            exc,
            (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.ReadError,
                httpx.RemoteProtocolError,
            ),
        ):
            return True
    try:
        import openai
    except ImportError:
        openai = None  # type: ignore[assignment]
    if openai is not None:
        if _exception_chain_contains(
            exc,
            (openai.APITimeoutError, openai.APIConnectionError),
        ):
            return True
    return False


SYSTEM_PROMPT = """You are a baseline SWE-bench coding agent.

You work inside a checked-out git repository. Fix the issue with the smallest correct patch.

Return exactly one JSON object per turn, with no markdown:
{
  "thought": "brief reasoning",
  "action": "run_shell" | "read_file" | "write_file" | "finish",
  "args": {...}
}

Actions:
- run_shell args: {"command": "rg ..."} or tests/edit commands.
- read_file args: {"path": "relative/path.py", "start_line": 1, "max_lines": 200}
- write_file args: {"path": "relative/path.py", "content": "full new file content"}
- finish args: {"summary": "what changed and what was tested"}

Prefer rg, sed, python scripts, and focused tests. Inspect before editing. Keep the patch minimal.
"""


@dataclass(frozen=True)
class AgentResult:
    summary: str
    iterations: int


class BaselineLangChainAgent:
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
            max_retries=6,
            default_headers={
                "HTTP-Referer": "http://localhost/evolve2",
                "X-Title": "evolve2-agent-bench",
            },
            **model_kwargs,
        )

    def run(self, workspace: Path, task: dict[str, Any], max_iterations: int) -> AgentResult:
        tools = WorkspaceTools(root=workspace, traces=self.traces)
        conversation: list[str] = [
            "SWE-bench task:",
            f"instance_id: {task['instance_id']}",
            f"repo: {task['repo']}",
            "problem_statement:",
            task["problem_statement"],
        ]
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

            final_iterations = max_iterations
            final_summary = ""
            terminal = False

            for iteration in range(1, max_iterations + 1):
                with mlflow_span(
                    f"agent_iteration_{iteration}",
                    "AGENT",
                    attributes={"iteration": iteration},
                ) as iter_span:
                    user_content = "\n\n".join(conversation)
                    raw = self._invoke(iteration, user_content)
                    try:
                        with mlflow_span("parse_agent_json_action", "PARSER") as parse_span:
                            action = self._parse_action(raw)
                            if parse_span is not None:
                                parse_span.set_inputs(truncate_for_span({"raw_response": raw}))
                                parse_span.set_outputs(
                                    truncate_for_span(
                                        {
                                            "thought": action.thought,
                                            "action": action.action,
                                            "args": action.args.model_dump(),
                                        }
                                    )
                                )
                    except (json.JSONDecodeError, ValidationError) as exc:
                        self.traces.append_agent(
                            "invalid_action",
                            {"iteration": iteration, "error": str(exc), "raw": raw},
                        )
                        if iter_span is not None:
                            iter_span.set_outputs(
                                truncate_for_span({"invalid_action": True, "error": str(exc)})
                            )
                        conversation.append(
                            "Your previous response was invalid. Return exactly one valid JSON object "
                            "matching the action schema."
                        )
                        continue

                    self.traces.append_agent(
                        "agent_action",
                        {
                            "iteration": iteration,
                            "thought": action.thought,
                            "action": action.action,
                            "action_args": action.args.model_dump(),
                        },
                    )
                    finish_blocked = False
                    blocked_summary = ""
                    finish_args: FinishArgs | None = None
                    if action.action == "finish":
                        args = action.args
                        if not isinstance(args, FinishArgs):
                            raise TypeError("finish action received non-finish args")
                        finish_args = args
                        if not self._has_tracked_source_diff(workspace):
                            finish_blocked = True
                            blocked_summary = (
                                "Finish blocked: no tracked source diff under src/ yet. "
                                "Edit source files before trying finish again."
                            )
                            self.traces.append_agent(
                                "agent_finish_blocked",
                                {"iteration": iteration, "summary": blocked_summary},
                            )
                            result = {"ok": False, "output": blocked_summary}
                        else:
                            self.traces.append_agent(
                                "agent_finish",
                                {"iteration": iteration, "summary": args.summary},
                            )
                            result = {"ok": True, "output": args.summary}
                    else:
                        result = self._execute(tools, action)
                    self.traces.append_agent(
                        "agent_observation",
                        {
                            "iteration": iteration,
                            "action": action.action,
                            "ok": result["ok"],
                            "observation": result["output"],
                        },
                    )
                    if iter_span is not None:
                        iter_span.set_outputs(
                            truncate_for_span(
                                {
                                    "action": action.action,
                                    "ok": result["ok"],
                                    "observation_preview": result["output"],
                                }
                            )
                        )
                    conversation.append(
                        json.dumps(
                            {
                                "iteration": iteration,
                                "action": action.action,
                                "ok": result["ok"],
                                "observation": result["output"],
                            },
                            ensure_ascii=False,
                        )
                    )
                    if finish_blocked:
                        continue
                    if action.action == "finish":
                        assert finish_args is not None
                        final_summary = finish_args.summary
                        final_iterations = iteration
                        terminal = True
                        break

            if not terminal:
                final_summary = f"Stopped after {max_iterations} iterations without finish action."
                self.traces.append_agent("agent_stop", {"summary": final_summary})

            if root_span is not None:
                root_span.set_outputs(
                    truncate_for_span(
                        {
                            "summary": final_summary,
                            "iterations": final_iterations,
                            "finished_normally": terminal,
                        }
                    )
                )

            return AgentResult(summary=final_summary, iterations=final_iterations)

    def _invoke(self, iteration: int, user_content: str) -> str:
        messages_lc = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_content)]
        with mlflow_span(
            "chat_openai_invoke",
            "CHAT_MODEL",
            attributes={"iteration": iteration, "model": self.config.model},
        ) as sp:
            started = time.monotonic()
            response = None
            last_exc: BaseException | None = None
            transport_retries = 0
            for attempt in range(1, LLM_TRANSPORT_MAX_ATTEMPTS + 1):
                try:
                    response = self.llm.invoke(messages_lc)
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
                    if not _is_retryable_llm_transport(exc):
                        raise
                    if attempt >= LLM_TRANSPORT_MAX_ATTEMPTS:
                        break
                    transport_retries += 1
                    self.traces.append_llm(
                        "llm_transport_retry",
                        {
                            "iteration": iteration,
                            "attempt": attempt,
                            "max_attempts": LLM_TRANSPORT_MAX_ATTEMPTS,
                            "model": self.config.model,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                    )
                    delay = min(LLM_TRANSPORT_BACKOFF_CAP_S, 0.25 * (2 ** (attempt - 1)))
                    time.sleep(delay)

            elapsed = time.monotonic() - started

            if response is None:
                assert last_exc is not None
                err_summary = {
                    "iteration": iteration,
                    "model": self.config.model,
                    "error": str(last_exc),
                    "error_type": type(last_exc).__name__,
                    "transport_retries": transport_retries,
                    "elapsed_seconds": round(elapsed, 3),
                }
                if sp is not None:
                    sp.set_inputs(
                        truncate_for_span(
                            {
                                "messages": [
                                    {"role": "system", "content": SYSTEM_PROMPT},
                                    {"role": "user", "content": user_content},
                                ]
                            }
                        )
                    )
                    sp.set_outputs(truncate_for_span({"transport_failed": True, **err_summary}))
                self.traces.append_llm("llm_invoke_transport_failed", err_summary)
                return ""

            content = str(response.content)
            usage = response.response_metadata.get("token_usage") or response.response_metadata.get(
                "usage"
            )
            if sp is not None:
                sp.set_inputs(
                    truncate_for_span(
                        {
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": user_content},
                            ]
                        }
                    )
                )
                sp.set_outputs(
                    truncate_for_span(
                        {
                            "response": content,
                            "usage": usage,
                            "elapsed_seconds": round(elapsed, 3),
                            "transport_retries": transport_retries,
                        }
                    )
                )
            self.traces.append_llm(
                "llm_call",
                {
                    "iteration": iteration,
                    "model": self.config.model,
                    "elapsed_seconds": round(elapsed, 3),
                    "usage": usage,
                    "transport_retries": transport_retries,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    "response": content,
                },
            )
            return content.strip()

    def _parse_action(self, raw: str) -> AgentAction:
        for start, end in _json_object_spans(raw):
            candidate = raw[start:end]
            try:
                return AgentAction.model_validate(json.loads(candidate))
            except (json.JSONDecodeError, ValidationError):
                continue
        return AgentAction.model_validate(json.loads(raw))

    def _execute(self, tools: WorkspaceTools, action: AgentAction) -> dict[str, Any]:
        span_name = f"tool_{action.action}"
        args_dump = truncate_for_span(action.args.model_dump())
        with mlflow_span(span_name, "TOOL", attributes={"action": action.action}) as tsp:
            if tsp is not None:
                tsp.set_inputs(args_dump)
            if action.action == "run_shell":
                args = action.args
                if not isinstance(args, ShellArgs):
                    raise TypeError("run_shell action received non-shell args")
                result = tools.run_shell(args.command)
            elif action.action == "read_file":
                args = action.args
                if not isinstance(args, ReadFileArgs):
                    raise TypeError("read_file action received non-read args")
                result = tools.read_file(args.path, args.start_line, args.max_lines)
            elif action.action == "write_file":
                args = action.args
                if not isinstance(args, WriteFileArgs):
                    raise TypeError("write_file action received non-write args")
                result = tools.write_file(args.path, args.content)
            elif action.action == "finish":
                args = action.args
                if not isinstance(args, FinishArgs):
                    raise TypeError("finish action received non-finish args")
                result = type("FinishResult", (), {"ok": True, "output": args.summary})()
            else:
                raise ValueError(f"Unknown action: {action.action}")
            out = {"ok": result.ok, "output": result.output}
            if tsp is not None:
                tsp.set_outputs(truncate_for_span(out))
            return out

    def _has_tracked_source_diff(self, workspace: Path) -> bool:
        proc = subprocess.run(
            ["git", "-C", str(workspace), "diff", "--name-only", "--", "src"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "Failed to inspect tracked source diff: "
                f"returncode={proc.returncode}, stderr={proc.stderr.strip()}"
            )
        return any(line.strip() for line in proc.stdout.splitlines())


def _json_object_spans(raw: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    depth = 0
    start: int | None = None
    in_string = False
    escape = False
    for index, char in enumerate(raw):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    spans.append((start, index + 1))
                    start = None
    return spans
