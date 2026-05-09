from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from rich import print

from evolve2_agent_bench.bench.swebench_runner import run_one_task
from evolve2_agent_bench.config import DEFAULT_MODEL, OpenRouterConfig


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
        default_headers={
            "HTTP-Referer": "http://localhost/evolve2",
            "X-Title": "evolve2-model-check",
        },
    )
    response = llm.invoke([HumanMessage(content="Reply with exactly: model-ok")])
    print(str(response.content).strip())


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
        int,
        typer.Option(min=256, help="Maximum completion tokens for each agent LLM call."),
    ] = 4096,
    evaluation_timeout: Annotated[int, typer.Option(min=60)] = 1800,
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
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
