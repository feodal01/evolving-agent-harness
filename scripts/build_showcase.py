from __future__ import annotations

import html
import json
import os
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "artifacts" / "meta"
OUT = ROOT / "docs" / "show" / "index.html"

DATASET_DIR = ROOT / "datasets" / "SWE-bench_Verified" / "test"
RUNS_DIR = ROOT / "artifacts" / "runs"

ASCII_REPLACEMENTS = str.maketrans(
    {
        "–": "-",
        "—": "-",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "…": "...",
    }
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def read_board_rows() -> list[dict[str, Any]]:
    path = META / "hypotheses-board.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("artifacts/meta/hypotheses-board.json must contain a list at rows")
    return rows


def merged_hypotheses(index_rows: list[dict[str, Any]], board_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in index_rows + board_rows:
        hypothesis_id = row.get("hypothesis_id")
        if not hypothesis_id:
            continue
        current = merged.setdefault(str(hypothesis_id), {})
        current.update(row)
    return sorted(
        merged.values(),
        key=lambda row: (str(row.get("updated_at") or row.get("created_at") or ""), str(row.get("hypothesis_id"))),
        reverse=True,
    )


def latest_timestamp(events: list[dict[str, Any]]) -> str:
    for event in reversed(events):
        ts = event.get("ts")
        if ts:
            return str(ts)
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def github_repo_url() -> str:
    github_repository = os.environ.get("GITHUB_REPOSITORY")
    if github_repository:
        server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
        return f"{server_url}/{github_repository}"
    try:
        remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return "https://github.com/feodal01/evolving-agent-harness"
    if remote.startswith("git@github.com:"):
        path = remote.removeprefix("git@github.com:").removesuffix(".git")
        return f"https://github.com/{path}"
    if remote.startswith("https://github.com/"):
        return remote.removesuffix(".git")
    return "https://github.com/feodal01/evolving-agent-harness"


def repo_blob_url(repo_url: str, path: str) -> str:
    return f"{repo_url}/blob/main/{path}"


def text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).translate(ASCII_REPLACEMENTS)


def esc(value: Any) -> str:
    return html.escape(text(value), quote=True)


FUNNEL = {
    "idea": ("backlog", "Backlog"),
    "running": ("testing", "Testing now"),
    "rejected": ("dropped", "Dropped"),
    "superseded": ("dropped", "Dropped"),
    "merged": ("shipped", "Shipped"),
    "baseline": ("reference", "Reference"),
}

FUNNEL_ORDER = ["backlog", "testing", "dropped", "shipped"]
FUNNEL_LABELS = {
    "backlog": "Backlog",
    "testing": "Testing now",
    "dropped": "Dropped",
    "shipped": "Shipped",
}

FUNNEL_COLORS = {
    "backlog": "var(--violet)",
    "testing": "var(--blue)",
    "dropped": "var(--red)",
    "shipped": "var(--green)",
}


def funnel_state(row: dict[str, Any]) -> tuple[str, str]:
    status = str(row.get("status") or "unknown")
    return FUNNEL.get(status, ("dropped", "Dropped"))


def event_summary(event: dict[str, Any]) -> str:
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return ""
    for key in ("summary", "detail", "rationale", "value_headline", "note", "sampler_rationale"):
        if payload.get(key):
            return str(payload[key])
    if payload.get("decision"):
        return f"Decision: {payload['decision']}"
    return ""


def find_breakthrough(events: list[dict[str, Any]], hypotheses: list[dict[str, Any]]) -> dict[str, Any] | None:
    for event in reversed(events):
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        if payload.get("patch_bytes", 0) and int(payload.get("patch_bytes", 0)) > 0:
            hypothesis_id = event.get("hypothesis_id")
            hyp = next((row for row in hypotheses if row.get("hypothesis_id") == hypothesis_id), {})
            return {
                "hypothesis_id": hypothesis_id,
                "title": hyp.get("title", ""),
                "summary": hyp.get("summary", ""),
                "patch_bytes": payload.get("patch_bytes"),
                "run_id": payload.get("run_id"),
                "detail": payload.get("detail"),
            }
    return None


def load_benchmark_instance_ids() -> list[str]:
    cache = META / "benchmark-instances.json"
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
        return data.get("instance_ids", [])
    if not DATASET_DIR.exists():
        return []
    try:
        from datasets import load_from_disk
        ds = load_from_disk(str(DATASET_DIR))
        ids = [str(row["instance_id"]) for row in ds]
        cache.write_text(json.dumps({"instance_ids": ids, "total": len(ids)}, indent=2), encoding="utf-8")
        return ids
    except Exception:
        return []


def load_validation_sets() -> dict[str, Any] | None:
    path = META / "validation-sets.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def collect_run_results() -> dict[str, dict[str, Any]]:
    cache = META / "benchmark-results.json"
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if isinstance(v, dict)}
    results: dict[str, dict[str, Any]] = {}
    if not RUNS_DIR.exists():
        return results
    for run_dir in sorted(RUNS_DIR.iterdir()):
        result_file = run_dir / "result.json"
        if not result_file.exists():
            continue
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        iid = data.get("instance_id", "")
        if not iid:
            continue
        report = data.get("evaluation", {}).get("report", {})
        resolved = iid in report.get("resolved_ids", [])
        patch_bytes = int(data.get("patch_bytes", 0) or 0)
        existing = results.get(iid)
        if existing is None or (resolved and not existing["resolved"]):
            results[iid] = {"resolved": resolved, "patch_bytes": patch_bytes}
    if results:
        cache.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def render_benchmark_bar(instance_ids: list[str], run_results: dict[str, dict[str, Any]]) -> str:
    if not instance_ids:
        return ""

    validation_sets = load_validation_sets()
    if validation_sets is None:
        return _render_flat_bar(instance_ids, run_results)
    return _render_batched_bar(instance_ids, run_results, validation_sets)


