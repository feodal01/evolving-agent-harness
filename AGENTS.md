# Agent Map

This repo contains the evolving SWE-bench coding agent and the meta-optimization system that drives its improvement.

## Architecture

- **Evolving agent**: `src/evolve2_agent_bench/agent/` — LangGraph ReAct agent with shell, read_file, write_file tools.
- **Benchmark harness**: `src/evolve2_agent_bench/bench/` — offline SWE-bench Verified runner with auto-enabled MLflow tracing.
- **Meta-optimization docs**: `docs/meta/` — MCTS-style hypothesis generation, execution, and analysis.
- **Run artifacts**: `artifacts/runs/<run_id>/` — JSONL traces, result.json, patches (git-ignored).
- **MLflow traces**: `artifacts/mlruns/` — auto-captured span hierarchies for every run (git-ignored).
- **Meta artifacts**: `artifacts/meta/` — hypotheses-board.json, hypothesis-index.jsonl, dossiers.

## Setup

```bash
uv sync
set -a; source .env; set +a
uv run evolve2 model-check
uv run evolve2 materialize-dataset
uv run evolve2 dataset-status
```

SWE-bench Verified must be materialized locally before running tasks. The harness does not fall back to HuggingFace Hub. Default location: `datasets/SWE-bench_Verified`. Override with `EVOLVE2_SWEBENCH_DATASET_ROOT`.

## Running tasks

```bash
uv run evolve2 run-task --instance-id <id> --max-iterations 100 --evaluation-timeout 1800
```

MLflow tracing is auto-enabled. Disable with `--no-mlflow` or `EVOLVE2_MLFLOW_TRACING=0`. View traces: `uv run evolve2 mlflow-ui` → http://localhost:5050 (avoid 5000 on macOS — AirPlay).

Do not set `--agent-max-tokens` unless the hypothesis is specifically about response budget.

## Meta-optimization

Use [`docs/meta/prompt-unified.md`](docs/meta/prompt-unified.md) as the `/goal` prompt for the single meta-optimization agent. The unified agent performs all phases (orchestration, proposal, execution, analysis, decision) sequentially. Start at [`docs/meta/README.md`](docs/meta/README.md) for orientation.

Meta-optimization is **MCTS-style**: dossiers record search nodes with sampled rollouts, values, and deferred child actions. See [`docs/meta/artifacts-schema.md`](docs/meta/artifacts-schema.md) Appendix B for the dossier template including Search node (MCTS).

### Key rules

- Generate three candidate hypotheses with roles (exploit / explore / bridge), `trace_anchor`, `fix_type`, and effort/result/confidence scores before choosing one (see [`docs/meta/prompt-proposer.md`](docs/meta/prompt-proposer.md)).
- **Classify hypotheses**: `mechanical` (cheap fix, one-task gate only) vs `hypothesis` (full validation ladder with baseline comparison). This prevents burning budget on trivial fixes.
- **Research scan**: Before proposing hypotheses, review reference agents (SWE-agent, Aider, OpenHands, Moatless), LangChain/LangGraph docs, and research literature. Narrow trace-only hypotheses without external grounding are a sign of insufficient research.
- Use `main` for the mainstream agent and `hyp/HXXXX-<slug>` branches for individual hypotheses.
- Push every completed hypothesis branch. Merge only confirmed hypotheses into `main` per Pareto rules in [`docs/meta/prompt-analyzer.md`](docs/meta/prompt-analyzer.md).
- Validate in stages: one-task gate → batch gate → (user approval) → full evolution set → (user approval) → test set.
- Ask only for hard blockers (unavailable models, missing credentials, broken infrastructure) and full-benchmark approval.

### Validation protocol

- The 500 SWE-bench Verified instances are split into a 336-instance **evolution set** and a 164-instance **test set** (2/3 + 1/3 stratified by project). See [`docs/VALIDATION_POLICY.md`](docs/VALIDATION_POLICY.md).
- Instance assignments are in [`artifacts/meta/validation-sets.json`](artifacts/meta/validation-sets.json). Read this file to find the active batch.
- **NEVER** run or inspect test-set instances during evolution. The test set is unlocked only with human consent after the evolution set is fully resolved or a 20-attempt plateau is confirmed.
- The evolution set is organized into 56 batches of 6. Batch 0 contains 3 resolved + 3 new instances (status: active). The agent works through one batch at a time.
- Batch expansion: when the active batch is fully resolved, or after 20 consecutive no-improvement attempts, the next locked batch becomes active.
- `no_improvement_count` in `validation-sets.json` tracks consecutive no-improvement attempts and resets on any Pareto improvement.

### Observability

- **JSONL traces**: `artifacts/runs/<run_id>/trace.jsonl` is the canonical trace.
- **MLflow spans**: Every LLM call, tool invocation, and evaluation is captured as MLflow spans.
- **Meta-events**: `artifacts/meta/meta-events.jsonl` records all meta-optimization actions.
- **Hypothesis dossiers**: `artifacts/meta/hypotheses/` contains full hypothesis lifecycle records.
- **Hypothesis index**: `artifacts/meta/hypothesis-index.jsonl` is the compact status lookup.
