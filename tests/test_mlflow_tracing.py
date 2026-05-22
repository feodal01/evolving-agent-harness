"""MLflow tracing toggle helpers."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evolve2_agent_bench.mlflow_tracing import mlflow_trace_event, tracing_requested
from evolve2_agent_bench.trace import RunTraces


class TestTracingRequested(unittest.TestCase):
    def test_cli_forces_true(self) -> None:
        prior = os.environ.pop("EVOLVE2_MLFLOW_TRACING", None)
        try:
            self.assertTrue(tracing_requested(cli_flag=True))
            self.assertFalse(tracing_requested(cli_flag=False))
        finally:
            if prior is not None:
                os.environ["EVOLVE2_MLFLOW_TRACING"] = prior


class TestMlflowTraceEvent(unittest.TestCase):
    def test_adds_jsonl_record_to_current_span(self) -> None:
        class FakeSpan:
            def __init__(self) -> None:
                self.events = []

            def add_event(self, event) -> None:
                self.events.append(event)

        span = FakeSpan()
        with (
            patch("evolve2_agent_bench.mlflow_tracing.observability_enabled", return_value=True),
            patch("mlflow.get_current_active_span", return_value=span),
        ):
            mlflow_trace_event(
                {
                    "event": "tool_result",
                    "stream": "tool",
                    "tool_name": "read_file",
                    "tool_input": {"path": "src/example.py"},
                }
            )

        self.assertEqual(len(span.events), 1)
        event = span.events[0]
        self.assertEqual(event.name, "tool_result")
        self.assertEqual(event.attributes["stream"], "tool")
        self.assertEqual(event.attributes["tool_name"], "read_file")
        self.assertEqual(event.attributes["tool_input"], '{"path": "src/example.py"}')

    def test_run_trace_append_mirrors_record_to_mlflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch(
            "evolve2_agent_bench.trace.mlflow_trace_event"
        ) as mirror:
            traces = RunTraces.create(Path(tmp))
            record = traces.append("run_start", {"stream": "run", "run_id": "r1"})

        mirror.assert_called_once_with(record)

    def test_stream_slice_append_does_not_duplicate_mlflow_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch(
            "evolve2_agent_bench.trace.mlflow_trace_event"
        ) as mirror:
            traces = RunTraces.create(Path(tmp))
            traces.append_agent("agent_start", {"run_id": "r1"})

        mirror.assert_called_once()
        mirrored_record = mirror.call_args.args[0]
        self.assertEqual(mirrored_record["event"], "agent_start")
        self.assertEqual(mirrored_record["stream"], "agent")

    def test_env_truthy(self) -> None:
        prior = os.environ.pop("EVOLVE2_MLFLOW_TRACING", None)
        try:
            os.environ["EVOLVE2_MLFLOW_TRACING"] = "1"
            self.assertTrue(tracing_requested())
        finally:
            os.environ.pop("EVOLVE2_MLFLOW_TRACING", None)
            if prior is not None:
                os.environ["EVOLVE2_MLFLOW_TRACING"] = prior


if __name__ == "__main__":
    unittest.main()