def _render_flat_bar(instance_ids: list[str], run_results: dict[str, dict[str, Any]]) -> str:
    resolved_count = 0
    attempted_unresolved = 0
    not_attempted = 0
    ticks: list[str] = []

    for iid in instance_ids:
        result = run_results.get(iid)
        if result is None:
            not_attempted += 1
            ticks.append('<span class="tick unattempted" title=""></span>')
        elif result["resolved"]:
            resolved_count += 1
            ticks.append(f'<span class="tick resolved" title="{esc(iid)}"></span>')
        else:
            attempted_unresolved += 1
            ticks.append(f'<span class="tick unresolved" title="{esc(iid)}"></span>')

    total = len(instance_ids)
    pct = (resolved_count / total * 100) if total else 0
    attempted = resolved_count + attempted_unresolved

    ticks_html = "\n".join(ticks)
    return f"""
    <section class="benchmark">
      <p class="eyebrow">Benchmark</p>
      <h2>SWE-bench Verified</h2>
      <p class="bench-desc">500 real GitHub issues from 12 Python repositories. Each instance requires generating a patch that passes the project's test suite.</p>
      <div class="bench-stats">
        <div class="stat"><span>{resolved_count}<span class="stat-total">/{total}</span></span><label>Resolved</label></div>
        <div class="stat"><span>{attempted_unresolved}<span class="stat-total">/{attempted}</span></span><label>Attempted, unresolved</label></div>
        <div class="stat"><span>{not_attempted}</span><label>Not attempted</label></div>
        <div class="stat resolved-pct"><span>{pct:.1f}%</span><label>Resolve rate</label></div>
      </div>
      <div class="bar-container">
        <div class="bar">
          {ticks_html}
        </div>
      </div>
      <div class="legend">
        <span class="legend-item"><span class="tick resolved"></span> Resolved</span>
        <span class="legend-item"><span class="tick unresolved"></span> Attempted, unresolved</span>
        <span class="legend-item"><span class="tick unattempted"></span> Not attempted</span>
      </div>
    </section>"""


