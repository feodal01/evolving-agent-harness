"""Retry logic when ChatOpenAI.invoke hits transport / JSON parse failures."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

from langchain_core.messages import AIMessage

from evolve2_agent_bench.agent.base import ReActCodingAgent
from evolve2_agent_bench.config import LLMConfig
from evolve2_agent_bench.trace import RunTraces


def _make_agent(tmp: str) -> tuple[ReActCodingAgent, Path]:
    run_dir = Path(tmp)
    traces = RunTraces.create(run_dir)
    cfg = LLMConfig(api_key="test-key", model="m", base_url="http://localhost/v1")
    agent = ReActCodingAgent(cfg, traces, max_tokens=None)
    return agent, run_dir


class TestLLMTransportRetry(unittest.TestCase):
    @patch("evolve2_agent_bench.agent.base.time.sleep", autospec=True)
    def test_retries_json_decode_then_succeeds(self, _sleep: Mock) -> None:
        with TemporaryDirectory() as td:
            agent, run_dir = _make_agent(td)
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
        with TemporaryDirectory() as td:
            agent, run_dir = _make_agent(td)
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


if __name__ == "__main__":
    unittest.main()
