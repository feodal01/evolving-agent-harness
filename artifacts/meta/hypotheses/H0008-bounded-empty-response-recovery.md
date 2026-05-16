# H0008 Bounded Empty Response Recovery

Status: running

Branch: `hyp/H0008-bounded-empty-response-recovery`

Created: 2026-05-16
Updated: 2026-05-16

## Hypothesis

If, after a LangChain model returns an empty string, the agent retries once with an explicit reminder that `read_file` must use `max_lines` at most 400 (and optionally caps oversized `max_lines` before validation), then recovery stops producing schema-invalid reads and reduces wasted `invalid_action` iterations on `astropy__astropy-12907`, measured by `invalid_action` count and patch publication vs baseline.

## Motivation

H0007 (`hyp/H0007-langgraph-recovery`) showed empty-response recovery working, but the retry produced `read_file` with `max_lines=500`, which violates `ReadFileArgs` (`le=400`) and still counted as `invalid_action`. Slot A tightens recovery so the model is nudged toward schema-valid reads without widening the parser elsewhere.

## Baseline Evidence

- Baseline branch/commit: see H0007 dossier / `main` context at parent
- Baseline run ids:
  - `20260508-182634-astropy__astropy-12907`
  - (H0007 partial) `20260509-082534-astropy__astropy-12907`
- Trace paths (if present locally):
  - `artifacts/runs/20260508-182634-astropy__astropy-12907/trace.jsonl`
  - `artifacts/runs/20260509-082534-astropy__astropy-12907/trace.jsonl`
- Failure class: empty model response → recovery → schema-invalid `read_file` (`max_lines` > 400)
- Key observed events: `empty_model_response_recovery` then `invalid_action` due to `max_lines` bound (H0007 dossier)

## Candidate Hypotheses Considered

| Candidate | Role | Mechanism | Trace anchor | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | exploit | H0007-style empty retry + explicit `max_lines<=400` reminder; narrow cap on parsed `read_file` args | strong | H0007 dossier | S | fewer post-recovery invalid actions | high | chosen (this branch) |
| B | explore | Widen `ReadFileArgs` to `le=800` | medium | schema change | S | fewer invalid | low | rejected — hides bounds discipline |
| C | bridge | Full LangGraph invalid-action node | weak | literature | L | unknown | low | rejected — out of scope for Slot A |

## Proposed Change

- `src/evolve2_agent_bench/agent/base.py` only:
  - Refactor `_invoke` to match H0007 (`_invoke_once`, `recovery_attempt` in `llm_call`, `empty_model_response_recovery` agent event).
  - Recovery human message explicitly states `read_file` / `max_lines` must be between 1 and 400 inclusive, and asks for one valid JSON action.
  - Light repair: when a JSON blob parses to `action: read_file` and `args.max_lines` is a number `> 400`, set `max_lines` to 400 before `AgentAction` validation (trace-targeted; no other fields).

Non-goals: tool changes, benchmark harness changes, `SYSTEM_PROMPT` rewrites beyond clarifying the read-file bound in the recovery line if needed.

## Test Plan

- Validation: `uv run python -m compileall -q src scripts`; `uv run evolve2 model-check` (with `.env`)
- Benchmark: `uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 100 --evaluation-timeout 1800` (agent_max_tokens unset)
- Stage: one-task gate only
- Metrics: resolved, patch bytes, invalid actions, LLM/tool calls, wall time, tokens (from `summarize_trace.py` / `result.json`)

## Expected Pareto Movement

- Primary: same or better patch publication and resolved on the gate task
- Secondary: fewer invalid actions after empty-response recovery; no regression in iteration/token efficiency
- Regression risk: extra LLM call on empty responses; repair could mask model behavior (bounded to `max_lines` only)

## Result

Fill after running.

## Metrics

| Metric | Baseline | Candidate | Delta |
| --- | --- | --- | --- |
| Resolved instances | | | |
| Patch published / patch bytes | | | |
| Empty patch instances | | | |
| Wall seconds | | | |
| Prompt tokens | | | |
| Completion tokens | | | |
| Total tokens | | | |
| Invalid actions | | | |
| Tool calls | | | |

## Pareto Assessment

Fill after running.

## Decision

Fill after running.

## Search node (MCTS)

- **Parent state**: branched from `main`; parent hypothesis context H0007 (inconclusive empty recovery + invalid `max_lines`).
- **State fingerprint**: empty LLM content → single retry → schema-invalid `read_file` over 400 lines.
- **Children considered**: A expanded (this run); B/C deferred/abandoned per table.
- **Rollout depth**: `one-task`; baseline run ids cited above; candidate: fill after run.
- **Value summary**: fill after metrics.
- **Revisit queue**: none yet.

## Evidence Links

- Candidate run: fill
- Candidate trace: fill
- Commit: fill
