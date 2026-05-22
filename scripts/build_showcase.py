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

ASCII_REPLACEMENTS = str.maketrans(
    {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
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
    "inconclusive": ("tested", "Tested"),
    "rejected": ("dropped", "Dropped"),
    "merged": ("shipped", "Shipped"),
    "baseline": ("reference", "Reference"),
}

FUNNEL_ORDER = ["backlog", "testing", "tested", "dropped", "shipped"]
FUNNEL_LABELS = {
    "backlog": "Backlog",
    "testing": "Testing now",
    "tested": "Tested",
    "dropped": "Dropped",
    "shipped": "Shipped",
}


def funnel_state(row: dict[str, Any]) -> tuple[str, str]:
    status = str(row.get("status") or "unknown")
    return FUNNEL.get(status, ("tested", "Tested"))


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
            title = next((row.get("title") for row in hypotheses if row.get("hypothesis_id") == hypothesis_id), "")
            return {
                "hypothesis_id": hypothesis_id,
                "title": title,
                "patch_bytes": payload.get("patch_bytes"),
                "run_id": payload.get("run_id"),
                "detail": payload.get("detail"),
            }
    return None


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


def render_hypothesis_cards(repo_url: str, rows: list[dict[str, Any]], limit: int = 8) -> str:
    cards = []
    for row in rows[:limit]:
        state, label = funnel_state(row)
        dossier = row.get("dossier") or row.get("dossier_path")
        href = repo_blob_url(repo_url, str(dossier)) if dossier else repo_url
        headline = row.get("value_headline") or "No value headline recorded yet."
        cards.append(
            f"""
            <article class="card">
              <div class="card-top">
                <a class="hid" href="{esc(href)}">{esc(row.get("hypothesis_id", "?"))}</a>
                <span class="pill {state}">{esc(label)}</span>
              </div>
              <h3>{esc(row.get("title", "Untitled hypothesis"))}</h3>
              <p>{esc(headline)}</p>
            </article>
            """
        )
    return "\n".join(cards)


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


def render_active_rows(rows: list[dict[str, Any]]) -> str:
    active = [row for row in rows if funnel_state(row)[0] in {"testing", "backlog"}]
    if not active:
        return '<p class="muted">No active rows are recorded on the board right now.</p>'
    items = []
    for row in active[:6]:
        items.append(
            f"""
            <li>
              <strong>{esc(row.get("hypothesis_id"))}: {esc(row.get("title"))}</strong>
              <span>{esc(row.get("value_headline", ""))}</span>
            </li>
            """
        )
    return "<ul>" + "\n".join(items) + "</ul>"


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

    breakthrough_html = ""
    if breakthrough:
        breakthrough_html = f"""
        <section class="breakthrough">
          <p class="eyebrow">Latest breakthrough</p>
          <h2>{esc(breakthrough.get("hypothesis_id"))}: {esc(breakthrough.get("title"))}</h2>
          <p>{esc(breakthrough.get("detail"))}</p>
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
    .wrap {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 56px; }}
    header {{
      min-height: 58vh;
      display: grid;
      align-content: center;
      border-bottom: 1px solid var(--line);
      margin-bottom: 28px;
    }}
    .eyebrow {{ text-transform: uppercase; letter-spacing: .08em; color: var(--muted); font-size: 12px; font-weight: 700; }}
    h1 {{ font-size: clamp(42px, 7vw, 92px); line-height: .96; margin: 10px 0 18px; letter-spacing: 0; max-width: 900px; }}
    h2 {{ font-size: 28px; margin: 0 0 12px; letter-spacing: 0; }}
    h3 {{ margin: 10px 0 8px; font-size: 18px; letter-spacing: 0; }}
    .lead {{ font-size: 21px; max-width: 780px; color: #2e3a42; }}
    .meta {{ color: var(--muted); margin-top: 18px; }}
    .grid {{ display: grid; gap: 16px; }}
    .stats {{ grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); margin: 28px 0; }}
    .stat {{ background: var(--panel); border: 1px solid var(--line); padding: 18px; }}
    .stat span {{ display: block; font-size: 34px; font-weight: 800; }}
    .stat label {{ color: var(--muted); text-transform: uppercase; font-size: 12px; font-weight: 700; }}
    section {{ margin: 34px 0; }}
    .breakthrough, .panel {{ background: var(--panel); border: 1px solid var(--line); padding: 24px; }}
    .breakthrough {{ border-left: 6px solid var(--green); }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }}
    .chips span {{ border: 1px solid var(--line); padding: 7px 10px; background: #f9fafb; font-size: 13px; }}
    .cards {{ grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); }}
    .card {{ background: var(--panel); border: 1px solid var(--line); padding: 18px; min-height: 190px; }}
    .card-top {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; }}
    .hid {{ font-weight: 800; text-decoration: none; }}
    .pill {{ border: 1px solid var(--line); padding: 4px 8px; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    .backlog {{ color: var(--violet); }}
    .testing {{ color: var(--blue); }}
    .tested {{ color: var(--amber); }}
    .dropped {{ color: var(--red); }}
    .shipped {{ color: var(--green); }}
    .feed {{ list-style: none; padding: 0; margin: 0; }}
    .feed li {{ border-top: 1px solid var(--line); padding: 16px 0; }}
    .feed time {{ display: block; color: var(--muted); font-size: 13px; }}
    .feed strong {{ display: inline-block; margin-right: 8px; }}
    .feed p {{ margin: 6px 0 0; color: #2f3a42; }}
    .two {{ grid-template-columns: minmax(0, 1fr) minmax(280px, .55fr); align-items: start; }}
    .panel ul {{ margin: 0; padding-left: 20px; }}
    .panel li {{ margin: 0 0 12px; }}
    .panel li span {{ display: block; color: var(--muted); }}
    .muted {{ color: var(--muted); }}
    footer {{ margin-top: 48px; color: var(--muted); font-size: 14px; }}
    @media (max-width: 760px) {{
      header {{ min-height: 46vh; }}
      .two {{ grid-template-columns: 1fr; }}
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

    <section class="grid two">
      <div>
        <p class="eyebrow">Latest episodes</p>
          <div class="grid cards">
          {render_hypothesis_cards(repo_url, visible_hypotheses)}
        </div>
      </div>
      <aside class="panel">
        <p class="eyebrow">On deck</p>
        {render_active_rows(board_rows)}
      </aside>
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
