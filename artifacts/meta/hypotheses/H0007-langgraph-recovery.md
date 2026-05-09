# H0007 LangGraph-Style Empty Response Recovery

Status: inconclusive

Branch: `hyp/H0007-langgraph-recovery`

Created: 2026-05-09
Updated: 2026-05-09

## Candidate Hypotheses Considered

| Candidate | Mechanism | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- |
| A | Add a LangGraph-style model-call recovery hook: if a model response is empty, immediately retry once with a terse schema reminder before classifying the iteration as invalid. | H0003 observed an empty model response; LangChain custom middleware docs describe wrapping model calls for retry; LangGraph fault-tolerance docs describe retries before error handling. | S | M | medium | Chosen because it targets empty model responses without widening the action parser or changing tools. |
| B | Convert the loop to LangChain `create_agent` with structured output for `AgentAction`. | LangChain structured-output docs describe provider/tool strategies for schema enforcement; prior parser failures show protocol fragility. | L | L | low | Rejected for this cycle because OpenRouter/model support is uncertain and the migration would change many surfaces at once. |
| C | Add a LangGraph state machine with explicit invalid-action and no-patch recovery nodes. | LangGraph fault-tolerance docs and H0004 no-patch behavior suggest explicit recovery states may help. | L | L | medium | Rejected for this cycle because it is broader than the immediate empty-response failure and would be hard to attribute on one task. |

## Hypothesis

If the agent retries an empty LangChain model response once with an explicit action-schema recovery prompt, then empty responses will stop consuming full agent iterations as invalid actions, measured by lower `invalid_action_count` and equal or better patch publication on `astropy__astropy-12907`.

## Motivation

Prior rejected parser experiments improved protocol metrics but did not publish a patch. H0003 specifically observed an empty model response after otherwise valid tool execution, and H0004 shows that simply accepting more action syntax does not address all control-loop recovery failures. LangChain custom middleware references describe wrap-style model-call retries, and LangGraph fault-tolerance references frame retries before error handling as a standard recovery mechanism. This hypothesis applies that mechanism narrowly inside the existing loop.

## Baseline Evidence

- Baseline branch/commit: `main` / `0a79213`
- Baseline run ids:
  - `20260508-182634-astropy__astropy-12907`
  - prior empty-response evidence: `20260508-180609-astropy__astropy-12907`
- Trace paths:
  - `artifacts/runs/20260508-182634-astropy__astropy-12907/trace.jsonl`
  - `artifacts/runs/20260508-180609-astropy__astropy-12907/trace.jsonl`
- Failure class: `no_patch` plus `invalid_action_protocol`
- Key observed events:
  - H0003 candidate saw one invalid action caused by an empty model response.
  - H0004 same-budget baseline saw `invalid_action_count=10`, `patch_bytes=0`, and `empty_patch_instances=1`.
  - H0004 parser recovery was rejected because improved invalid-action metrics did not produce a tracked source patch.

## Proposed Change

Change only `src/evolve2_agent_bench/agent/base.py`:

- wrap each LangChain model invocation in a narrow empty-response retry;
- retry at most once and only when `response.content` is empty after stripping;
- append an extra human recovery instruction for the retry;
- trace each attempt and a separate empty-response recovery event.

Non-goals:

- Do not add provider-style tool-call parsing.
- Do not migrate to LangChain `create_agent` or a full LangGraph graph.
- Do not change tools, benchmark orchestration, model, token limits, or evaluation settings.

## Test Plan

- Validation commands:
  - `uv run python -m compileall -q src scripts`
  - local monkeypatched model-call check that an empty first response triggers one retry
  - `uv run evolve2 model-check`
- Benchmark task ids:
  - `astropy__astropy-12907`
- Validation stage: one-task gate
- Max iterations / timeout:
  - `--max-iterations 100 --evaluation-timeout 1800`
- Agent max tokens: unset
- Metrics to compare:
  - resolved instances
  - patch bytes / empty patch instances
  - invalid actions
  - LLM calls
  - tool calls
  - wall seconds
  - prompt, completion, and total tokens
- Stop condition:
  - one decision-grade candidate run, or an exact infrastructure blocker documented as inconclusive.

## Expected Pareto Movement

- Primary metric: equal or better patch publication and resolved instances.
- Secondary metrics: fewer invalid actions caused by empty responses.
- Regression risks: if the model/provider returns empty responses repeatedly, the retry adds one extra LLM call and token cost without changing the no-patch outcome.

## Result

Implemented a narrow empty-response recovery hook in `BaselineLangChainAgent._invoke`:

- every model call is traced with `recovery_attempt`;
- if the first response content is empty after stripping, the agent appends a terse human recovery instruction and retries once;
- the retry path records `empty_model_response_recovery`.

Validation completed:

- `uv run python -m compileall -q src scripts`
- local monkeypatched model-call check confirmed one empty first response triggers exactly one retry;
- `uv run evolve2 model-check` returned `model-ok` after sourcing credentials from `../evolve2/.env` because this assigned worktree did not contain its own `.env`.

The one-task gate was attempted with:

```bash
set -a; source ../evolve2/.env; set +a; uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 100 --evaluation-timeout 1800
```

Candidate run `20260509-082534-astropy__astropy-12907` did not complete. The process exited with code 143 after iteration 17 and wrote no `result.json`, `patch.diff`, prediction, or evaluation logs. The trace is still useful as partial evidence: the empty-response recovery fired at iteration 13. The retry produced a non-empty `read_file` action targeting `astropy/modeling/separable.py`, but it used `max_lines=500`, which violates the current `ReadFileArgs.max_lines <= 400` schema. The action was therefore still recorded as `invalid_action`.

Because the decision-grade gate did not finish and no patch/evaluation result exists, this hypothesis is inconclusive rather than confirmed or rejected by benchmark outcome.

## Metrics

| Metric | Baseline | Candidate | Delta |
| --- | --- | --- | --- |
| Resolved instances | 0 | n/a | n/a |
| Patch published / patch bytes | no / 0 | no result | n/a |
| Empty patch instances | 1 | no result | n/a |
| Wall seconds | 291.792 | no result | n/a |
| Prompt tokens | 80820 | 67063 partial | n/a |
| Completion tokens | not recorded in H0004 table | 37223 partial | n/a |
| Total tokens | 80820 | 104286 partial | n/a |
| Invalid actions | 10 | 3 partial | n/a |
| Tool calls | 6 | 14 partial | n/a |

## Pareto Assessment

Inconclusive. The recovery mechanism activated and turned an empty model response into a non-empty model response, but the recovered action still failed schema validation. The run then terminated before patch creation and SWE-bench evaluation, so there is no comparable patch-publication, solve-rate, wall-time, or evaluation evidence.

Diagnostic evidence suggests the mechanism is too weak as implemented: an empty-response retry needs either stricter recovery instructions for bounded tool arguments or a schema repair path. That should be tested as a separate hypothesis rather than folded into H0007 after the incomplete gate.

## Decision

Keep unmerged. Do not promote to the three-task gate. Mark H0007 inconclusive because the decision-grade one-task gate terminated before result generation.

## Evidence Links

- Candidate run: `artifacts/runs/20260509-082534-astropy__astropy-12907/`
- Candidate trace: `artifacts/runs/20260509-082534-astropy__astropy-12907/trace.jsonl`
- Commit:
