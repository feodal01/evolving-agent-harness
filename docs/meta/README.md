# Meta-optimization docs (`docs/meta/`)

Role-based **agent prompts** and artifact schemas for MCTS-style harness evolution on the SWE-bench agent.

## Prompt files (one role = one file)

| Role | Prompt | Use when |
|------|--------|----------|
| Orchestrator | [prompt-orchestrator.md](prompt-orchestrator.md) | `/goal` — coordinates rounds, board, spawns subagents |
| Executor | [prompt-executor.md](prompt-executor.md) | Implements one hypothesis; **runs** benchmark gates |
| Analyzer | [prompt-analyzer.md](prompt-analyzer.md) | Reads finished runs; Pareto report only |
| Proposer | [prompt-proposer.md](prompt-proposer.md) | New/refill rows on the hypotheses board |
| Sampler | [prompt-sampler.md](prompt-sampler.md) | Picks next `hypothesis_id` (JSON to orchestrator) |

Schemas and dossier template: [artifacts-schema.md](artifacts-schema.md).

## Orchestrator spawn rule

When spawning a subagent, pass **only** that role’s prompt file plus the snapshot packet from [artifacts-schema.md](artifacts-schema.md) §3. Example: *“Operate using `docs/meta/prompt-executor.md`. Snapshot: …”*

## Related paths

- Agent: `src/evolve2_agent_bench/agent/`
- Runs: `artifacts/runs/<run_id>/`
- Meta: `artifacts/meta/` (`hypotheses-board.json`, `meta-events.jsonl`, dossiers)
