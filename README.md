# Evolve2

Evolve2 is a long-running experiment in self-improving coding agents.

The project starts with a deliberately small SWE-bench agent, then lets a meta-agent improve the harness around it: tools, prompts, tracing, validation, and recovery behavior. Every attempted improvement becomes an episode with a hypothesis, a branch, a benchmark run, and a verdict.

The fun part is not a polished final score. It is watching the agent learn how to become a better agent.

## Watch The Run

- **Live show page:** [feodal01.github.io/evolving-agent-harness](https://feodal01.github.io/evolving-agent-harness/) ([source](docs/show/index.html))
- **Current board:** [artifacts/meta/hypotheses-board.json](artifacts/meta/hypotheses-board.json)
- **Hypothesis archive:** [artifacts/meta/hypotheses](artifacts/meta/hypotheses)
- **Operator manual:** [docs/meta/README.md](docs/meta/README.md)

When GitHub Pages is enabled for this repository, the show page is deployed by `.github/workflows/showcase.yml` on every `main` update. It turns the meta-agent's ledger into a public scoreboard and episode feed.

## The Premise

Most agent progress is invisible: a prompt changes, a tool gets stricter, a failed run disappears into logs. Evolve2 makes that process visible.

Each round asks:

1. What failure did the latest trace expose?
2. What small harness change might move the frontier?
3. Did it publish a patch, solve a task, or reveal a better next move?
4. Should the change merge, stay as evidence, or become a deferred branch in the search tree?

The meta-agent is not allowed to rely on chat memory. Its memory is the repository: dossiers, events, traces, branches, and benchmark outputs.

## Why It Matters

Large models can hide weak harnesses. Small models expose them.

Evolve2 uses a small model by default and puts pressure on the surrounding system: action interfaces, file-editing affordances, feedback loops, observability, and benchmark discipline. A small improvement that turns an empty diff into a real patch is a visible step forward.

The first major breakthrough was H0022: blocking untracked scratch-file writes. After many zero-patch runs, the agent finally produced a non-empty SWE-bench patch. It still did not solve the task, but it crossed a structural threshold: from talking about fixes to submitting diffs.

## How To Read The Repository

- `artifacts/meta/hypotheses/*.md` are episode dossiers.
- `artifacts/meta/meta-events.jsonl` is the chronological production log.
- `artifacts/meta/hypotheses-board.json` is the current season board.
- `src/evolve2_agent_bench/agent/` is the evolving coding agent.
- `src/evolve2_agent_bench/bench/` runs SWE-bench Verified tasks.
- `docs/meta/` contains the operating prompts for the meta-agent.

## Run It Locally

```bash
uv sync
set -a
source .env
set +a
uv run evolve2 model-check
uv run evolve2 dataset-status
uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 100 --evaluation-timeout 1800
```

SWE-bench Verified must be materialized locally before benchmark runs. Use `uv run evolve2 materialize-dataset` if `dataset-status` says it is missing.

MLflow tracing is enabled by default:

```bash
uv run evolve2 mlflow-ui
```

## Build The Show Page

```bash
uv run python scripts/build_showcase.py
```

The generated page is `docs/show/index.html`. The GitHub Pages workflow runs the same command before deployment.

## Status

Evolve2 is intentionally unfinished. The goal is to make the improvement process legible enough that people can follow the arc: failed ideas, small discoveries, merged mechanics, and the next bet.
