"""Recompute meta artifacts from authoritative sources.

Reads run results, batch summaries, and the hypothesis board to regenerate:
- merged-results.jsonl (current merged agent results per instance)
- validation-sets.json no_improvement_count (computed from board)
- docs/show/index.html (showcase rebuilt from fresh data)

Usage:
    uv run python scripts/update_artifacts.py
    uv run python scripts/update_artifacts.py --dry-run
    uv run python scripts/update_artifacts.py --steps merged,nic,validation,showcase
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "artifacts" / "meta"
RUNS = ROOT / "artifacts" / "runs"
MERGED_RESULTS = META / "merged-results.jsonl"
VALIDATION_SETS = META / "validation-sets.json"
BOARD = META / "hypotheses-board.json"
BENCHMARK_CACHE = META / "benchmark-results.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def git_head_sha() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, timeout=5,
        )
        return proc.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "unknown"


def load_run_result(run_id: str) -> dict[str, Any] | None:
    """Load result.json for a given run_id."""
    result_file = RUNS / run_id / "result.json"
    if not result_file.exists():
        return None
    try:
        return json.loads(result_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def extract_run_summary(result: dict[str, Any]) -> dict[str, Any] | None:
    """Extract instance_id, resolved, patch_bytes, run_id from a result.json."""
    iid = result.get("instance_id")
    if not iid:
        return None
    report = result.get("evaluation", {}).get("report", {})
    resolved = iid in report.get("resolved_ids", []) or report.get("resolved_instances", 0) > 0
    return {
        "instance_id": iid,
        "resolved": resolved,
        "patch_bytes": int(result.get("patch_bytes", 0) or 0),
        "run_id": result.get("run_id", ""),
    }


def _parse_raw_stdout(raw: str) -> dict[str, Any] | None:
    """Parse the JSON result object from a batch summary's raw_stdout field."""
    if not raw:
        return None
    # The raw_stdout may contain the evolve2 CLI JSON output (multi-line).
    # Find the first '{' and parse from there.
    idx = raw.find("{")
    if idx < 0:
        return None
    try:
        obj = json.loads(raw[idx:], strict=False)
        if "run_id" in obj:
            return obj
    except json.JSONDecodeError:
        pass
    return None


def find_baseline_run_ids() -> dict[str, str]:
    """Find the most recent baseline run_id for each instance from batch summaries."""
    run_id_map: dict[str, str] = {}
    if not META.exists():
        return run_id_map
    for summary_file in sorted(META.glob("batch-*-baseline-summary.json")):
        data = read_json(summary_file)
        if not isinstance(data, list):
            continue
        for entry in data:
            iid = entry.get("instance_id")
            rid = entry.get("run_id")
            # run_id may be at top level (new format) or inside raw_stdout (old format)
            if not rid:
                parsed = _parse_raw_stdout(entry.get("raw_stdout", ""))
                if parsed:
                    rid = parsed.get("run_id")
            if iid and rid:
                run_id_map[iid] = rid
    return run_id_map


def find_latest_run_per_instance() -> dict[str, str]:
    """Find the most recent run_id for each instance from run directories."""
    iid_to_run: dict[str, str] = {}
    if not RUNS.exists():
        return iid_to_run
    for run_dir in sorted(RUNS.iterdir()):
        result_file = run_dir / "result.json"
        if not result_file.exists():
            continue
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        iid = data.get("instance_id")
        rid = data.get("run_id")
        if iid and rid:
            iid_to_run[iid] = rid
    return iid_to_run


# --- Step: update merged-results.jsonl ---

def update_merged_results(dry_run: bool = False) -> list[str]:
    """Regenerate merged-results.jsonl from run artifacts.

    For instances that have a baseline batch summary, use those results
    (they represent the current merged agent). For others, preserve
    existing merged-results entries.
    """
    changes: list[str] = []
    vs = read_json(VALIDATION_SETS)
    if not vs:
        changes.append("SKIP: validation-sets.json not found")
        return changes

    all_instance_ids = set()
    for batch in vs.get("batches", []):
        all_instance_ids.update(batch.get("instance_ids", []))

    # Get baseline run results (authoritative for "current merged agent")
    baseline_run_ids = find_baseline_run_ids()
    latest_runs = find_latest_run_per_instance()

    # Build new merged results
    new_results: dict[str, dict[str, Any]] = {}

    # First: existing entries (preserved for instances without baseline data)
    for row in read_jsonl(MERGED_RESULTS):
        iid = row.get("instance_id", "")
        if iid:
            new_results[iid] = row

    # Override with baseline batch results
    head_sha = git_head_sha()
    for iid, rid in baseline_run_ids.items():
        result = load_run_result(rid)
        if result:
            summary = extract_run_summary(result)
            if summary:
                summary["merge_sha"] = head_sha
                new_results[iid] = summary

    # For instances with runs but no baseline, use the latest run on main
    # (only if the instance doesn't already have a result)
    # This is a fallback for batches without baseline summaries.

    # Sort and write
    sorted_results = sorted(new_results.values(), key=lambda r: r.get("instance_id", ""))
    lines = [json.dumps(r, ensure_ascii=False, sort_keys=True) for r in sorted_results]
    new_content = "\n".join(lines) + "\n" if lines else ""

    old_content = MERGED_RESULTS.read_text(encoding="utf-8") if MERGED_RESULTS.exists() else ""
    resolved_count = sum(1 for r in sorted_results if r.get("resolved"))
    total = len(sorted_results)

    old_resolved = old_content.count('"resolved": true')
    if new_content != old_content:
        changes.append(f"merged-results.jsonl: {resolved_count}/{total} resolved (was {old_resolved} resolved)")
        if not dry_run:
            MERGED_RESULTS.write_text(new_content, encoding="utf-8")
    else:
        changes.append(f"merged-results.jsonl: unchanged ({resolved_count}/{total} resolved)")

    return changes


