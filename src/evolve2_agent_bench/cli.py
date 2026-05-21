from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from rich import print as rprint

from evolve2_agent_bench.bench.swebench_runner import (
    DEFAULT_DATASET_DIR,
    materialize_dataset,
    resolve_dataset_root,
    run_one_task,
)
from evolve2_agent_bench.config import DEFAULT_MODEL, OpenRouterConfig
from evolve2_agent_bench.mlflow_tracing import launch_mlflow_ui
from evolve2_agent_bench.trace_view import format_compact_trace


app = typer.Typer(no_args_is_help=True)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@app.command()
def model_check(
    model: Annotated[str, typer.Option(help="OpenRouter model id.")] = DEFAULT_MODEL,
) -> None:
    """Verify OpenRouter connectivity and model availability."""
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


@app.command("materialize-dataset")
def materialize_dataset_cmd(
    out: Annotated[
        Path,
        typer.Option(help="Output directory for the dataset."),
    ] = Path(DEFAULT_DATASET_DIR),
    force: Annotated[
        bool,
        typer.Option("--force", help="Redownload and overwrite."),
    ] = False,
) -> None:
    """Download SWE-bench Verified dataset for offline use."""
    root = project_root()
    out_path = out if out.is_absolute() else root / out
    rprint(f"Materializing SWE-bench Verified to {out_path} …")
    result = materialize_dataset(out_path, force=force)
    rprint(f"[green]Done.[/green] Dataset at: {result}")
    rprint(f"export EVOLVE2_SWEBENCH_DATASET_ROOT={result}")


@app.command("dataset-status")
def dataset_status_cmd() -> None:
    """Check if SWE-bench Verified dataset is available offline."""
    root = project_root()
    try:
        ds_root = resolve_dataset_root(root)
        rprint(f"[green]Dataset available:[/green] {ds_root}")
    except FileNotFoundError as exc:
        rprint(f"[red]Dataset not found.[/red] {exc}")
        raise typer.Exit(code=1)


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


@app.command("mlflow-ui")
def mlflow_ui_cmd(
    port: Annotated[int, typer.Option(help="Port for the MLflow UI.")] = 5000,
) -> None:
    """Print the command to launch the MLflow UI for inspecting traces."""
    root = project_root()
    cmd = launch_mlflow_ui(root, port)
    rprint(f"[bold]Run this command to start the MLflow UI:[/bold]\n\n  {cmd}\n")
    rprint(f"Then open http://localhost:{port} in your browser.")


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
    no_mlflow: Annotated[
        bool,
        typer.Option(
            "--no-mlflow",
            help="Disable MLflow tracing for this run (enabled by default).",
        ),
    ] = False,
) -> None:
    """Run the ReAct coding agent on a single SWE-bench task with evaluation."""
    root = project_root()
    config = OpenRouterConfig.from_env(model=model)
    mlflow_flag: bool | None = False if no_mlflow else None
    result = run_one_task(
        project_root=root,
        instance_id=instance_id,
        config=config,
        max_iterations=max_iterations,
        agent_max_tokens=agent_max_tokens,
        evaluation_timeout=evaluation_timeout,
        enable_mlflow_tracing=mlflow_flag,
    )
    rprint(json.dumps(result, indent=2, ensure_ascii=False))
