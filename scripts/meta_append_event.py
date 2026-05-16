#!/usr/bin/env python3
"""Append one validated JSON line to artifacts/meta/meta-events.jsonl.

Usage:
  echo '{"ts":"...","actor":"executor","event":"executor.started",...}' | uv run python scripts/meta_append_event.py
  uv run python scripts/meta_append_event.py '{"ts":"..."}'

Required keys: ts, actor, event, correlation_id, payload (object).
Optional: hypothesis_id (string or null).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REQUIRED = ("ts", "actor", "event", "correlation_id", "payload")
ALLOWED_ACTORS = frozenset({"orchestrator", "executor", "analyzer", "proposer"})


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_path = root / "artifacts" / "meta" / "meta-events.jsonl"
    raw = sys.stdin.read().strip() if not sys.argv[1:] else sys.argv[1]
    if not raw:
        print("No JSON payload provided.", file=sys.stderr)
        return 2
    try:
        obj: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2
    for key in REQUIRED:
        if key not in obj:
            print(f"Missing required key: {key}", file=sys.stderr)
            return 2
    if obj["actor"] not in ALLOWED_ACTORS:
        print(f"actor must be one of {sorted(ALLOWED_ACTORS)}", file=sys.stderr)
        return 2
    if not isinstance(obj["payload"], dict):
        print("payload must be a JSON object", file=sys.stderr)
        return 2
    if "hypothesis_id" in obj and obj["hypothesis_id"] is not None and not isinstance(obj["hypothesis_id"], str):
        print("hypothesis_id must be string or null", file=sys.stderr)
        return 2
    if obj["event"] == "sample.selected" and obj["actor"] != "orchestrator":
        print("sample.selected events must use actor orchestrator", file=sys.stderr)
        return 2
    line = json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n"
    default_path.parent.mkdir(parents=True, exist_ok=True)
    with default_path.open("a", encoding="utf-8") as handle:
        handle.write(line)
    print(str(default_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
