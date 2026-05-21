#!/usr/bin/env python3
"""Download SWE-bench Verified (test split) once and save with datasets.save_to_disk.

After this, set EVOLVE2_SWEBENCH_DATASET_ROOT to the parent directory passed via --out
so evolve2 loads tasks and swebench evaluation from disk (no Hugging Face Hub at run time).

Example:
  uv run python scripts/materialize_swebench_verified.py --out ./datasets/SWE-bench_Verified
  export EVOLVE2_SWEBENCH_DATASET_ROOT="$(pwd)/datasets/SWE-bench_Verified"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from datasets import load_dataset


DATASET = "princeton-nlp/SWE-bench_Verified"
SPLIT = "test"


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
    out = args.out.expanduser().resolve()
    split_dir = out / SPLIT
    marker = split_dir / "dataset_info.json"
    if marker.is_file() and not args.force:
        print(f"Already present (use --force to refresh): {marker}")
        print(f"export EVOLVE2_SWEBENCH_DATASET_ROOT={out}")
        return 0

    out.mkdir(parents=True, exist_ok=True)
    if split_dir.exists() and args.force:
        import shutil

        shutil.rmtree(split_dir)

    print(f"Downloading {DATASET} split={SPLIT} …")
    ds = load_dataset(DATASET, split=SPLIT)
    ds.save_to_disk(str(split_dir))
    print(f"Saved to {split_dir}")
    print(f"export EVOLVE2_SWEBENCH_DATASET_ROOT={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
