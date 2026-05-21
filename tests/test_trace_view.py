"""Tests for trace compact view / LLM user-message deltas."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from evolve2_agent_bench.trace_view import (
    format_compact_trace,
    resolve_trace_path,
    user_message_delta,
)


class TestUserMessageDelta(unittest.TestCase):
    def test_suffix(self) -> None:
        prev = "hello"
        curr = "hello\n\nworld"
        d, ok = user_message_delta(prev, curr)
        self.assertTrue(ok)
        self.assertEqual(d, "world")

    def test_no_suffix_returns_full(self) -> None:
        d, ok = user_message_delta("abc", "cba")
        self.assertFalse(ok)
        self.assertEqual(d, "cba")


class TestResolveTracePath(unittest.TestCase):
    def test_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            p = Path(tmp.name)
        try:
            self.assertEqual(resolve_trace_path(p), p)
        finally:
            p.unlink(missing_ok=True)

    def test_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "trace.jsonl").write_text("{}\n", encoding="utf-8")
            self.assertEqual(resolve_trace_path(root), root / "trace.jsonl")


class TestFormatCompactTraceLlDelta(unittest.TestCase):
    def test_llm_shows_only_appended_user_turn(self) -> None:
        records = [
            {"stream": "llm", "event": "llm_call", "ts_ms": 1, "iteration": 1, "model": "m",
             "messages": [{"role": "system", "content": "SYS"}, {"role": "user", "content": "BASE"}],
             "response": "R1"},
            {"stream": "llm", "event": "llm_call", "ts_ms": 2, "iteration": 2, "model": "m",
             "messages": [{"role": "system", "content": "SYS"}, {"role": "user", "content": "BASE\n\nSTEP2"}],
             "response": "R2"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
            buf = io.StringIO()
            format_compact_trace(path, out=buf, stream_filter=frozenset({"llm"}))
            text = buf.getvalue()
        self.assertIn("new_user_turn (delta)", text)
        self.assertIn("STEP2", text)
        # Second LLM turn must not repeat the full accumulated user prefix in the delta section.
        second_turn = text.split("iteration=2", maxsplit=1)[1]
        pre_resp = second_turn.split("response:", maxsplit=1)[0]
        self.assertIn("STEP2", pre_resp)
        self.assertNotIn("BASE", pre_resp)


if __name__ == "__main__":
    unittest.main()
