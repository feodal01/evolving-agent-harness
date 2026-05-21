"""Retry logic when ChatOpenAI.invoke hits transport / JSON parse failures."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

from langchain_core.messages import AIMessage

from evolve2_agent_bench.agent.base import BaselineLangChainAgent
from evolve2_agent_bench.config import OpenRouterConfig
from evolve2_agent_bench.trace import RunTraces


class TestLLMTransportRetry(unittest.TestCase):
    @patch("evolve2_agent_bench.agent.base.subprocess.run", autospec=True)
    def test_finish_control_state_false_without_tracked_diff(self, run_mock: Mock) -> None:
        cfg = OpenRouterConfig(api_key="test-key", model="m")
        with TemporaryDirectory() as td:
            run_dir = Path(td)
            traces = RunTraces.create(run_dir)
            agent = BaselineLangChainAgent(cfg, traces, max_tokens=None)
            run_mock.return_value = Mock(returncode=0, stdout="", stderr="")

            state = agent._finish_control_state(run_dir)

            self.assertEqual(
                state,
                {
                    "tracked_source_diff": False,
                    "patch_confirmed": False,
                    "ready_to_finish": False,
                },
            )

    @patch("evolve2_agent_bench.agent.base.subprocess.run", autospec=True)
    def test_finish_control_state_true_with_tracked_diff(self, run_mock: Mock) -> None:
        cfg = OpenRouterConfig(api_key="test-key", model="m")
        with TemporaryDirectory() as td:
            run_dir = Path(td)
            traces = RunTraces.create(run_dir)
            agent = BaselineLangChainAgent(cfg, traces, max_tokens=None)
            run_mock.side_effect = [
                Mock(returncode=0, stdout="src/foo.py\n", stderr=""),
                Mock(returncode=0, stdout="diff --git a/src/foo.py b/src/foo.py\n", stderr=""),
            ]

            state = agent._finish_control_state(run_dir)

            self.assertEqual(
                state,
                {
                    "tracked_source_diff": True,
                    "patch_confirmed": True,
                    "ready_to_finish": True,
                },
            )

    @patch("evolve2_agent_bench.agent.base.time.sleep", autospec=True)
    def test_retries_json_decode_then_succeeds(self, _sleep: Mock) -> None:
        cfg = OpenRouterConfig(api_key="test-key", model="m")
        with TemporaryDirectory() as td:
            run_dir = Path(td)
            traces = RunTraces.create(run_dir)
            agent = BaselineLangChainAgent(cfg, traces, max_tokens=None)
            agent._finish_control_state = Mock(
                return_value={
                    "tracked_source_diff": True,
                    "patch_confirmed": True,
                    "ready_to_finish": True,
                }
            )
            mock_llm = MagicMock()
            calls = {"n": 0}

            def invoke_side_effect(_messages: object) -> AIMessage:
                calls["n"] += 1
                if calls["n"] < 3:
                    raise json.JSONDecodeError("Expecting value", "not-json", 0)
                return AIMessage(
                    content='{"thought":"t","action":"finish","args":{"summary":"done"}}'
                )

            mock_llm.invoke.side_effect = invoke_side_effect
            agent.llm = mock_llm

            result = agent.run(
                run_dir,
                {
                    "instance_id": "x",
                    "repo": "r",
                    "base_commit": "c",
                    "problem_statement": "p",
                },
                max_iterations=5,
            )
            self.assertEqual(result.summary, "done")
            self.assertEqual(calls["n"], 3)

    @patch("evolve2_agent_bench.agent.base.time.sleep", autospec=True)
    def test_non_retryable_raises(self, _sleep: Mock) -> None:
        cfg = OpenRouterConfig(api_key="test-key", model="m")
        with TemporaryDirectory() as td:
            run_dir = Path(td)
            traces = RunTraces.create(run_dir)
            agent = BaselineLangChainAgent(cfg, traces, max_tokens=None)
            agent._finish_control_state = Mock(
                return_value={
                    "tracked_source_diff": False,
                    "patch_confirmed": False,
                    "ready_to_finish": False,
                }
            )
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = ValueError("not transport")
            agent.llm = mock_llm

            with self.assertRaises(ValueError):
                agent.run(
                    run_dir,
                    {
                        "instance_id": "x",
                        "repo": "r",
                        "base_commit": "c",
                        "problem_statement": "p",
                    },
                    max_iterations=2,
                )

    @patch("evolve2_agent_bench.agent.base.LLM_TRANSPORT_MAX_ATTEMPTS", 3)
    @patch("evolve2_agent_bench.agent.base.time.sleep", autospec=True)
    def test_exhaustion_logs_transport_failed(self, _sleep: Mock) -> None:
        cfg = OpenRouterConfig(api_key="test-key", model="m")
        with TemporaryDirectory() as td:
            run_dir = Path(td)
            traces = RunTraces.create(run_dir)
            agent = BaselineLangChainAgent(cfg, traces, max_tokens=None)
            agent._finish_control_state = Mock(
                return_value={
                    "tracked_source_diff": False,
                    "patch_confirmed": False,
                    "ready_to_finish": False,
                }
            )
            mock_llm = MagicMock()

            def invoke_side_effect(_messages: object) -> AIMessage:
                raise json.JSONDecodeError("Expecting value", "", 0)

            mock_llm.invoke.side_effect = invoke_side_effect
            agent.llm = mock_llm

            agent.run(
                run_dir,
                {
                    "instance_id": "x",
                    "repo": "r",
                    "base_commit": "c",
                    "problem_statement": "p",
                },
                max_iterations=1,
            )

            text = (run_dir / "trace.jsonl").read_text(encoding="utf-8")
            self.assertIn("llm_invoke_transport_failed", text)
            self.assertIn("llm_transport_retry", text)


if __name__ == "__main__":
    unittest.main()
