from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from evolve2_agent_bench.trace import RunTraces


MAX_TOOL_OUTPUT = 12000


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    output: str


def _resolve_inside(root: Path, requested: str) -> Path:
    target = (root / requested).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise ValueError(f"Path escapes workspace: {requested}")
    return target


@dataclass(frozen=True)
class WorkspaceTools:
    root: Path
    traces: RunTraces

    def run_shell(self, command: str, timeout_seconds: int = 120) -> ToolResult:
        self.traces.append(
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
                cwd=self.root,
                shell=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            output = f"$ {command}\n\nCommand timed out after {timeout_seconds} seconds."
            self.traces.append_shell(
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
            return ToolResult(ok=False, output=output)
        elapsed = time.monotonic() - started
        output = f"$ {command}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
        truncated = output[:MAX_TOOL_OUTPUT]
        if len(output) > MAX_TOOL_OUTPUT:
            truncated += "\n\n[output truncated]"
        self.traces.append_shell(
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
        return ToolResult(ok=proc.returncode == 0, output=truncated)

    def read_file(self, path: str, start_line: int, max_lines: int) -> ToolResult:
        tool_input = {"path": path, "start_line": start_line, "max_lines": max_lines}
        self.traces.append(
            "tool_call",
            {"stream": "tool", "tool_name": "read_file", "tool_input": tool_input},
        )
        target = _resolve_inside(self.root, path)
        if not target.is_file():
            output = f"File not found: {path}"
            self.traces.append(
                "tool_result",
                {
                    "stream": "tool",
                    "tool_name": "read_file",
                    "ok": False,
                    "tool_input": tool_input,
                    "tool_output": output,
                },
            )
            return ToolResult(ok=False, output=output)
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        start = start_line - 1
        selected = lines[start : start + max_lines]
        rendered = "\n".join(
            f"{line_no}: {line}" for line_no, line in enumerate(selected, start=start_line)
        )
        output = rendered[:MAX_TOOL_OUTPUT]
        self.traces.append(
            "tool_result",
            {
                "stream": "tool",
                "tool_name": "read_file",
                "ok": True,
                "tool_input": tool_input,
                "tool_output": output,
            },
        )
        return ToolResult(ok=True, output=output)

    def write_file(self, path: str, content: str) -> ToolResult:
        tool_input = {
            "path": path,
            "content_bytes": len(content.encode("utf-8")),
            "content_preview": content[:MAX_TOOL_OUTPUT],
        }
        self.traces.append(
            "tool_call",
            {"stream": "tool", "tool_name": "write_file", "tool_input": tool_input},
        )
        target = _resolve_inside(self.root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        output = f"Wrote {path} ({len(content.encode('utf-8'))} bytes)"
        self.traces.append(
            "tool_result",
            {
                "stream": "tool",
                "tool_name": "write_file",
                "ok": True,
                "tool_input": tool_input,
                "tool_output": output,
            },
        )
        return ToolResult(ok=True, output=output)
