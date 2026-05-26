"""Run validation batch for the active batch from validation-sets.json.

Sequentially runs all instances in the active batch using the evolve2 CLI.
Reads the active batch from artifacts/meta/validation-sets.json so the
meta-agent cannot cherry-pick instances.

Usage:
    uv run python scripts/run_validation_batch.py --fix-type mechanical
    uv run python scripts/run_validation_batch.py --fix-type hypothesis [--baseline]

For hypothesis runs, use --baseline to indicate this is the baseline run
(on main). Without --baseline, it is the candidate run (on the hypothesis branch).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATION_SETS_PATH = ROOT / "artifacts" / "meta" / "validation-sets.json"
RUNS_DIR = ROOT / "artifacts" / "runs"


def load_validation_sets() -> dict:
    if not VALIDATION_SETS_PATH.is_file():
        print(f"ERROR: {VALIDATION_SETS_PATH} not found", file=sys.stderr)
        sys.exit(1)
    return json.loads(VALIDATION_SETS_PATH.read_text(encoding="utf-8"))


def find_active_batch(validation_sets: dict) -> tuple[int, dict]:
    """Return (batch_index, batch_dict) for the lowest active/expanded batch."""
    for i, batch in enumerate(validation_sets["batches"]):
        status = batch.get("status", "locked")
        if status in ("active", "expanded"):
            return i, batch
    print("ERROR: No active or expanded batch found in validation-sets.json", file=sys.stderr)
    sys.exit(1)


def run_instance(instance_id: str, max_iterations: int = 100, evaluation_timeout: int = 1800) -> dict:
    """Run a single instance via the evolve2 CLI and return the result."""
    cmd = [
        "uv", "run", "evolve2", "run-task",
        "--instance-id", instance_id,
        "--max-iterations", str(max_iterations),
        "--evaluation-timeout", str(evaluation_timeout),
    ]
    print(f"\n{'='*60}")
    print(f"Running instance: {instance_id}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)

    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Try to parse the result JSON from stdout (evolve2 run-task prints it)
    output = result.stdout.strip()
    if output:
        try:
            # The CLI prints JSON at the end
            last_line = output.split("\n")[-1]
            return json.loads(last_line)
        except json.JSONDecodeError:
            pass

    return {"instance_id": instance_id, "raw_stdout": output, "returncode": result.returncode}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run validation batch: all 6 instances in the active batch, sequentially."
    )
    parser.add_argument(
        "--fix-type",
        choices=["mechanical", "hypothesis"],
        required=True,
        help="Fix type determines validation requirements.",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Mark this as a baseline run (for hypothesis fix-type).",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=100,
        help="Agent iteration cap (default: 100).",
    )
    parser.add_argument(
        "--evaluation-timeout",
        type=int,
        default=1800,
        help="Evaluation timeout in seconds (default: 1800).",
    )
    args = parser.parse_args()

    validation_sets = load_validation_sets()
    batch_index, batch = find_active_batch(validation_sets)
    instance_ids = batch.get("instance_ids", batch.get("instances", []))
    batch_status = batch.get("status", "unknown")

    print(f"Validation batch runner")
    print(f"  Fix type:    {args.fix_type}")
    print(f"  Batch index: {batch_index}")
    print(f"  Batch status:{batch_status}")
    print(f"  Instances:   {len(instance_ids)}")
    print(f"  Baseline:    {args.baseline}")
    print()

    if args.fix_type == "hypothesis" and not args.baseline:
        print("NOTE: This is a CANDIDATE run. Make sure you are on the hypothesis branch.")
    elif args.fix_type == "hypothesis" and args.baseline:
        print("NOTE: This is a BASELINE run. Make sure you are on main.")
    elif args.fix_type == "mechanical":
        print("NOTE: Mechanical fix validation. No baseline comparison needed.")

    results = []
    for i, instance_id in enumerate(instance_ids, 1):
        print(f"\n--- Instance {i}/{len(instance_ids)} ---")
        result = run_instance(instance_id, args.max_iterations, args.evaluation_timeout)
        result["batch_index"] = batch_index
        result["batch_status"] = batch_status
        result["fix_type"] = args.fix_type
        result["is_baseline"] = args.baseline
        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("BATCH VALIDATION SUMMARY")
    print("=" * 60)
    resolved_count = 0
    for r in results:
        iid = r.get("instance_id", "unknown")
        resolved = r.get("evaluation", {}).get("report", {}).get("resolved", False)
        patch_bytes = r.get("patch_bytes", 0)
        run_id = r.get("run_id", "unknown")
        status = "RESOLVED" if resolved else "NOT RESOLVED"
        if resolved:
            resolved_count += 1
        print(f"  {iid}: {status} (patch_bytes={patch_bytes}, run_id={run_id})")

    print(f"\nResolved: {resolved_count}/{len(instance_ids)}")
    print(f"Fix type: {args.fix_type}")
    print(f"Baseline: {args.baseline}")

    # Write summary to a file
    summary_path = ROOT / "artifacts" / "meta" / f"batch-{batch_index}-{'baseline' if args.baseline else 'candidate'}-summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nSummary written to: {summary_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
