from __future__ import annotations

import re
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any

from langchain.tools import tool
from pydantic import Field

from evolve2_agent_bench.mlflow_tracing import mlflow_span, truncate_for_span
from evolve2_agent_bench.trace import RunTraces

MAX_TOOL_OUTPUT = 12_000

_SCRATCH_WRITE_BLOCKED = (
    "\n\nBLOCKED: Writing to untracked files is not allowed. "
    "SWE-bench evaluates your git diff — only edits to existing tracked source files count. "
    "Use `sed -i` to edit an existing tracked file, or write_file on a tracked path. "
    "Run `git ls-files` to see tracked files."
)

_PYTEST_UNAVAILABLE = (
    "\n\npytest is unavailable in this agent shell. Do not retry pytest or pip. "
    "Apply the fix directly with sed -i or write_file on the source file you already read."
)

_NO_EDIT_REMINDER = (
    "\n\nREMINDER: You have read the source code but not edited anything yet. "
    "You MUST apply a fix now using `sed -i` or `write_file`. "
    "Do not write reproduction scripts or run tests — edit the tracked source file."
)

_REPEATED_COMMAND_BREAK = (
    "\n\nSTOP: You have run the same command multiple times without progress. "
    "You are stuck in a loop. Break out by editing the source file now with `sed -i`."
)

_REDIRECT_RE = re.compile(
    r">+\s*"
    r"(?:"
    r'["\']?([\w./-]+\.(?:py|sh|txt|json))["\']?'
    r"|"
    r"['\"]?(\w+\.py)['\"]?"
    r")"
)

_HEREDOC_RE = re.compile(r"<<+\s*['\"]?(\w+)['\"]?\s*")


def _resolve_inside(root: Path, requested: str) -> Path:
    target = (root / requested).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise ValueError(f"Path escapes workspace: {requested}")
    return target


