"""Tests for checkpointed finalization resume."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from evolve2_agent_bench.agent.base import BaselineLangChainAgent
from evolve2_agent_bench.config import OpenRouterConfig
from evolve2_agent_bench.trace import RunTraces


class TestCheckpointedFinalizationResume(unittest.TestCase):
    def test_resume_loads_checkpoint_and_clears_it_after_finish(self) -> None:
        cfg = OpenRouterConfig(api_key="test-key", model="m")
        with TemporaryDirectory() as td:
            root = Path(td)
            workspace = root / "repo"
            workspace.mkdir()
            traces = RunTraces.create(root)
            checkpoint_path = root / ".evolve2_checkpoint.json"

            first_agent = BaselineLangChainAgent(cfg, traces, max_tokens=None)
            first_agent._invoke = MagicMock(
                side_effect=[
                    json.dumps(
                        {
                            "thought": "t1",
                            "action": "run_shell",
                            "args": {"command": "true"},
                        }
                    ),
                    json.dumps(
                        {
                            "thought": "t2",
                            "action": "run_shell",
                            "args": {"command": "true"},
                        }
                    ),
                    json.dumps(
                        {
                            "thought": "t3",
                            "action": "run_shell",
                            "args": {"command": "true"},
                        }
                    ),
                ]
            )
            first_agent._execute = MagicMock(
                side_effect=lambda _tools, action: {"ok": True, "output": action.action}
            )

            first_result = first_agent.run(
                workspace,
                {
                    "instance_id": "x",
                    "repo": "r",
                    "base_commit": "c",
                    "problem_statement": "p",
                },
                max_iterations=3,
            )

            self.assertEqual(first_result.summary, "Stopped after 3 iterations without finish action.")
            self.assertTrue(checkpoint_path.exists())
            payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["task_instance_id"], "x")
            self.assertEqual(payload["final_iterations"], 3)
            self.assertIn("Checkpoint reached after iteration 3.", payload["conversation"][-1])

            resumed_agent = BaselineLangChainAgent(cfg, traces, max_tokens=None)
            resumed_agent._invoke = MagicMock(
                return_value=json.dumps(
                    {
                        "thought": "done",
                        "action": "finish",
                        "args": {"summary": "done"},
                    }
                )
            )

            resumed_result = resumed_agent.run(
                workspace,
                {
                    "instance_id": "x",
                    "repo": "r",
                    "base_commit": "c",
                    "problem_statement": "p",
                },
                max_iterations=5,
            )

            self.assertEqual(resumed_result.summary, "done")
            self.assertEqual(resumed_result.iterations, 4)
            self.assertEqual(resumed_agent._invoke.call_args[0][0], 4)
            self.assertFalse(checkpoint_path.exists())


if __name__ == "__main__":
    unittest.main()