# --- Step: compute no_improvement_count ---

def compute_no_improvement_count() -> int:
    """Count consecutive non-merged hypotheses from the board, newest first."""
    board = read_json(BOARD)
    if not board:
        return 0
    rows = board.get("rows", [])
    if not rows:
        return 0

    sorted_rows = sorted(
        rows,
        key=lambda r: (str(r.get("updated_at") or ""), str(r.get("hypothesis_id") or "")),
        reverse=True,
    )

    count = 0
    for row in sorted_rows:
        status = str(row.get("status", ""))
        if status == "merged":
            break
        if status in ("rejected", "superseded"):
            count += 1
        # Skip "idea", "running", "in_progress" etc. — they don't count

    return count


# --- Step: update validation-sets.json ---

def update_validation_sets(dry_run: bool = False) -> list[str]:
    """Update no_improvement_count in validation-sets.json from the board."""
    changes: list[str] = []
    vs = read_json(VALIDATION_SETS)
    if not vs:
        changes.append("SKIP: validation-sets.json not found")
        return changes

    nic = compute_no_improvement_count()
    old_nic = vs.get("no_improvement_count", 0)

    if nic != old_nic:
        changes.append(f"validation-sets.json: no_improvement_count {old_nic} -> {nic}")
        if not dry_run:
            vs["no_improvement_count"] = nic
            # Also update in the active batch
            for batch in vs.get("batches", []):
                if batch.get("status") in ("active", "expanded"):
                    batch["no_improvement_count"] = nic
            write_json(VALIDATION_SETS, vs)
    else:
        changes.append(f"validation-sets.json: no_improvement_count unchanged ({nic})")

    return changes


# --- Step: rebuild showcase ---

def rebuild_showcase(dry_run: bool = False) -> list[str]:
    """Remove benchmark cache and rebuild showcase HTML."""
    changes: list[str] = []

    if BENCHMARK_CACHE.exists():
        changes.append("Removed benchmark-results.json cache")
        if not dry_run:
            BENCHMARK_CACHE.unlink()

    try:
        from build_showcase import main as showcase_main
        # build_showcase is in scripts/ — import would need sys.path hack
        # Use subprocess instead for simplicity
    except ImportError:
        pass

    if not dry_run:
        try:
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build_showcase.py")],
                cwd=ROOT, text=True, capture_output=True, timeout=30,
            )
            if proc.returncode == 0:
                changes.append("Showcase rebuilt successfully")
            else:
                changes.append(f"Showcase rebuild failed: {proc.stderr[:200]}")
        except Exception as e:
            changes.append(f"Showcase rebuild error: {e}")
    else:
        changes.append("Would rebuild showcase (skipped in dry-run)")

    return changes


# --- Main ---

ALL_STEPS = ["merged", "nic", "validation", "showcase"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Recompute meta artifacts from authoritative sources.")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would change without writing files.",
    )
    parser.add_argument(
        "--steps", default=",".join(ALL_STEPS),
        help=f"Comma-separated steps to run: {', '.join(ALL_STEPS)} (default: all)",
    )
    args = parser.parse_args()

    steps = [s.strip() for s in args.steps.split(",") if s.strip() in ALL_STEPS]
    if not steps:
        print(f"No valid steps. Choose from: {', '.join(ALL_STEPS)}", file=sys.stderr)
        return 1

    all_changes: list[str] = []

    if "merged" in steps:
        all_changes.extend(update_merged_results(dry_run=args.dry_run))

    if "nic" in steps:
        nic = compute_no_improvement_count()
        all_changes.append(f"no_improvement_count (computed): {nic}")

    if "validation" in steps:
        all_changes.extend(update_validation_sets(dry_run=args.dry_run))

    if "showcase" in steps:
        all_changes.extend(rebuild_showcase(dry_run=args.dry_run))

    print("Artifact update results:")
    for change in all_changes:
        print(f"  {change}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
