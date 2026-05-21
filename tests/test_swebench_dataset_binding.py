"""Unit tests for local SWE-bench Verified dataset binding."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from evolve2_agent_bench.bench.swebench_runner import (
    DATASET_NAME,
    SPLIT,
    LOCAL_DATASET_ROOT_ENV,
    harness_dataset_arg,
    local_swebench_dataset_root,
)


class TestHarnessDatasetArg(unittest.TestCase):
    def test_hub_when_root_none(self) -> None:
        self.assertEqual(harness_dataset_arg(None), DATASET_NAME)

    def test_path_when_root_set(self) -> None:
        p = Path("/tmp/evolve2-dummy-root")
        self.assertEqual(harness_dataset_arg(p), str(p))


class TestLocalSwebenchDatasetRoot(unittest.TestCase):
    def test_unset_returns_none(self) -> None:
        prior = os.environ.pop(LOCAL_DATASET_ROOT_ENV, None)
        try:
            self.assertIsNone(local_swebench_dataset_root())
        finally:
            if prior is not None:
                os.environ[LOCAL_DATASET_ROOT_ENV] = prior

    def test_raises_when_marker_missing(self) -> None:
        prior = os.environ.pop(LOCAL_DATASET_ROOT_ENV, None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                os.environ[LOCAL_DATASET_ROOT_ENV] = str(root)
                with self.assertRaises(FileNotFoundError):
                    local_swebench_dataset_root()
        finally:
            os.environ.pop(LOCAL_DATASET_ROOT_ENV, None)
            if prior is not None:
                os.environ[LOCAL_DATASET_ROOT_ENV] = prior

    def test_returns_root_when_marker_present(self) -> None:
        prior = os.environ.pop(LOCAL_DATASET_ROOT_ENV, None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                marker = root / SPLIT / "dataset_info.json"
                marker.parent.mkdir(parents=True)
                marker.write_text("{}", encoding="utf-8")
                os.environ[LOCAL_DATASET_ROOT_ENV] = str(root)
                got = local_swebench_dataset_root()
                self.assertEqual(got, root.resolve())
        finally:
            os.environ.pop(LOCAL_DATASET_ROOT_ENV, None)
            if prior is not None:
                os.environ[LOCAL_DATASET_ROOT_ENV] = prior


if __name__ == "__main__":
    unittest.main()
