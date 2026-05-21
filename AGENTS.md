# Agent Map

This repo is split between the evolving SWE-bench agent and the meta-optimization artifacts that guide future harness changes.

- Evolving agent code lives in `src/evolve2_agent_bench/agent/`.
- Benchmark orchestration lives in `src/evolve2_agent_bench/bench/`.
- Meta-agent experiment records live in `artifacts/meta/`.
- Run traces are written under `artifacts/runs/` and are ignored by git.

When writing complex features or significant refactors, use an ExecPlan as described in `docs/PLANS.md` from design to implementation.

Load OpenRouter credentials from local `.env` before benchmark work: `set -a; source .env; set +a`. Use `uv run evolve2 model-check` before benchmark work that depends on OpenRouter. Use `uv run evolve2 run-task --instance-id <id> --max-iterations 100 --evaluation-timeout 1800` for decision-grade one-task SWE-bench Verified runs. Do not set `--agent-max-tokens` unless the hypothesis is specifically about response budget.

To avoid Hugging Face Hub rate limits on dataset fetch, materialize SWE-bench Verified once (`scripts/materialize_swebench_verified.py`) and set `EVOLVE2_SWEBENCH_DATASET_ROOT` to that parent directory so tasks and evaluation load from disk (see README).

For MLflow-backed LangChain trace UI during benchmark runs: `uv sync --extra mlflow`, then `EVOLVE2_MLFLOW_TRACING=1` or `evolve2 run-task --mlflow` (see README).

For single-hypothesis meta-agent optimization work, start at [`docs/meta/README.md`](docs/meta/README.md) and follow [`docs/meta/prompt-executor.md`](docs/meta/prompt-executor.md) (and [`docs/meta/artifacts-schema.md`](docs/meta/artifacts-schema.md) for dossier/index shapes). Meta-optimization is **MCTS-style**: dossiers record nodes, sampled rollouts, values, and deferred child actions; see **Search tree (MCTS-style meta-optimization)** in [`docs/meta/prompt-orchestrator.md`](docs/meta/prompt-orchestrator.md). For multi-worker orchestration, use [`docs/meta/prompt-orchestrator.md`](docs/meta/prompt-orchestrator.md) as the `/goal` prompt. Work autonomously according to the role you are running: a hypothesis worker owns one branch and pushes that branch; an orchestrator owns worktree assignment, `hypotheses-board.json`, `meta-events.jsonl` (`sample.selected` only via orchestrator), and central publication to `main`. Ask only for hard blockers such as unavailable models, missing credentials, broken infrastructure, or conflicting user changes. Treat `artifacts/runs/<run_id>/trace.jsonl` as the canonical trace, `artifacts/meta/hypothesis-index.jsonl` as the central index, and `artifacts/meta/hypotheses/` as the full hypothesis record. Generate three candidate hypotheses with roles (exploit / explore / bridge), `trace_anchor`, and effort/result/confidence scores before choosing one (see [`docs/meta/prompt-proposer.md`](docs/meta/prompt-proposer.md)). Use `main` for the mainstream agent and `hyp/HXXXX-<slug>` branches for individual hypotheses. Push every completed hypothesis branch. Merge only confirmed hypotheses into `main` per Pareto rules in [`docs/meta/prompt-analyzer.md`](docs/meta/prompt-analyzer.md) and merge policy in [`docs/meta/prompt-orchestrator.md`](docs/meta/prompt-orchestrator.md) (including trace-targeted confirmations when named trace metrics improve and `patch_published` does not regress). Undeclared diagnostic tweaks without patch, solve-rate, or trace-targeted evidence are not enough to merge. Rejected or inconclusive code stays only on its hypothesis branch; central artifacts are published to `main` by the standalone worker or by the orchestrator, depending on mode.

Validate hypotheses in stages. Start with the one-task gate, promote only passing hypotheses to the fixed three-task gate, and ask the user for explicit approval before any full SWE-bench Verified run.
