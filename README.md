# evolve2-agent-bench

Python harness for evolving a LangChain coding agent against SWE-bench Verified.

The project has two separated surfaces:

- `src/evolve2_agent_bench/agent/`: the baseline agent that is evaluated and evolved.
- `docs/META_OPTIMIZATION.md` plus `artifacts/meta/`: the self-contained meta-agent manual and central hypothesis ledger.

## Setup

```bash
uv sync
export OPENROUTER_API_KEY=...
```

The default model is `google/gemma-4-26b-a4b-it` through OpenRouter.

## Smoke Check

```bash
uv run evolve2 model-check
```

## Run One SWE-bench Verified Task

```bash
uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 8
```

Each run writes a directory under `artifacts/runs/<run_id>/` containing:

- `trace.jsonl`: canonical unified timeline with task input, LLM messages, model responses, parsed actions, tool calls, tool outputs, errors, patch, prediction, and evaluation summary.
- `task.json`: public SWE-bench instance fields given to the agent. Gold patches and hidden evaluator fields are not written to run artifacts.
- `agent_events.jsonl`: high-level agent decisions.
- `llm_calls.jsonl`: model-specific slice of the unified trace.
- `shell_events.jsonl`: shell-specific slice of the unified trace.
- `patch.diff`: generated prediction patch.
- `prediction.jsonl`: SWE-bench prediction input.
- `evaluation_stdout.log` and `evaluation_stderr.log`: SWE-bench harness output.
- `result.json`: compact outcome summary.

Worktrees are created under `artifacts/worktrees/<run_id>/` and are intentionally ignored by git. The agent initializes git inside the checked-out task repository so patch generation is deterministic.

## Meta-Optimization Loop

The detailed self-contained meta-agent workflow is in `docs/META_OPTIMIZATION.md`.
Offline LangChain and LangGraph references are stored under `docs/references/langchain/` so meta-agent hypotheses can use current framework capabilities without internet access.
The research frame for generating hypothesis families is stored in `docs/references/research/agent-evolution-literature.md`.

After every run, append a record to `artifacts/meta/experiment-ledger.jsonl`. The expected meta-agent workflow is:

1. Create a hypothesis branch from `main`.
2. Inspect `result.json`, `trace.jsonl`, and only the relevant secondary slices.
3. Classify the failure mode or success mechanism.
4. Propose one narrow harness change with a measurable hypothesis.
5. Re-run a fixed task subset and compare Pareto metrics: resolved count, wall time, token usage, tool calls, patch size, and failure class.
6. Record the outcome in `artifacts/meta/experiment-ledger.jsonl`.
7. Merge only confirmed hypotheses into `main`; keep failed branches for history.

Large traces stay in per-run JSONL files; the meta ledger stores references and metrics, not copied traces.
