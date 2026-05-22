"""MLflow observability for evolve2 benchmark runs.

MLflow is a **required** dependency as of v0.2. All coding agent runs and meta-
optimization actions are traced to a local file-backed MLflow store by default.

Tracing is enabled automatically. Disable with ``EVOLVE2_MLFLOW_TRACING=0`` or
CLI ``--no-mlflow``.

Environment:
- ``MLFLOW_TRACKING_URI`` — override the default local store
  (default: ``sqlite://<project_root>/artifacts/mlflow.db``).
- ``MLFLOW_EXPERIMENT_NAME`` — default ``evolve2-agent-bench``.
"""

from __future__ import annotations

import logging
import json
import os
import threading
from contextlib import contextmanager
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

_lock = threading.Lock()
_initialized = False

_obs_enabled: ContextVar[bool] = ContextVar("evolve2_mlflow_obs_enabled", default=False)

MAX_SPAN_CHARS = 24_000
MAX_EVENT_ATTRIBUTE_CHARS = 8_000


def _default_tracking_uri(project_root: Path | None = None) -> str:
    if project_root is None:
        project_root = Path(__file__).resolve().parents[2]
    db_path = project_root / "artifacts" / "mlflow.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def tracing_requested(cli_flag: bool | None = None) -> bool:
    """Return True unless explicitly disabled. MLflow tracing is ON by default."""
    if cli_flag is not None:
        return cli_flag
    v = os.environ.get("EVOLVE2_MLFLOW_TRACING", "").strip().lower()
    if v in {"0", "false", "no", "off"}:
        return False
    return True


def observability_enabled() -> bool:
    return _obs_enabled.get()


def truncate_for_span(value: Any, max_chars: int = MAX_SPAN_CHARS) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        if len(value) <= max_chars:
            return value
        return value[:max_chars] + f"\n… [{len(value) - max_chars} more chars]"
    if isinstance(value, dict):
        n = max(len(value), 1)
        return {k: truncate_for_span(v, max_chars=max(4000, max_chars // n)) for k, v in value.items()}
    if isinstance(value, list):
        cap = min(50, len(value))
        div = max(cap, 1)
        out = [truncate_for_span(v, max_chars=max_chars // div) for v in value[:cap]]
        if len(value) > cap:
            out.append(f"… [{len(value) - cap} more items]")
        return out
    return value


def _span_attribute_value(value: Any) -> str | bool | int | float:
    if isinstance(value, (bool, int, float, str)):
        if isinstance(value, str) and len(value) > MAX_EVENT_ATTRIBUTE_CHARS:
            return value[:MAX_EVENT_ATTRIBUTE_CHARS] + f"\n… [{len(value) - MAX_EVENT_ATTRIBUTE_CHARS} more chars]"
        return value
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if len(encoded) <= MAX_EVENT_ATTRIBUTE_CHARS:
        return encoded
    return encoded[:MAX_EVENT_ATTRIBUTE_CHARS] + f"\n… [{len(encoded) - MAX_EVENT_ATTRIBUTE_CHARS} more chars]"


def mlflow_trace_event(record: dict[str, Any]) -> None:
    """Attach a JSONL trace record to the current MLflow span as a searchable event."""
    if not observability_enabled():
        return
    import mlflow
    from mlflow.entities import SpanEvent

    span = mlflow.get_current_active_span()
    if span is None:
        return
    event = str(record.get("event", "trace_event"))
    attributes = {
        key: _span_attribute_value(value)
        for key, value in record.items()
        if key not in {"event"}
    }
    span.add_event(SpanEvent(name=event, attributes=attributes))


def ensure_initialized(project_root: Path | None = None) -> None:
    """Configure tracking URI + experiment once."""
    global _initialized
    with _lock:
        if _initialized:
            return
        import mlflow

        uri = os.environ.get("MLFLOW_TRACKING_URI", "").strip()
        if not uri:
            uri = _default_tracking_uri(project_root)
        mlflow.set_tracking_uri(uri)

        experiment = os.environ.get("MLFLOW_EXPERIMENT_NAME", "evolve2-agent-bench").strip()
        mlflow.set_experiment(experiment_name=experiment)

        _initialized = True
        _logger.info("MLflow tracking initialized (uri=%s, experiment=%s)", uri, experiment)


@contextmanager
def mlflow_span(
    name: str,
    span_type: str,
    *,
    attributes: dict[str, Any] | None = None,
):
    """Nested span when observability is enabled; otherwise no-op."""
    if not observability_enabled():
        yield None
        return
    import mlflow

    attrs = attributes or {}
    with mlflow.start_span(name=name, span_type=span_type, attributes=attrs) as span:
        yield span


@contextmanager
def mlflow_parent_run(
    *,
    run_name: str,
    requested: bool,
    tags: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    project_root: Path | None = None,
):
    """One MLflow Run per benchmark + enable nested manual spans."""
    if not requested:
        yield
        return

    ensure_initialized(project_root)
    import mlflow

    safe_name = run_name[:250]
    token: Token[bool] | None = None
    with mlflow.start_run(run_name=safe_name):
        if tags:
            for key, value in tags.items():
                mlflow.set_tag(key, str(value)[:500])
        if params:
            for key, value in params.items():
                if value is None:
                    mlflow.log_param(key, "unset")
                elif isinstance(value, (bool, int, float, str)):
                    mlflow.log_param(key, value)
                else:
                    mlflow.log_param(key, str(value)[:500])
        token = _obs_enabled.set(True)
        try:
            yield
        finally:
            if token is not None:
                _obs_enabled.reset(token)


def launch_mlflow_ui(project_root: Path | None = None, port: int = 5050) -> str:
    """Return the shell command to launch the MLflow UI for the local store."""
    if project_root is None:
        project_root = Path(__file__).resolve().parents[2]
    uri = os.environ.get("MLFLOW_TRACKING_URI", "").strip()
    if not uri:
        uri = _default_tracking_uri(project_root)
    return f"mlflow ui --backend-store-uri {uri} --port {port}"
