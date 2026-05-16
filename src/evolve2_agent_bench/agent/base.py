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
from evolve2_agent_bench.trace import RunTraces


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

The benchmark patch is `git diff` on tracked files; untracked files alone do not count. Use write_file on existing repo paths for real edits.
"""

# Consecutive validParsed turns with empty `git diff` before injecting a control hint (H0005-style progress nudge).
_NO_PATCH_EMPTY_DIFF_ROUNDS = 3
# Consecutive invalid JSON parses before emitting an expanded argument template (bounded retry cue).
_INVALID_PARSE_STREAK_CAP = 3

_INVALID_JSON_TEMPLATE_REMINDER = """\
Repeated parse failures: reply with exactly one JSON object, no markdown fence. Minimal valid shapes:

{"thought":"why","action":"run_shell","args":{"command":"rg -n pattern src"}}

{"thought":"why","action":"read_file","args":{"path":"pkg/module.py","start_line":1,"max_lines":200}}

{"thought":"why","action":"write_file","args":{"path":"pkg/module.py","content":"full file text"}}

{"thought":"why","action":"finish","args":{"summary":"what changed and tests run"}}
"""

_NO_PATCH_CONTROL_HINT = """\
Control hint: `git diff` has stayed empty across several turns. Next action must apply a tracked source or test edit via write_file on an existing file path (not scratch/untracked-only work), then run a minimal targeted check.
"""


def _tracked_git_diff_snapshot(workspace: Path) -> tuple[bool, str]:
    """Return (diff_empty, shortstat_or_placeholder_for_model).

    Empty stdout from `git diff --shortstat` means no tracked unstaged diff (matches patch extraction).
    """
    proc = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--shortstat"],
        cwd=str(workspace.resolve()),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        return False, f"(git diff unavailable: {err[:400]})"
    stat = proc.stdout.strip()
    return stat == "", stat or "(no staged/unstaged diff)"


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

        invalid_parse_streak = 0
        empty_diff_rounds = 0

        for iteration in range(1, max_iterations + 1):
            user_content = "\n\n".join(conversation)
            raw = self._invoke(iteration, user_content)
            try:
                action = self._parse_action(raw)
            except (json.JSONDecodeError, ValidationError) as exc:
                invalid_parse_streak += 1
                self.traces.append_agent(
                    "invalid_action",
                    {
                        "iteration": iteration,
                        "error": str(exc),
                        "raw": raw,
                        "invalid_parse_streak": invalid_parse_streak,
                    },
                )
                conversation.append(
                    "Your previous response was invalid. Return exactly one valid JSON object "
                    "matching the action schema."
                )
                if invalid_parse_streak >= _INVALID_PARSE_STREAK_CAP:
                    conversation.append(_INVALID_JSON_TEMPLATE_REMINDER)
                    invalid_parse_streak = 0
                continue

            invalid_parse_streak = 0

            self.traces.append_agent(
                "agent_action",
                {
                    "iteration": iteration,
                    "thought": action.thought,
                    "action": action.action,
                    "action_args": action.args.model_dump(),
                },
            )

            if action.action == "finish":
                diff_empty, shortstat = _tracked_git_diff_snapshot(workspace)
                if diff_empty:
                    empty_diff_rounds += 1
                    self.traces.append_agent(
                        "finish_rejected_empty_diff",
                        {
                            "iteration": iteration,
                            "git_diff_shortstat": shortstat,
                            "tracked_git_diff_empty": True,
                            "empty_diff_rounds": empty_diff_rounds,
                        },
                    )
                    conversation.append(
                        json.dumps(
                            {
                                "iteration": iteration,
                                "event": "finish_rejected_empty_diff",
                                "detail": "finish not allowed while git diff is empty; edit tracked files first.",
                                "tracked_git_diff_empty": True,
                                "git_diff_shortstat": shortstat,
                            },
                            ensure_ascii=False,
                        )
                    )
                    if empty_diff_rounds >= _NO_PATCH_EMPTY_DIFF_ROUNDS:
                        self.traces.append_agent(
                            "no_patch_control_hint",
                            {"iteration": iteration, "empty_diff_rounds": empty_diff_rounds},
                        )
                        conversation.append(_NO_PATCH_CONTROL_HINT)
                        empty_diff_rounds = 0
                    continue

            result = self._execute(tools, action)
            diff_empty, shortstat = _tracked_git_diff_snapshot(workspace)
            obs_payload = {
                "iteration": iteration,
                "action": action.action,
                "ok": result["ok"],
                "observation": result["output"],
                "tracked_git_diff_empty": diff_empty,
                "git_diff_shortstat": shortstat,
            }
            self.traces.append_agent("agent_observation", obs_payload)
            conversation.append(json.dumps(obs_payload, ensure_ascii=False))

            if diff_empty:
                empty_diff_rounds += 1
            else:
                empty_diff_rounds = 0

            if empty_diff_rounds >= _NO_PATCH_EMPTY_DIFF_ROUNDS:
                self.traces.append_agent(
                    "no_patch_control_hint",
                    {"iteration": iteration, "empty_diff_rounds": empty_diff_rounds},
                )
                conversation.append(_NO_PATCH_CONTROL_HINT)
                empty_diff_rounds = 0

            if action.action == "finish":
                args = action.args
                if not isinstance(args, FinishArgs):
                    raise TypeError("finish action received non-finish args")
                self.traces.append_agent(
                    "agent_finish",
                    {"iteration": iteration, "summary": args.summary},
                )
                return AgentResult(summary=args.summary, iterations=iteration)

        summary = f"Stopped after {max_iterations} iterations without finish action."
        self.traces.append_agent("agent_stop", {"summary": summary})
        return AgentResult(summary=summary, iterations=max_iterations)

    def _invoke(self, iteration: int, user_content: str) -> str:
        started = time.monotonic()
        response = self.llm.invoke(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_content)]
        )
        elapsed = time.monotonic() - started
        content = str(response.content)
        usage = response.response_metadata.get("token_usage") or response.response_metadata.get("usage")
        self.traces.append_llm(
            "llm_call",
            {
                "iteration": iteration,
                "model": self.config.model,
                "elapsed_seconds": round(elapsed, 3),
                "usage": usage,
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
        return {"ok": result.ok, "output": result.output}


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
