"""Compact, step-oriented rendering of unified trace.jsonl (especially LLM deltas)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TextIO


def user_message_delta(prev_user: str, curr_user: str) -> tuple[str, bool]:
    """Return (delta, True) if curr_user extends prev_user; else full curr_user with suffix_ok False."""
    if curr_user.startswith(prev_user):
        delta = curr_user[len(prev_user) :]
        return delta.lstrip("\n"), True
    return curr_user, False


def resolve_trace_path(target: Path) -> Path:
    if target.is_file():
        return target
    if target.is_dir():
        candidate = target / "trace.jsonl"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"No trace.jsonl at {target}")


def iter_trace_records(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def truncate(text: str, max_chars: int | None) -> str:
    if max_chars is None or len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n… [truncated]"


def format_compact_trace(
    path: Path,
    *,
    out: TextIO,
    llm_delta: bool = True,
    max_response_chars: int | None = 8000,
    max_delta_chars: int | None = None,
    limit_events: int | None = None,
    stream_filter: frozenset[str] | None = None,
) -> None:
    """Write a human-readable step trace.

    stream_filter: when set, only records whose `stream` is in this set (e.g. frozenset({'llm'})).
    """
    path = resolve_trace_path(path)
    prev_user = ""
    emitted = 0
    llm_index = 0
    for rec in iter_trace_records(path):
        stream = str(rec.get("stream", ""))
        event = str(rec.get("event", ""))

        if stream_filter is not None and stream not in stream_filter:
            continue

        if limit_events is not None and emitted >= limit_events:
            print(f"\n… stopped after {limit_events} matching events (--limit)", file=out)
            break

        emitted += 1
        ts_ms = rec.get("ts_ms")
        head = f"[{stream or '?'}::{event}]"
        if ts_ms is not None:
            head = f"{head} ts_ms={ts_ms}"

        if event == "llm_call" and stream == "llm":
            llm_index += 1
            user = ""
            sys_preview = ""
            for msg in rec.get("messages") or []:
                if not isinstance(msg, dict):
                    continue
                role = msg.get("role")
                content = str(msg.get("content", ""))
                if role == "user":
                    user = content
                elif role == "system":
                    sys_preview = content[:120] + ("…" if len(content) > 120 else "")
            if llm_delta:
                delta, suffix_ok = user_message_delta(prev_user, user)
                prev_user = user
                if not suffix_ok:
                    print(f"\n{head} iteration={rec.get('iteration')} ⚠ user payload not suffix of prior", file=out)
            else:
                delta = user
            if max_delta_chars is not None:
                delta = truncate(delta, max_delta_chars)
            resp = truncate(str(rec.get("response", "")), max_response_chars)
            print(f"\n{'─' * 72}", file=out)
            print(f"{head} iteration={rec.get('iteration')} model={rec.get('model')}", file=out)
            if llm_index == 1 and sys_preview:
                print(f"system (prefix): {sys_preview}", file=out)
            label = "new_user_turn (delta)" if llm_delta else "full_user_message"
            print(f"{label}:\n{delta if delta.strip() else '(empty delta)'}", file=out)
            print(f"response:\n{resp}", file=out)
            usage = rec.get("usage")
            if usage:
                print(f"usage: {usage}", file=out)
            continue

        if stream == "agent":
            extra = {k: v for k, v in rec.items() if k not in {"stream", "event", "ts_ms"}}
            print(f"{head} {json.dumps(extra, ensure_ascii=False)[:4000]}", file=out)
            continue

        if stream == "tool":
            extra = {k: v for k, v in rec.items() if k not in {"stream", "event", "ts_ms"}}
            print(f"{head} {json.dumps(extra, ensure_ascii=False)[:4000]}", file=out)
            continue

        if stream == "run":
            if event == "task_loaded":
                task = rec.get("task")
                keys = list(task.keys()) if isinstance(task, dict) else None
                iid = task.get("instance_id") if isinstance(task, dict) else None
                print(f"{head} instance_id={iid} task_fields={keys}", file=out)
            else:
                slim = {k: rec[k] for k in ("run_id", "instance_id", "dataset", "dataset_source") if k in rec}
                print(f"{head} {json.dumps(slim, ensure_ascii=False)}", file=out)
            continue

        if stream == "evaluation":
            if event == "evaluation_start":
                cmd = rec.get("command")
                print(f"{head} cmd={' '.join(cmd) if isinstance(cmd, list) else cmd}", file=out)
            elif event == "evaluation_finish":
                print(
                    f"{head} returncode={rec.get('returncode')} elapsed={rec.get('elapsed_seconds')}s",
                    file=out,
                )
            else:
                print(f"{head}", file=out)
            continue

        print(f"{head} {json.dumps({k: v for k, v in rec.items() if k not in {'ts_ms'}}, ensure_ascii=False)[:2000]}", file=out)
