from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from rich import print as rprint

from evolve2_agent_bench.bench.swebench_runner import run_one_task
from evolve2_agent_bench.config import DEFAULT_MODEL, OpenRouterConfig
from evolve2_agent_bench.trace_view import format_compact_trace


app = typer.Typer(no_args_is_help=True)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@app.command()
def model_check(
    model: Annotated[str, typer.Option(help="OpenRouter model id.")] = DEFAULT_MODEL,
) -> None:
    config = OpenRouterConfig.from_env(model=model)
    llm = ChatOpenAI(
        model=config.model,
        api_key=config.api_key,
        base_url=config.base_url,
        temperature=0,
        max_tokens=16,
        max_retries=6,
        default_headers={
            "HTTP-Referer": "http://localhost/evolve2",
            "X-Title": "evolve2-model-check",
        },
    )
    response = llm.invoke([HumanMessage(content="Reply with exactly: model-ok")])
    rprint(str(response.content).strip())


@app.command("trace-view")
def trace_view_cmd(
    target: Annotated[
        Path,
        typer.Argument(help="trace.jsonl file or run directory containing trace.jsonl.", exists=True),
    ],
    full_llm_user: Annotated[
        bool,
        typer.Option("--full-llm-user", help="Show full user blob each call (default: delta only)."),
    ] = False,
    max_response_chars: Annotated[
        int,
        typer.Option("--max-response-chars", help="Truncate model reply in output; 0 = no limit."),
    ] = 8000,
    max_delta_chars: Annotated[
        int | None,
        typer.Option("--max-delta-chars", help="Truncate printed user-message delta."),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Stop after this many matching records."),
    ] = None,
    stream: Annotated[
        list[str],
        typer.Option("--stream", help="Repeat to restrict e.g. --stream llm --stream agent."),
    ] = [],
) -> None:
    """Print a compact timeline; LLM turns default to new user text only (suffix delta)."""
    import sys

    mrc = None if max_response_chars == 0 else max_response_chars
    sf_parts = [s.strip().lower() for s in stream if s.strip()]
    sf: frozenset[str] | None = frozenset(sf_parts) if sf_parts else None
    format_compact_trace(
        target,
        out=sys.stdout,
        llm_delta=not full_llm_user,
        max_response_chars=mrc,
        max_delta_chars=max_delta_chars,
        limit_events=limit,
        stream_filter=sf,
    )


@app.command()
def run_task(
    instance_id: Annotated[
        str,
        typer.Option(help="SWE-bench Verified instance id."),
    ] = "astropy__astropy-12907",
    model: Annotated[str, typer.Option(help="OpenRouter model id.")] = DEFAULT_MODEL,
    max_iterations: Annotated[
        int,
        typer.Option(min=1, max=200, help="Emergency loop cap, not a short work budget."),
    ] = 100,
    agent_max_tokens: Annotated[
        int | None,
        typer.Option(
            min=256,
            help="Optional maximum completion tokens for each agent LLM call. Unset by default.",
        ),
    ] = None,
    evaluation_timeout: Annotated[int, typer.Option(min=60)] = 1800,
    mlflow_tracing: Annotated[
        bool,
        typer.Option(
            "--mlflow",
            help="Send LangChain traces to MLflow (requires: uv sync --extra mlflow). Or set EVOLVE2_MLFLOW_TRACING=1.",
        ),
    ] = False,
) -> None:
    root = project_root()
    config = OpenRouterConfig.from_env(model=model)
    result = run_one_task(
        project_root=root,
        instance_id=instance_id,
        config=config,
        max_iterations=max_iterations,
        agent_max_tokens=agent_max_tokens,
        evaluation_timeout=evaluation_timeout,
        enable_mlflow_tracing=mlflow_tracing,
    )
    rprint(json.dumps(result, indent=2, ensure_ascii=False))
