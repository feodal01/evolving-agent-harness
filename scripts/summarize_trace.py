from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "artifacts" / "runs"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def resolve_run_dir(run_id: str) -> Path:
    candidate = RUNS_DIR / run_id
    if candidate.is_dir():
        return candidate
    matches = sorted(path for path in RUNS_DIR.glob(f"*{run_id}*") if path.is_dir())
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise SystemExit(f"No run found for: {run_id}")
    raise SystemExit(f"Run id is ambiguous: {run_id}")


def usage_totals(events: list[dict[str, Any]]) -> dict[str, int]:
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for event in events:
        usage = event.get("usage")
        if not isinstance(usage, dict):
            continue
        for key in totals:
            value = usage.get(key)
            if isinstance(value, int):
                totals[key] += value
    return totals


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize a unified evolve2 trace.")
    parser.add_argument("run_id", help="Full or unique suffix of artifacts/runs/<run_id>.")
    args = parser.parse_args()

    run_dir = resolve_run_dir(args.run_id)
    trace_path = run_dir / "trace.jsonl"
    result_path = run_dir / "result.json"
    if not trace_path.is_file():
        raise SystemExit(f"Missing trace: {trace_path}")

    events = load_jsonl(trace_path)
    event_counts = Counter(str(event["event"]) for event in events)
    stream_counts = Counter(str(event.get("stream", "unknown")) for event in events)
    tool_counts = Counter(
        str(event["tool_name"]) for event in events if event.get("event") == "tool_call"
    )
    invalid_actions = [event for event in events if event.get("event") == "invalid_action"]
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}

    summary = {
        "run_id": run_dir.name,
        "trace_path": str(trace_path),
        "result_path": str(result_path) if result_path.is_file() else None,
        "event_count": len(events),
        "event_counts": dict(sorted(event_counts.items())),
        "stream_counts": dict(sorted(stream_counts.items())),
        "tool_counts": dict(sorted(tool_counts.items())),
        "invalid_action_count": len(invalid_actions),
        "token_usage": usage_totals(events),
        "patch_bytes": result.get("patch_bytes"),
        "wall_seconds": result.get("wall_seconds"),
        "evaluation_report": result.get("evaluation", {}).get("report"),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
