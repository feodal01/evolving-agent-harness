# Agent Map

This repo is split between the evolving SWE-bench agent and the meta-optimization artifacts that guide future harness changes.

- Evolving agent code lives in `src/evolve2_agent_bench/agent/`.
- Benchmark orchestration lives in `src/evolve2_agent_bench/bench/`.
- Meta-agent experiment records live in `artifacts/meta/`.
- Run traces are written under `artifacts/runs/` and are ignored by git.

When writing complex features or significant refactors, use an ExecPlan as described in `docs/PLANS.md` from design to implementation.

Use `uv run evolve2 model-check` before benchmark work that depends on OpenRouter. Use `uv run evolve2 run-task --instance-id <id>` for one-task SWE-bench Verified runs.

For meta-agent optimization work, read `docs/META_OPTIMIZATION.md` first. Treat `artifacts/runs/<run_id>/trace.jsonl` as the canonical trace and `artifacts/meta/experiment-ledger.jsonl` as the central hypothesis ledger. Use `main` for the mainstream agent and `hyp/<date>-<slug>` branches for individual hypotheses; merge only confirmed hypotheses and keep rejected branches.
