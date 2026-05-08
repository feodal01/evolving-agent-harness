# Meta Artifacts

This directory stores durable memory for the meta-LLM.

- `hypothesis-index.jsonl`: compact append-only index of hypothesis ids and dossier paths.
- `hypotheses/<id>.md`: full lifecycle dossier for each hypothesis, from proposal through result.
- `hypotheses/TEMPLATE.md`: copy this when creating a new hypothesis dossier.
- `experiment-ledger.jsonl`: legacy baseline ledger from the initial bootstrap. New hypotheses should use the index plus dossier format.

Use `docs/META_OPTIMIZATION.md` for the operating workflow. Do not copy full traces here; reference `artifacts/runs/<run_id>/trace.jsonl` instead.
