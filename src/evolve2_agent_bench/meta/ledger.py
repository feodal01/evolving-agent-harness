from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any


def current_git_sha(project_root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=project_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        return "uncommitted"
    return proc.stdout.strip()


def append_baseline_record(project_root: Path, result: dict[str, Any]) -> None:
    report = result.get("evaluation", {}).get("report", {})
    resolved = len(report.get("resolved_ids", [])) if isinstance(report, dict) else 0
    error_ids = report.get("error_ids", []) if isinstance(report, dict) else []
    failure_class = "resolved" if resolved else "evaluation_error" if error_ids else "unresolved"
    record = {
        "experiment_id": f"{time.strftime('%Y%m%d-%H%M%S')}-baseline",
        "parent_agent_git_sha": current_git_sha(project_root),
        "hypothesis": "Baseline LangChain JSON-action loop can produce an evaluable SWE-bench patch with full traces.",
        "change_summary": "Initial baseline agent and SWE-bench runner.",
        "task_ids": [result["instance_id"]],
        "run_ids": [result["run_id"]],
        "metrics": {
            "resolved": resolved,
            "wall_seconds": result["wall_seconds"],
            "llm_calls": result["agent_iterations"],
            "tool_calls": result["agent_iterations"],
            "patch_bytes": result["patch_bytes"],
        },
        "finding": failure_class,
        "next_action": "Inspect run traces and choose the smallest agent change that improves localization, patching, or validation.",
    }
    ledger = project_root / "artifacts" / "meta" / "experiment-ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
