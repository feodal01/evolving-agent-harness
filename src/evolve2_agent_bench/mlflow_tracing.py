"""MLflow observability for evolve2 benchmark runs.

Uses manual :py:class:`mlflow.start_span` traces (full agent + tools + harness).
LangChain autolog for ChatOpenAI stays **disabled** to avoid duplicate spans.

Enable with ``EVOLVE2_MLFLOW_TRACING=1`` or CLI ``--mlflow``.
Requires: ``uv sync --extra mlflow``

Environment:
- ``MLFLOW_TRACKING_URI`` — optional file/SQL store URI.
- ``MLFLOW_EXPERIMENT_NAME`` — default ``evolve2-agent-bench``.
"""

from __future__ import annotations

import logging
import os
import threading
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

_logger = logging.getLogger(__name__)

_lock = threading.Lock()
_initialized = False

# True only inside an active ``mlflow.start_run`` when tracing was requested.
_obs_enabled: ContextVar[bool] = ContextVar("evolve2_mlflow_obs_enabled", default=False)

MAX_SPAN_CHARS = 24_000


def tracing_requested(cli_enable: bool = False) -> bool:
    if cli_enable:
        return True
    v = os.environ.get("EVOLVE2_MLFLOW_TRACING", "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def observability_enabled() -> bool:
    return _obs_enabled.get()


def truncate_for_span(value: Any, max_chars: int = MAX_SPAN_CHARS) -> Any:
    """Shrink large strings / structures for MLflow span payloads."""
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


def ensure_initialized() -> None:
    """Configure tracking URI + experiment once."""
    global _initialized
    with _lock:
        if _initialized:
            return
        try:
            import mlflow
        except ImportError as exc:
            raise RuntimeError(
                "MLflow tracing is enabled but mlflow is not installed. "
                "Install with: uv sync --extra mlflow"
            ) from exc

        uri = os.environ.get("MLFLOW_TRACKING_URI", "").strip()
        if uri:
            mlflow.set_tracking_uri(uri)

        experiment = os.environ.get("MLFLOW_EXPERIMENT_NAME", "evolve2-agent-bench").strip()
        mlflow.set_experiment(experiment_name=experiment)

        _initialized = True
        _logger.info("MLflow tracking initialized (experiment=%s)", experiment)


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
):
    """One MLflow Run per benchmark + enable nested manual spans."""
    if not requested:
        yield
        return

    ensure_initialized()
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
