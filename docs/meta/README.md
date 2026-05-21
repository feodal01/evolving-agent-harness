# Meta-optimization docs (`docs/meta/`)

MCTS-style harness evolution for the SWE-bench coding agent, operated by a **single unified agent**.

## Unified workflow (v0.2+)

The meta-optimization loop is run by one agent that follows all phases sequentially:

| Phase | What happens | Reference |
|-------|-------------|-----------|
| 1. Round setup | Checkout main, verify env, read board | [prompt-unified.md](prompt-unified.md) §1 |
| 2. Hypothesis generation | Research scan, generate 3 candidates, classify fix_type | [prompt-unified.md](prompt-unified.md) §2, [prompt-proposer.md](prompt-proposer.md) |
| 3. Execution | Branch, implement, validate (ladder depends on fix_type) | [prompt-unified.md](prompt-unified.md) §3, [prompt-executor.md](prompt-executor.md) |
| 4. Analysis | Pareto comparison, MLflow trace inspection | [prompt-unified.md](prompt-unified.md) §4, [prompt-analyzer.md](prompt-analyzer.md) |
| 5. Decision | Merge / reject / keep, publish registry | [prompt-unified.md](prompt-unified.md) §5 |
| 6. Next round | Continue or stop | [prompt-unified.md](prompt-unified.md) §6 |

**Start here**: use [prompt-unified.md](prompt-unified.md) as the `/goal` prompt for the meta-optimization agent.

## Role-specific reference prompts

| Role | Prompt | Use when |
|------|--------|----------|
| Unified | [prompt-unified.md](prompt-unified.md) | **Primary operating manual** — all phases, merge decisions, autonomy |
| Executor | [prompt-executor.md](prompt-executor.md) | Implementation, git workflow, validation ladder |
| Analyzer | [prompt-analyzer.md](prompt-analyzer.md) | Trace analysis, Pareto comparison, trace-targeted rules |
| Proposer | [prompt-proposer.md](prompt-proposer.md) | Hypothesis generation, research scan, candidate scoring |
| Sampler | [prompt-sampler.md](prompt-sampler.md) | MCTS selection policy |

Schemas and dossier template: [artifacts-schema.md](artifacts-schema.md).

## Key changes in v0.2

1. **Single agent**: One agent reads the relevant prompt section at each phase.
2. **ReAct coding agent**: LangGraph ReAct agent with native tool calling (shell, read_file, write_file).
3. **MLflow required**: Tracing is auto-enabled for every run. View with `uv run evolve2 mlflow-ui`.
4. **Offline SWE-bench**: Dataset must be materialized locally. No HuggingFace Hub fallback.
5. **Fix types**: `mechanical` (cheap, one-task validation) or `hypothesis` (full validation ladder).
6. **Broader research**: Mandatory external research scan before hypothesis generation.

## Related paths

See [prompt-unified.md](prompt-unified.md) §System overview for full path listing.
