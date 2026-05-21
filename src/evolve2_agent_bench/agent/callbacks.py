"""LangChain callback handler that bridges agent events to RunTraces + MLflow."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage

from evolve2_agent_bench.trace import RunTraces

MAX_TRACE_CHARS = 12_000


def _tool_output_text(output: Any) -> str:
    if isinstance(output, str):
        return output
    content = getattr(output, "content", None)
    if content is not None:
        return str(content)
    return str(output)


def _trunc(text: str, limit: int = MAX_TRACE_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n… [truncated]"


class AgentTraceCallback(BaseCallbackHandler):
    """Streams LangChain agent lifecycle events into RunTraces JSONL and MLflow spans."""

    def __init__(self, traces: RunTraces) -> None:
        super().__init__()
        self.traces = traces
        self._iteration = 0
        self._llm_start_times: dict[UUID, float] = {}

    @property
    def iteration(self) -> int:
        return self._iteration

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._iteration += 1
        self._llm_start_times[run_id] = time.monotonic()

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._iteration += 1
        self._llm_start_times[run_id] = time.monotonic()

    def on_llm_end(self, response: Any, *, run_id: UUID, **kwargs: Any) -> None:
        elapsed = time.monotonic() - self._llm_start_times.pop(run_id, time.monotonic())
        generation = response.generations[0][0] if response.generations else None
        content = generation.text if generation else ""
        usage = {}
        if generation and hasattr(generation, "generation_info") and generation.generation_info:
            usage = generation.generation_info.get("token_usage", {})
        if hasattr(response, "llm_output") and response.llm_output:
            usage = usage or response.llm_output.get("token_usage", {})

        self.traces.append_llm(
            "llm_call",
            {
                "iteration": self._iteration,
                "elapsed_seconds": round(elapsed, 3),
                "usage": usage,
                "response": _trunc(content),
            },
        )

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        elapsed = time.monotonic() - self._llm_start_times.pop(run_id, time.monotonic())
        self.traces.append_llm(
            "llm_error",
            {
                "iteration": self._iteration,
                "elapsed_seconds": round(elapsed, 3),
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self.traces.append_agent(
            "agent_action",
            {
                "iteration": self._iteration,
                "action": serialized.get("name", "unknown"),
                "action_args": _trunc(input_str),
            },
        )

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        self.traces.append_agent(
            "agent_observation",
            {
                "iteration": self._iteration,
                "ok": True,
                "observation": _trunc(_tool_output_text(output)),
            },
        )

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self.traces.append_agent(
            "agent_observation",
            {
                "iteration": self._iteration,
                "ok": False,
                "observation": _trunc(str(error)),
            },
        )

    def on_agent_finish(self, finish: Any, *, run_id: UUID, **kwargs: Any) -> None:
        self.traces.append_agent(
            "agent_finish",
            {
                "iteration": self._iteration,
                "summary": _trunc(str(finish.return_values) if hasattr(finish, "return_values") else str(finish)),
            },
        )
