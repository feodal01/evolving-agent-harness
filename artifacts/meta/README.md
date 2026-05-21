# Meta Artifacts

This directory stores durable memory for the meta-LLM.

- `hypothesis-index.jsonl`: compact append-only index of hypothesis ids and dossier paths.
- `hypotheses-board.json`: operational board for multi-role meta flow (orchestrator-owned; see `docs/meta/artifacts-schema.md`).
- `meta-events.jsonl`: append-only orchestration and worker events (see `docs/meta/artifacts-schema.md`).
- `hypotheses/<id>.md`: full lifecycle dossier for each hypothesis, from proposal through result. Dossiers follow an **MCTS-style ledger**: **Search node (MCTS)** records parent state, rollout depth, value summary, deferred child actions, and revisit queue (see `docs/meta/artifacts-schema.md` Appendix B).
- `hypotheses/TEMPLATE.md`: copy this when creating a new hypothesis dossier.
- `experiment-ledger.jsonl`: legacy baseline ledger from the initial bootstrap. New hypotheses should use the index plus dossier format.

Use `docs/meta/README.md` and the role prompts it indexes. Do not copy full traces here; reference `artifacts/runs/<run_id>/trace.jsonl` instead.
