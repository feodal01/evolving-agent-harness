# Meta-optimization docs (`docs/meta/`)

Entry point for **role-based** meta-optimization prompts and artifact schemas. Legacy `docs/META_OPTIMIZATION.md` and `docs/ORCHESTRATOR_PROMPT.md` were removed; all instructions live here.

## Files

| Path | Use as |
|------|--------|
| [artifacts-schema.md](artifacts-schema.md) | Canonical schemas: `hypotheses-board.json`, `meta-events.jsonl`, snapshot contract, dossier template appendix, `hypothesis-index.jsonl` appendix. |
| [prompt-orchestrator.md](prompt-orchestrator.md) | **`/goal` for the orchestrator** — board + events authority, merge to `main`, parallel rounds, BPMN flow reference. |
| [prompt-executor.md](prompt-executor.md) | Hypothesis worker implementing one branch and bench gates. |
| [prompt-proposer.md](prompt-proposer.md) | Idea generation (exploit/explore/bridge, references). |
| [prompt-sampler.md](prompt-sampler.md) | MCTS-style row selection; **JSON only** to orchestrator (no `sample.selected` append). |
| [prompt-analyzer.md](prompt-analyzer.md) | Trace + Pareto analysis reports; **no merge authority**. |

## BPMN (orchestrator-first)

The orchestrator starts each round, owns `hypotheses-board.json`, and is the **only** writer of `sample.selected` in `meta-events.jsonl`. See the diagram in [prompt-orchestrator.md](prompt-orchestrator.md) § “BPMN process”.

## Quick start

1. Orchestrator: open `prompt-orchestrator.md` as `/goal`.
2. Load `artifacts-schema.md` before editing meta files.
3. Point subagents at **their** prompt file only (not the orchestrator prompt).

## Related code paths

- Agent: `src/evolve2_agent_bench/agent/`
- Bench: `src/evolve2_agent_bench/bench/`
- Runs: `artifacts/runs/<run_id>/`
- Meta: `artifacts/meta/`
