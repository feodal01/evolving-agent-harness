# Agent Map

This repo is split between the evolving SWE-bench agent and the meta-optimization artifacts that guide future harness changes.

- Evolving agent code lives in `src/evolve2_agent_bench/agent/`.
- Benchmark orchestration lives in `src/evolve2_agent_bench/bench/`.
- Meta-agent experiment records live in `artifacts/meta/`.
- Run traces are written under `artifacts/runs/` and are ignored by git.

When writing complex features or significant refactors, use an ExecPlan as described in `docs/PLANS.md` from design to implementation.

Use `uv run evolve2 model-check` before benchmark work that depends on OpenRouter. Use `uv run evolve2 run-task --instance-id <id>` for one-task SWE-bench Verified runs.

For meta-agent optimization work, read `docs/META_OPTIMIZATION.md` first and follow it without needing extra chat instructions. Treat `artifacts/runs/<run_id>/trace.jsonl` as the canonical trace, `artifacts/meta/hypothesis-index.jsonl` as the central index, and `artifacts/meta/hypotheses/` as the full hypothesis record. Use `main` for the mainstream agent and `hyp/HXXXX-<slug>` branches for individual hypotheses. Push every completed hypothesis branch. Merge only confirmed hypotheses into `main`; for rejected or inconclusive hypotheses, push the branch, then update only the central hypothesis artifacts on `main` and push `main`.
