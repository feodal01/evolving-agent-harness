"""Tests for agent trace callbacks."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from langchain_core.messages import ToolMessage

from evolve2_agent_bench.agent.callbacks import AgentTraceCallback, _tool_output_text
from evolve2_agent_bench.trace import RunTraces


class TestToolOutputText(unittest.TestCase):
    def test_string_passthrough(self) -> None:
        self.assertEqual(_tool_output_text("hello"), "hello")

    def test_tool_message_content(self) -> None:
        msg = ToolMessage(content="tool result", tool_call_id="call-1")
        self.assertEqual(_tool_output_text(msg), "tool result")


class TestAgentTraceCallback(unittest.TestCase):
    def test_on_tool_end_accepts_tool_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            traces = RunTraces.create(run_dir=run_dir)
            callback = AgentTraceCallback(traces=traces)
            callback.on_tool_end(
                ToolMessage(content="ok", tool_call_id="call-1"),
                run_id=uuid4(),
            )
            lines = (run_dir / "trace.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            event = json.loads(lines[0])
            self.assertEqual(event["event"], "agent_observation")
            self.assertEqual(event["observation"], "ok")