def _render_batched_bar(
    instance_ids: list[str],
    run_results: dict[str, dict[str, Any]],
    vs: dict[str, Any],
) -> str:
    evo_set = vs.get("evolution_set", [])
    test_set = vs.get("test_set", [])
    batches = vs.get("batches", [])
    batch_size = vs.get("batch_size", 6)
    no_imp = vs.get("no_improvement_count", 0)
    no_imp_thresh = vs.get("no_improvement_threshold", 20)

    # Build instance -> (batch_index, batch_status) lookup
    iid_to_batch: dict[str, tuple[int, str]] = {}
    for batch in batches:
        idx = batch["batch_index"]
        status = batch.get("status", "locked")
        for iid in batch["instance_ids"]:
            iid_to_batch[iid] = (idx, status)

    # Count resolved in evolution set
    evo_resolved = 0
    evo_attempted_unresolved = 0
    for iid in evo_set:
        result = run_results.get(iid)
        if result and result["resolved"]:
            evo_resolved += 1
        elif result and not result["resolved"]:
            evo_attempted_unresolved += 1

    evo_total = len(evo_set)
    evo_pct = (evo_resolved / evo_total * 100) if evo_total else 0

    # Count batches resolved
    batches_resolved = sum(1 for b in batches if b.get("status") == "resolved")
    total_batches = len(batches)

    # Find active batch info
    active_batch = next((b for b in batches if b.get("status") in ("active", "expanded")), None)
    active_info = ""
    if active_batch:
        ab_ids = active_batch["instance_ids"]
        ab_resolved = sum(1 for iid in ab_ids if run_results.get(iid, {}).get("resolved"))
        active_info = f'<div class="stat"><span>{ab_resolved}<span class="stat-total">/{len(ab_ids)}</span></span><label>Active batch ({active_batch["batch_index"]})</label></div>'

    # Render evolution-set batches
    batch_groups: list[str] = []
    for batch in batches:
        idx = batch["batch_index"]
        status = batch.get("status", "locked")
        ticks_html = ""
        for iid in batch["instance_ids"]:
            result = run_results.get(iid)
            if result is None:
                ticks_html += f'<span class="tick unattempted" title="{esc(iid)}"></span>'
            elif result["resolved"]:
                ticks_html += f'<span class="tick resolved" title="{esc(iid)}"></span>'
            else:
                ticks_html += f'<span class="tick unresolved" title="{esc(iid)}"></span>'
        batch_groups.append(
            f'<div class="batch-group {esc(status)}" title="Batch {idx} ({esc(status)})">{ticks_html}</div>'
        )

    # Render test-set ticks
    test_ticks: list[str] = []
    for iid in test_set:
        test_ticks.append(f'<span class="tick test-locked" title="{esc(iid)}"></span>')

    evo_html = "\n".join(batch_groups)
    test_html = "\n".join(test_ticks)

    return f"""
    <section class="benchmark">
      <p class="eyebrow">Benchmark</p>
      <h2>SWE-bench Verified</h2>
      <p class="bench-desc">500 real GitHub issues from 12 Python repositories. Validation policy: <a href="https://github.com/feodal01/evolving-agent-harness/blob/main/docs/VALIDATION_POLICY.md">2/3 evolution + 1/3 held-out test</a>. Each instance requires generating a patch that passes the project's test suite.</p>
      <div class="bench-stats">
        <div class="stat"><span>{evo_resolved}<span class="stat-total">/{evo_total}</span></span><label>Resolved (evolution)</label></div>
        {active_info}
        <div class="stat"><span>{batches_resolved}<span class="stat-total">/{total_batches}</span></span><label>Batches resolved</label></div>
        <div class="stat"><span>{no_imp}<span class="stat-total">/{no_imp_thresh}</span></span><label>No-improvement streak</label></div>
        <div class="stat resolved-pct"><span>{evo_pct:.1f}%</span><label>Evolution resolve rate</label></div>
      </div>
      <div class="bar-container">
        <div class="bar">
          {evo_html}
        </div>
        <div class="batch-separator">Test set (locked until evolution complete)</div>
        <div class="bar">
          {test_html}
        </div>
      </div>
      <div class="legend">
        <span class="legend-item"><span class="tick resolved"></span> Resolved</span>
        <span class="legend-item"><span class="tick unresolved"></span> Attempted, unresolved</span>
        <span class="legend-item"><span class="tick unattempted"></span> Not attempted</span>
        <span class="legend-item"><span class="tick test-locked"></span> Test set (locked)</span>
        <span class="legend-item"><span class="batch-legend resolved"></span> Batch resolved</span>
        <span class="legend-item"><span class="batch-legend active"></span> Batch active</span>
        <span class="legend-item"><span class="batch-legend expanded"></span> Batch expanded (plateau)</span>
        <span class="legend-item"><span class="batch-legend locked"></span> Batch locked</span>
      </div>
    </section>"""


def public_hypotheses(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if funnel_state(row)[0] != "reference"]