def _truncate(text: str, limit: int = MAX_TOOL_OUTPUT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[output truncated]"


def _is_tracked(root: Path, rel_path: str) -> bool:
    normalized = rel_path.strip().replace("\\", "/").lstrip("./")
    try:
        proc = subprocess.run(
            ["git", "ls-files", "--", normalized],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        return bool(proc.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return True


@contextmanager
def _tool_span(tool_name: str, tool_input: dict[str, Any]):
    with mlflow_span(
        f"tool.{tool_name}",
        "TOOL",
        attributes={"tool_name": tool_name},
    ) as span:
        if span is not None:
            span.set_inputs(truncate_for_span(tool_input))
        yield span


def _set_tool_span_output(span: Any, payload: dict[str, Any]) -> None:
    if span is not None:
        span.set_outputs(truncate_for_span(payload))


def _detect_untracked_write_target(root: Path, command: str) -> str | None:
    for m in _REDIRECT_RE.finditer(command):
        path = m.group(1) or m.group(2)
        if path and not _is_tracked(root, path):
            return path
    return None


class _CommandHistory:
    def __init__(self, max_window: int = 3) -> None:
        self._commands: list[str] = []
        self._max_window = max_window

    def record(self, command: str) -> None:
        self._commands.append(command.strip())
        if len(self._commands) > self._max_window * 2:
            self._commands = self._commands[-self._max_window * 2 :]

    def is_repeated(self) -> bool:
        if len(self._commands) < self._max_window:
            return False
        last = self._commands[-self._max_window :]
        return len(set(last)) == 1


def make_workspace_tools(root: Path, traces: RunTraces) -> list:
    """Build LangChain tool instances bound to a workspace root and trace sink."""
    cmd_history = _CommandHistory()

    @tool
    def run_shell(
        command: Annotated[str, Field(description="Shell command to execute in the repo workspace.")],
        timeout_seconds: Annotated[
            int, Field(default=120, description="Max seconds before the command is killed.")
        ] = 120,
    ) -> str:
        """Execute a shell command in the repository workspace. Use for searching code (rg, grep),
        applying edits (sed -i, patch), and git operations. Do NOT use for creating new files —
        only edit existing tracked source files. Prefer sed -i for targeted edits."""
        tool_input = {"command": command, "timeout_seconds": timeout_seconds}
        with _tool_span("shell", tool_input) as span:
            untracked_target = _detect_untracked_write_target(root, command)
            if untracked_target is not None:
                output = f"BLOCKED: Cannot write to untracked file {untracked_target}." + _SCRATCH_WRITE_BLOCKED
                traces.append(
                    "tool_call",
                    {"stream": "tool", "tool_name": "shell", "tool_input": tool_input},
                )
                payload = {
                    "command": command,
                    "tool_input": tool_input,
                    "tool_output": output,
                    "block_reason": "untracked_write",
                    "blocked_path": untracked_target,
                    "output": output,
                }
                traces.append_shell("shell_command_blocked", payload)
                _set_tool_span_output(span, {"ok": False, **payload})
                return output

            cmd_history.record(command)
            traces.append(
                "tool_call",
                {
                    "stream": "tool",
                    "tool_name": "shell",
                    "tool_input": tool_input,
                },
            )
            started = time.monotonic()
            try:
                proc = subprocess.run(
                    command,
                    cwd=root,
                    shell=True,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                output = f"$ {command}\n\nCommand timed out after {timeout_seconds} seconds."
                payload = {
                    "command": command,
                    "tool_input": tool_input,
                    "tool_output": output,
                    "timeout_seconds": timeout_seconds,
                    "stdout": exc.stdout or "",
                    "stderr": exc.stderr or "",
                    "output": output,
                }
                traces.append_shell("shell_command_timeout", payload)
                _set_tool_span_output(span, {"ok": False, **payload})
                return output

            elapsed = time.monotonic() - started
            output = f"$ {command}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
            if "pytest" in command and (
                "No module named pytest" in output
                or "pytest: command not found" in output
                or "command not found" in (proc.stderr or "")
            ):
                output += _PYTEST_UNAVAILABLE
            if cmd_history.is_repeated():
                output += _REPEATED_COMMAND_BREAK
            truncated = _truncate(output)
            payload = {
                "command": command,
                "tool_input": tool_input,
                "tool_output": truncated,
                "returncode": proc.returncode,
                "elapsed_seconds": round(elapsed, 3),
                "stdout_bytes": len(proc.stdout.encode("utf-8")),
                "stderr_bytes": len(proc.stderr.encode("utf-8")),
                "output": truncated,
            }
            traces.append_shell("shell_command", payload)
            _set_tool_span_output(span, {"ok": proc.returncode == 0, **payload})
            return truncated

    @tool
    def read_file(
        path: Annotated[str, Field(description="Relative file path from the repo root.")],
        start_line: Annotated[
            int, Field(default=1, ge=1, description="1-based starting line number.")
        ] = 1,
        max_lines: Annotated[
            int, Field(default=200, ge=1, le=400, description="Maximum lines to return.")
        ] = 200,
    ) -> str:
        """Read a file from the repository. Returns numbered lines for precise reference.
        Use start_line and max_lines to read specific sections of large files."""
        tool_input = {"path": path, "start_line": start_line, "max_lines": max_lines}
        with _tool_span("read_file", tool_input) as span:
            traces.append(
                "tool_call",
                {"stream": "tool", "tool_name": "read_file", "tool_input": tool_input},
            )
            target = _resolve_inside(root, path)
            if not target.is_file():
                output = f"File not found: {path}"
                payload = {
                    "stream": "tool",
                    "tool_name": "read_file",
                    "ok": False,
                    "tool_input": tool_input,
                    "tool_output": output,
                }
                traces.append("tool_result", payload)
                _set_tool_span_output(span, payload)
                return output

            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
            start = start_line - 1
            selected = lines[start : start + max_lines]
            rendered = "\n".join(
                f"{line_no}: {line}" for line_no, line in enumerate(selected, start=start_line)
            )
            output = _truncate(rendered)
            payload = {
                "stream": "tool",
                "tool_name": "read_file",
                "ok": True,
                "tool_input": tool_input,
                "tool_output": output,
            }
            traces.append("tool_result", payload)
            _set_tool_span_output(span, payload)
            return output

    @tool
    def write_file(
        path: Annotated[str, Field(description="Relative file path from the repo root.")],
        content: Annotated[str, Field(description="Complete new file content.")],
    ) -> str:
        """Write a file in the repository. Overwrites the entire file with the provided content.
        Only works on files that already exist in the repository (tracked by git). New files
        at the repo root are blocked — SWE-bench evaluates your git diff, not new files."""
        tool_input = {
            "path": path,
            "content_bytes": len(content.encode("utf-8")),
            "content_preview": content[:MAX_TOOL_OUTPUT],
        }
        with _tool_span("write_file", tool_input) as span:
            traces.append(
                "tool_call",
                {"stream": "tool", "tool_name": "write_file", "tool_input": tool_input},
            )
            target = _resolve_inside(root, path)
            if not _is_tracked(root, path):
                output = f"BLOCKED: {path} is not a tracked file." + _SCRATCH_WRITE_BLOCKED
                payload = {
                    "stream": "tool",
                    "tool_name": "write_file",
                    "ok": False,
                    "tool_input": tool_input,
                    "tool_output": output,
                }
                traces.append("tool_result", payload)
                _set_tool_span_output(span, payload)
                return output
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            output = f"Wrote {path} ({len(content.encode('utf-8'))} bytes)"
            payload = {
                "stream": "tool",
                "tool_name": "write_file",
                "ok": True,
                "tool_input": tool_input,
                "tool_output": output,
            }
            traces.append("tool_result", payload)
            _set_tool_span_output(span, payload)
            return output

    return [run_shell, read_file, write_file]
