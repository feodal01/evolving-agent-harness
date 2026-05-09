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

        shell_command_counts: dict[str, int] = {}
        for iteration in range(1, max_iterations + 1):
            user_content = "\n\n".join(conversation)
            raw = self._invoke(iteration, user_content)
            try:
                action = self._parse_action(raw)
            except (json.JSONDecodeError, ValidationError) as exc:
                self.traces.append_agent(
                    "invalid_action",
                    {"iteration": iteration, "error": str(exc), "raw": raw},
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
            result = self._execute(tools, action)
            repeat_count = _record_shell_repeat(action, shell_command_counts)
            observation_payload = _build_observation_payload(
                workspace=workspace,
                iteration=iteration,
                action=action.action,
                ok=result["ok"],
                output=result["output"],
                shell_repeat_count=repeat_count,
            )
            self.traces.append_agent("agent_observation", observation_payload)
            conversation.append(json.dumps(observation_payload, ensure_ascii=False))
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


def _record_shell_repeat(action: AgentAction, command_counts: dict[str, int]) -> int | None:
    if action.action != "run_shell":
        return None
    args = action.args
    if not isinstance(args, ShellArgs):
        raise TypeError("run_shell action received non-shell args")
    command_counts[args.command] = command_counts.get(args.command, 0) + 1
    return command_counts[args.command]


def _build_observation_payload(
    *,
    workspace: Path,
    iteration: int,
    action: str,
    ok: bool,
    output: str,
    shell_repeat_count: int | None,
) -> dict[str, Any]:
    patch_status = _workspace_patch_status(workspace)
    payload: dict[str, Any] = {
        "iteration": iteration,
        "action": action,
        "ok": ok,
        "observation": output,
        "patch_status": patch_status,
    }
    if shell_repeat_count is not None:
        payload["shell_repeat_count"] = shell_repeat_count
        if shell_repeat_count > 1:
            payload["repeat_note"] = (
                "This exact shell command has already run. Prefer a different evidence-gathering "
                "step or edit a tracked source file."
            )
    if (
        action != "finish"
        and iteration >= 3
        and patch_status.get("tracked_patch_bytes") == 0
    ):
        payload["progress_hint"] = (
            "No tracked patch exists yet. If localization evidence is sufficient, inspect or edit "
            "tracked source/test files instead of continuing reproduction."
        )
    return payload


def _workspace_patch_status(workspace: Path) -> dict[str, Any]:
    diff = _run_git_status_command(
        workspace,
        ["diff", "--no-ext-diff", "--binary"],
        timeout_seconds=30,
    )
    shortstat = _run_git_status_command(
        workspace,
        ["diff", "--shortstat"],
        timeout_seconds=10,
    )
    status = _run_git_status_command(
        workspace,
        ["status", "--short"],
        timeout_seconds=10,
    )
    if diff.returncode != 0 or shortstat.returncode != 0 or status.returncode != 0:
        return {
            "ok": False,
            "error": "\n".join(
                message
                for message in (diff.stderr, shortstat.stderr, status.stderr)
                if message
            ).strip()
            or "git status command failed",
        }

    status_lines = [line for line in status.stdout.splitlines() if line.strip()]
    tracked_files = [
        line[3:] if len(line) > 3 else line
        for line in status_lines
        if not line.startswith("?? ")
    ]
    untracked_files = [
        line[3:] if len(line) > 3 else line
        for line in status_lines
        if line.startswith("?? ")
    ]
    return {
        "ok": True,
        "tracked_patch_bytes": len(diff.stdout.encode("utf-8")),
        "tracked_diff_shortstat": shortstat.stdout.strip(),
        "tracked_changed_files": tracked_files[:20],
        "tracked_changed_file_count": len(tracked_files),
        "untracked_file_count": len(untracked_files),
        "untracked_files_preview": untracked_files[:10],
    }


def _run_git_status_command(
    workspace: Path, args: list[str], timeout_seconds: int
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=workspace,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            args=["git", *args],
            returncode=124,
            stdout=exc.stdout or "",
            stderr=f"git {' '.join(args)} timed out after {timeout_seconds} seconds",
        )


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
