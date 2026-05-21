from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool
from pydantic import Field

from evolve2_agent_bench.trace import RunTraces

MAX_TOOL_OUTPUT = 12_000


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


def make_workspace_tools(root: Path, traces: RunTraces) -> list:
    """Build LangChain tool instances bound to a workspace root and trace sink."""

    @tool
    def run_shell(
        command: Annotated[str, Field(description="Shell command to execute in the repo workspace.")],
        timeout_seconds: Annotated[
            int, Field(default=120, description="Max seconds before the command is killed.")
        ] = 120,
    ) -> str:
        """Execute a shell command in the repository workspace. Use for searching code (rg, grep),
        running tests (pytest), applying edits (sed, patch), git operations, or any CLI tool.
        Prefer targeted commands over broad searches."""
        traces.append(
            "tool_call",
            {
                "stream": "tool",
                "tool_name": "shell",
                "tool_input": {"command": command, "timeout_seconds": timeout_seconds},
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
            traces.append_shell(
                "shell_command_timeout",
                {
                    "command": command,
                    "tool_input": {"command": command, "timeout_seconds": timeout_seconds},
                    "tool_output": output,
                    "timeout_seconds": timeout_seconds,
                    "stdout": exc.stdout or "",
                    "stderr": exc.stderr or "",
                    "output": output,
                },
            )
            return output

        elapsed = time.monotonic() - started
        output = f"$ {command}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
        truncated = _truncate(output)
        traces.append_shell(
            "shell_command",
            {
                "command": command,
                "tool_input": {"command": command, "timeout_seconds": timeout_seconds},
                "tool_output": truncated,
                "returncode": proc.returncode,
                "elapsed_seconds": round(elapsed, 3),
                "stdout_bytes": len(proc.stdout.encode("utf-8")),
                "stderr_bytes": len(proc.stderr.encode("utf-8")),
                "output": truncated,
            },
        )
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
        traces.append(
            "tool_call",
            {"stream": "tool", "tool_name": "read_file", "tool_input": tool_input},
        )
        target = _resolve_inside(root, path)
        if not target.is_file():
            output = f"File not found: {path}"
            traces.append(
                "tool_result",
                {
                    "stream": "tool",
                    "tool_name": "read_file",
                    "ok": False,
                    "tool_input": tool_input,
                    "tool_output": output,
                },
            )
            return output

        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        start = start_line - 1
        selected = lines[start : start + max_lines]
        rendered = "\n".join(
            f"{line_no}: {line}" for line_no, line in enumerate(selected, start=start_line)
        )
        output = _truncate(rendered)
        traces.append(
            "tool_result",
            {
                "stream": "tool",
                "tool_name": "read_file",
                "ok": True,
                "tool_input": tool_input,
                "tool_output": output,
            },
        )
        return output

    @tool
    def write_file(
        path: Annotated[str, Field(description="Relative file path from the repo root.")],
        content: Annotated[str, Field(description="Complete new file content.")],
    ) -> str:
        """Write a file in the repository. Overwrites the entire file with the provided content.
        Use for creating new files or replacing file contents after reading and understanding the original."""
        tool_input = {
            "path": path,
            "content_bytes": len(content.encode("utf-8")),
            "content_preview": content[:MAX_TOOL_OUTPUT],
        }
        traces.append(
            "tool_call",
            {"stream": "tool", "tool_name": "write_file", "tool_input": tool_input},
        )
        target = _resolve_inside(root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        output = f"Wrote {path} ({len(content.encode('utf-8'))} bytes)"
        traces.append(
            "tool_result",
            {
                "stream": "tool",
                "tool_name": "write_file",
                "ok": True,
                "tool_input": tool_input,
                "tool_output": output,
            },
        )
        return output

    return [run_shell, read_file, write_file]
