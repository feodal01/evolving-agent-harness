#!/usr/bin/env python3
"""Download SWE-bench Verified (test split) once and save with datasets.save_to_disk.

Prefer the CLI command instead:
  uv run evolve2 materialize-dataset --out ./datasets/SWE-bench_Verified

After materialization, the harness loads tasks from disk automatically
(default: datasets/SWE-bench_Verified). Override with EVOLVE2_SWEBENCH_DATASET_ROOT.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("datasets/SWE-bench_Verified"),
        help="Parent directory; writes split to OUT/test/ (default: datasets/SWE-bench_Verified)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Redownload and overwrite even if OUT/test/dataset_info.json exists.",
    )
    args = parser.parse_args()

    from evolve2_agent_bench.bench.swebench_runner import materialize_dataset

    out = args.out.expanduser().resolve()
    result = materialize_dataset(out, force=args.force)
    print(f"Dataset at: {result}")
    print(f"export EVOLVE2_SWEBENCH_DATASET_ROOT={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
