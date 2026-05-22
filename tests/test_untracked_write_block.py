"""Tests for untracked file write blocking in tools."""

import subprocess
from contextlib import contextmanager
from pathlib import Path

import pytest

from evolve2_agent_bench.agent.tools import _is_tracked, _truncate, make_workspace_tools
from evolve2_agent_bench.trace import RunTraces


@pytest.fixture
def git_workspace(tmp_path: Path):
    ws = tmp_path / "repo"
    ws.mkdir()
    (ws / "tracked.py").write_text("x = 1\n")
    subprocess.run(["git", "init"], cwd=ws, check=True, capture_output=True)
    subprocess.run(["git", "add", "tracked.py"], cwd=ws, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=ws, check=True, capture_output=True)
    return ws


class TestIsTracked:
    def test_tracked_file(self, git_workspace: Path):
        assert _is_tracked(git_workspace, "tracked.py") is True

    def test_untracked_file(self, git_workspace: Path):
        assert _is_tracked(git_workspace, "untracked.py") is False

    def test_nested_tracked(self, git_workspace: Path):
        subdir = git_workspace / "pkg"
        subdir.mkdir()
        (subdir / "mod.py").write_text("y = 2\n")
        subprocess.run(["git", "add", "pkg/mod.py"], cwd=git_workspace, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "add pkg"], cwd=git_workspace, check=True, capture_output=True)
        assert _is_tracked(git_workspace, "pkg/mod.py") is True

    def test_untracked_nested(self, git_workspace: Path):
        assert _is_tracked(git_workspace, "pkg/new_file.py") is False


class TestWriteFileBlocking:
    def test_write_tracked_file_succeeds(self, git_workspace: Path, tmp_path: Path):
        traces = RunTraces.create(tmp_path / "traces")
        tools = make_workspace_tools(root=git_workspace, traces=traces)
        write_file = next(t for t in tools if t.name == "write_file")
        result = write_file.invoke({"path": "tracked.py", "content": "x = 42\n"})
        assert "Wrote tracked.py" in result
        assert "BLOCKED" not in result
        assert (git_workspace / "tracked.py").read_text() == "x = 42\n"

    def test_write_untracked_file_blocked(self, git_workspace: Path, tmp_path: Path):
        traces = RunTraces.create(tmp_path / "traces")
        tools = make_workspace_tools(root=git_workspace, traces=traces)
        write_file = next(t for t in tools if t.name == "write_file")
        result = write_file.invoke({"path": "reproduce_issue.py", "content": "print('hello')\n"})
        assert "BLOCKED" in result
        assert "untracked" in result.lower() or "not a tracked file" in result.lower()
        assert not (git_workspace / "reproduce_issue.py").exists()

    def test_write_untracked_nested_blocked(self, git_workspace: Path, tmp_path: Path):
        traces = RunTraces.create(tmp_path / "traces")
        tools = make_workspace_tools(root=git_workspace, traces=traces)
        write_file = next(t for t in tools if t.name == "write_file")
        result = write_file.invoke({"path": "test_repro.py", "content": "print('hello')\n"})
        assert "BLOCKED" in result


class TestPytestUnavailable:
    def test_pytest_failure_adds_message(self, git_workspace: Path, tmp_path: Path):
        traces = RunTraces.create(tmp_path / "traces")
        tools = make_workspace_tools(root=git_workspace, traces=traces)
        run_shell = next(t for t in tools if t.name == "run_shell")
        result = run_shell.invoke({"command": "pytest --version"})
        if "command not found" in result or "No module named" in result:
            assert "pytest is unavailable" in result


class TestToolMlflowSpans:
    def test_read_file_records_tool_span_inputs_and_outputs(
        self, git_workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        class FakeSpan:
            def __init__(self) -> None:
                self.inputs = None
                self.outputs = None

            def set_inputs(self, value) -> None:
                self.inputs = value

            def set_outputs(self, value) -> None:
                self.outputs = value

        spans: list[FakeSpan] = []

        @contextmanager
        def fake_mlflow_span(name, span_type, *, attributes=None):
            span = FakeSpan()
            spans.append(span)
            yield span

        monkeypatch.setattr("evolve2_agent_bench.agent.tools.mlflow_span", fake_mlflow_span)

        traces = RunTraces.create(tmp_path / "traces")
        tools = make_workspace_tools(root=git_workspace, traces=traces)
        read_file = next(t for t in tools if t.name == "read_file")
        result = read_file.invoke({"path": "tracked.py", "start_line": 1, "max_lines": 1})

        assert "1: x = 1" in result
        assert len(spans) == 1
        assert spans[0].inputs == {"path": "tracked.py", "start_line": 1, "max_lines": 1}
        assert spans[0].outputs["ok"] is True
        assert spans[0].outputs["tool_name"] == "read_file"
        assert "1: x = 1" in spans[0].outputs["tool_output"]