def render_funnel_counts(counts: Counter[str]) -> str:
    items = []
    for state in FUNNEL_ORDER:
        if counts.get(state, 0):
            items.append(
                f'<div class="stat {state}"><span>{counts[state]}</span><label>{esc(FUNNEL_LABELS[state])}</label></div>'
            )
    return "\n".join(items)


def render_card(repo_url: str, row: dict[str, Any]) -> str:
    state, label = funnel_state(row)
    dossier = row.get("dossier") or row.get("dossier_path")
    href = repo_blob_url(repo_url, str(dossier)) if dossier else repo_url
    headline = row.get("summary") or row.get("value_headline") or "No summary recorded yet."
    return f"""
            <article class="card {state}">
              <div class="card-top">
                <a class="hid" href="{esc(href)}">{esc(row.get("hypothesis_id", "?"))}</a>
                <span class="pill {state}">{esc(label)}</span>
              </div>
              <h3>{esc(row.get("title", "Untitled hypothesis"))}</h3>
              <p>{esc(headline)}</p>
            </article>"""


def render_funnel_columns(repo_url: str, rows: list[dict[str, Any]]) -> str:
    by_state: dict[str, list[dict[str, Any]]] = {s: [] for s in FUNNEL_ORDER}
    for row in rows:
        state, _ = funnel_state(row)
        if state in by_state:
            by_state[state].append(row)

    columns = []
    for state in FUNNEL_ORDER:
        col_rows = by_state[state]
        count = len(col_rows)
        color = FUNNEL_COLORS[state]
        label = FUNNEL_LABELS[state]
        cards_html = "\n".join(render_card(repo_url, r) for r in col_rows) if col_rows else '<p class="muted">None yet.</p>'
        columns.append(f"""
      <div class="funnel-col">
        <div class="funnel-header" style="border-top: 4px solid {color}">
          <h2>{esc(label)} <span class="funnel-count">{count}</span></h2>
        </div>
        <div class="funnel-cards">
          {cards_html}
        </div>
      </div>""")
    return "\n".join(columns)


def render_event_feed(events: list[dict[str, Any]], title_by_id: dict[str, str], limit: int = 12) -> str:
    rows = []
    for event in reversed(events[-limit:]):
        hypothesis_id = event.get("hypothesis_id")
        title = title_by_id.get(str(hypothesis_id), "") if hypothesis_id else ""
        summary = event_summary(event)
        rows.append(
            f"""
            <li>
              <time>{esc(event.get("ts", ""))}</time>
              <strong>{esc(event.get("event", "event"))}</strong>
              <span>{esc(hypothesis_id or "round")}{(" - " + esc(title)) if title else ""}</span>
              <p>{esc(summary)}</p>
            </li>
            """
        )
    return "\n".join(rows)


