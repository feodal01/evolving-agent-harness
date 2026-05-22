from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evolve2_agent_bench.mlflow_tracing import mlflow_trace_event


def utc_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True)
class JsonlTrace:
    path: Path
    mirror_to_mlflow: bool = True

    def append(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {"ts_ms": utc_ms(), "event": event, **payload}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        if self.mirror_to_mlflow:
            mlflow_trace_event(record)
        return record


@dataclass(frozen=True)
class RunTraces:
    run_dir: Path
    timeline: JsonlTrace
    agent: JsonlTrace
    llm: JsonlTrace
    shell: JsonlTrace

    @classmethod
    def create(cls, run_dir: Path) -> "RunTraces":
        run_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            run_dir=run_dir,
            timeline=JsonlTrace(run_dir / "trace.jsonl"),
            agent=JsonlTrace(run_dir / "agent_events.jsonl", mirror_to_mlflow=False),
            llm=JsonlTrace(run_dir / "llm_calls.jsonl", mirror_to_mlflow=False),
            shell=JsonlTrace(run_dir / "shell_events.jsonl", mirror_to_mlflow=False),
        )

    def append(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.timeline.append(event, payload)

    def append_agent(self, event: str, payload: dict[str, Any]) -> None:
        record = self.append(event, {"stream": "agent", **payload})
        self.agent.append(event, {key: value for key, value in record.items() if key != "stream"})

    def append_llm(self, event: str, payload: dict[str, Any]) -> None:
        record = self.append(event, {"stream": "llm", **payload})
        self.llm.append(event, {key: value for key, value in record.items() if key != "stream"})

    def append_shell(self, event: str, payload: dict[str, Any]) -> None:
        record = self.append(event, {"stream": "tool", "tool_name": "shell", **payload})
        self.shell.append(event, {key: value for key, value in record.items() if key != "stream"})
