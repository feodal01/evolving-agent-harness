"""MLflow tracing toggle helpers."""

from __future__ import annotations

import os
import unittest

from evolve2_agent_bench.mlflow_tracing import tracing_requested


class TestTracingRequested(unittest.TestCase):
    def test_cli_forces_true(self) -> None:
        prior = os.environ.pop("EVOLVE2_MLFLOW_TRACING", None)
        try:
            self.assertTrue(tracing_requested(cli_enable=True))
            self.assertFalse(tracing_requested(cli_enable=False))
        finally:
            if prior is not None:
                os.environ["EVOLVE2_MLFLOW_TRACING"] = prior

    def test_env_truthy(self) -> None:
        prior = os.environ.pop("EVOLVE2_MLFLOW_TRACING", None)
        try:
            os.environ["EVOLVE2_MLFLOW_TRACING"] = "1"
            self.assertTrue(tracing_requested(cli_enable=False))
        finally:
            os.environ.pop("EVOLVE2_MLFLOW_TRACING", None)
            if prior is not None:
                os.environ["EVOLVE2_MLFLOW_TRACING"] = prior


if __name__ == "__main__":
    unittest.main()
