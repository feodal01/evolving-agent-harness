# Agent Map

This repo is split between the evolving SWE-bench agent and the meta-optimization artifacts that guide future harness changes.

- Evolving agent code lives in `src/evolve2_agent_bench/agent/`.
- Benchmark orchestration lives in `src/evolve2_agent_bench/bench/`.
- Meta-agent experiment records live in `artifacts/meta/`.
- Run traces are written under `artifacts/runs/` and are ignored by git.

When writing complex features or significant refactors, use an ExecPlan as described in `docs/PLANS.md` from design to implementation.

Load OpenRouter credentials from local `.env` before benchmark work: `set -a; source .env; set +a`. Use `uv run evolve2 model-check` before benchmark work that depends on OpenRouter. Use `uv run evolve2 run-task --instance-id <id> --max-iterations 100 --evaluation-timeout 1800` for decision-grade one-task SWE-bench Verified runs. Do not set `--agent-max-tokens` unless the hypothesis is specifically about response budget.

For meta-agent optimization work, read `docs/META_OPTIMIZATION.md` first and follow it without needing extra chat instructions. Work autonomously: choose branch names, create commits, and push branches/main according to the manual without asking the user for routine approval. Ask only for hard blockers such as unavailable models, missing credentials, broken infrastructure, or conflicting user changes. Treat `artifacts/runs/<run_id>/trace.jsonl` as the canonical trace, `artifacts/meta/hypothesis-index.jsonl` as the central index, and `artifacts/meta/hypotheses/` as the full hypothesis record. Generate three candidate hypotheses with effort/result/confidence scores before choosing one. Use `main` for the mainstream agent and `hyp/HXXXX-<slug>` branches for individual hypotheses. Push every completed hypothesis branch. Merge only confirmed hypotheses into `main`; diagnostic progress without patch publication or solve-rate improvement is not enough. For rejected or inconclusive hypotheses, push the branch, then update only the central hypothesis artifacts on `main` and push `main`.

Validate hypotheses in stages. Start with the one-task gate, promote only passing hypotheses to the fixed three-task gate, and ask the user for explicit approval before any full SWE-bench Verified run.