def build_html() -> str:
    index_rows = read_jsonl(META / "hypothesis-index.jsonl")
    board_rows = read_board_rows()
    events = read_jsonl(META / "meta-events.jsonl")
    hypotheses = merged_hypotheses(index_rows, board_rows)
    visible_hypotheses = public_hypotheses(hypotheses)
    title_by_id = {str(row.get("hypothesis_id")): str(row.get("title", "")) for row in hypotheses}
    counts = Counter(funnel_state(row)[0] for row in visible_hypotheses)
    breakthrough = find_breakthrough(events, hypotheses)
    updated = latest_timestamp(events)
    repo_url = github_repo_url()

    benchmark_ids = load_benchmark_instance_ids()
    run_results = collect_run_results()
    benchmark_html = render_benchmark_bar(benchmark_ids, run_results)

    breakthrough_html = ""
    if breakthrough:
        breakthrough_desc = breakthrough.get("summary") or breakthrough.get("detail") or ""
        breakthrough_html = f"""
        <section class="breakthrough">
          <p class="eyebrow">Latest breakthrough</p>
          <h2>{esc(breakthrough.get("hypothesis_id"))}: {esc(breakthrough.get("title"))}</h2>
          <p>{esc(breakthrough_desc)}</p>
          <div class="chips">
            <span>{esc(breakthrough.get("patch_bytes"))} patch bytes</span>
            <span>run {esc(breakthrough.get("run_id"))}</span>
          </div>
        </section>
        """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Evolve2 Live</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172026;
      --muted: #66717a;
      --line: #d7dde2;
      --paper: #f6f7f8;
      --panel: #ffffff;
      --green: #1f7a4d;
      --blue: #2563a8;
      --red: #9c3d3d;
      --amber: #8a6500;
      --violet: #6b4aa0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--paper);
      line-height: 1.55;
    }}
    a {{ color: inherit; }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 32px 20px 56px; }}
    header {{
      min-height: 48vh;
      display: grid;
      align-content: center;
      border-bottom: 1px solid var(--line);
      margin-bottom: 28px;
    }}
    .eyebrow {{ text-transform: uppercase; letter-spacing: .08em; color: var(--muted); font-size: 12px; font-weight: 700; }}
    h1 {{ font-size: clamp(42px, 7vw, 92px); line-height: .96; margin: 10px 0 18px; letter-spacing: 0; max-width: 900px; }}
    h2 {{ font-size: 20px; margin: 0 0 12px; letter-spacing: 0; }}
    h3 {{ margin: 10px 0 8px; font-size: 16px; letter-spacing: 0; line-height: 1.3; }}
    .lead {{ font-size: 21px; max-width: 780px; color: #2e3a42; }}
    .meta {{ color: var(--muted); margin-top: 18px; }}
    .grid {{ display: grid; gap: 16px; }}
    .stats {{ grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); margin: 28px 0; }}
    .stat {{ background: var(--panel); border: 1px solid var(--line); padding: 18px; }}
    .stat span {{ display: block; font-size: 34px; font-weight: 800; }}
    .stat label {{ color: var(--muted); text-transform: uppercase; font-size: 12px; font-weight: 700; }}
    section {{ margin: 34px 0; }}
    .breakthrough {{ background: var(--panel); border: 1px solid var(--line); border-left: 6px solid var(--green); padding: 24px; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }}
    .chips span {{ border: 1px solid var(--line); padding: 7px 10px; background: #f9fafb; font-size: 13px; }}

    /* Funnel columns */
    .funnel {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; }}
    .funnel-col {{
      border: 1px solid var(--line);
      border-right: none;
      background: var(--panel);
    }}
    .funnel-col:last-child {{ border-right: 1px solid var(--line); }}
    .funnel-header {{
      padding: 14px 16px 10px;
      background: var(--panel);
      position: sticky;
      top: 0;
    }}
    .funnel-header h2 {{ display: flex; align-items: baseline; gap: 8px; margin: 0; }}
    .funnel-count {{
      font-size: 14px;
      font-weight: 800;
      color: var(--muted);
      background: #eef0f2;
      border-radius: 10px;
      padding: 2px 8px;
    }}
    .funnel-cards {{ padding: 0 12px 16px; }}

    .card {{
      background: #fafbfc;
      border: 1px solid var(--line);
      border-top: 3px solid var(--line);
      padding: 14px;
      margin-bottom: 10px;
      min-height: 120px;
    }}
    .card.shipped {{ border-top-color: var(--green); }}
    .card.dropped {{ border-top-color: var(--red); }}
    .card.backlog {{ border-top-color: var(--violet); }}
    .card.testing {{ border-top-color: var(--blue); }}
    .card-top {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; }}
    .hid {{ font-weight: 800; text-decoration: none; }}
    .pill {{ border: 1px solid var(--line); padding: 4px 8px; font-size: 11px; font-weight: 700; text-transform: uppercase; }}
    .backlog {{ color: var(--violet); }}
    .testing {{ color: var(--blue); }}
    .dropped {{ color: var(--red); }}
    .shipped {{ color: var(--green); }}
    .card p {{ font-size: 14px; color: #3a454d; margin: 6px 0 0; }}

    /* Event feed */
    .panel {{ background: var(--panel); border: 1px solid var(--line); padding: 24px; }}
    .feed {{ list-style: none; padding: 0; margin: 0; }}
    .feed li {{ border-top: 1px solid var(--line); padding: 16px 0; }}
    .feed time {{ display: block; color: var(--muted); font-size: 13px; }}
    .feed strong {{ display: inline-block; margin-right: 8px; }}
    .feed p {{ margin: 6px 0 0; color: #2f3a42; }}
    .muted {{ color: var(--muted); }}

    /* Benchmark bar */
    .benchmark {{ background: var(--panel); border: 1px solid var(--line); padding: 28px; }}
    .bench-desc {{ color: var(--muted); font-size: 15px; max-width: 720px; margin-bottom: 18px; }}
    .bench-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 22px; }}
    .stat-total {{ font-size: 18px; font-weight: 400; color: var(--muted); }}
    .resolved-pct span {{ color: var(--green); }}
    .bar-container {{ overflow-x: auto; padding: 4px 0; }}
    .bar {{ display: flex; flex-wrap: wrap; gap: 2px; min-width: 0; }}
    .tick {{
      width: 10px; height: 22px; border-radius: 2px; display: inline-block; flex-shrink: 0;
    }}
    .tick.resolved {{ background: var(--green); }}
    .tick.unresolved {{ background: var(--red); }}
    .tick.unattempted {{ background: #d7dde2; }}
    .tick.test-locked {{ background: #c8bfd6; opacity: 0.6; }}
    .tick[title]:hover {{ outline: 2px solid var(--ink); outline-offset: 1px; position: relative; z-index: 1; }}
    .batch-group {{ display: inline-flex; gap: 1px; margin-right: 3px; padding: 1px 2px; border-radius: 3px; border-left: 3px solid #d7dde2; }}
    .batch-group.resolved {{ border-left-color: var(--green); background: rgba(31, 122, 77, 0.05); }}
    .batch-group.active {{ border-left-color: var(--blue); background: rgba(37, 99, 168, 0.08); }}
    .batch-group.expanded {{ border-left-color: var(--amber); background: rgba(138, 101, 0, 0.06); }}
    .batch-group.locked {{ border-left-color: #d7dde2; }}
    .batch-separator {{ display: flex; align-items: center; gap: 8px; margin: 10px 0 6px; font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}
    .batch-separator::before, .batch-separator::after {{ content: ''; flex: 1; border-top: 1px dashed var(--line); }}
    .batch-legend {{ display: inline-block; width: 28px; height: 14px; border-radius: 2px; border-left: 3px solid #d7dde2; }}
    .batch-legend.resolved {{ border-left-color: var(--green); background: rgba(31, 122, 77, 0.05); }}
    .batch-legend.active {{ border-left-color: var(--blue); background: rgba(37, 99, 168, 0.08); }}
    .batch-legend.expanded {{ border-left-color: var(--amber); background: rgba(138, 101, 0, 0.06); }}
    .batch-legend.locked {{ border-left-color: #d7dde2; }}
    .legend {{ display: flex; gap: 20px; margin-top: 14px; flex-wrap: wrap; font-size: 13px; color: var(--muted); align-items: center; }}
    .legend-item {{ display: flex; align-items: center; gap: 6px; }}
    .legend .tick {{ width: 14px; height: 14px; }}
    footer {{ margin-top: 48px; color: var(--muted); font-size: 14px; }}
    @media (max-width: 760px) {{
      header {{ min-height: 40vh; }}
      .funnel {{ grid-template-columns: 1fr; }}
      .funnel-col {{ border-right: 1px solid var(--line); border-bottom: none; }}
      .funnel-col:last-child {{ border-bottom: 1px solid var(--line); }}
      .lead {{ font-size: 18px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <p class="eyebrow">Evolve2 live agent lab</p>
      <h1>A coding agent trying to improve itself.</h1>
      <p class="lead">Follow the experiment as a live series: each hypothesis is an episode, every branch is evidence, and every benchmark run moves the story forward or teaches the next move.</p>
      <p class="meta">Last ledger event: {esc(updated)}</p>
    </header>

    <section>
      <div class="grid stats">
        <div class="stat"><span>{len(visible_hypotheses)}</span><label>Total ideas</label></div>
        {render_funnel_counts(counts)}
      </div>
    </section>

    {breakthrough_html}

    {benchmark_html}

    <section>
      <p class="eyebrow">Hypothesis funnel</p>
      <div class="funnel">
        {render_funnel_columns(repo_url, visible_hypotheses)}
      </div>
    </section>

    <section class="panel">
      <p class="eyebrow">Production log</p>
      <ul class="feed">
        {render_event_feed(events, title_by_id)}
      </ul>
    </section>

    <footer>
      Generated from <a href="{esc(repo_blob_url(repo_url, "artifacts/meta"))}"><code>artifacts/meta</code></a> by <a href="{esc(repo_blob_url(repo_url, "scripts/build_showcase.py"))}"><code>scripts/build_showcase.py</code></a>. The public README is the trailer; this page is the episode feed.
    </footer>
  </div>
</body>
</html>
"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_html(), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
