# H0015 Checkpointed Finalization Resume

Status: inconclusive

Branch: `hyp/H0015-checkpointed-finalization-resume`

Created: 2026-05-21
Updated: 2026-05-21

## Hypothesis

If the agent persists a compact edit-confirmation checkpoint after the first few iterations and restores that checkpoint when a run resumes, then clean-diff finalization will stop losing progress across interruptions and the agent will be more likely to reach a real tracked patch before finishing on `astropy__astropy-12907`, measured by lower `empty_patch_instances`, higher `patch_bytes`, and stable `resolved_instances`.

## Motivation

The latest comparable trace on `astropy__astropy-12907` still ends with `patch_bytes = 0`, `empty_patch_instances = 1`, and an `agent_stop` after four iterations. H0014 already makes termination more explicit, but this follow-up tests the resume path: if the agent reaches a finalization checkpoint and then has to continue later, the checkpoint state should survive and keep the tracked-diff context visible.

## Baseline Evidence

- Baseline branch/commit: `main` @ `0cf10077bb2d447f8216e3c6f7c671e6d6f627c3`
- Baseline run ids:
  - `20260517-124357-astropy__astropy-12907`
- Trace paths:
  - `artifacts/runs/20260517-124357-astropy__astropy-12907/trace.jsonl`
- Result paths:
  - `artifacts/runs/20260517-124357-astropy__astropy-12907/result.json`
- Failure class: `no_patch` / early stop without finish
- Key observed events:
  - `agent_stop` after 4 iterations
  - `patch_created` with `patch_bytes = 0`
  - `evaluation_finish.report.empty_patch_instances = 1`

## Candidate Hypotheses Considered

| Candidate | Role (exploit / explore / bridge) | Mechanism | Trace anchor (strong / medium / weak) | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | exploit | Persist a compact edit-confirmation checkpoint after iteration 3 and restore it on the next run so finalization resumes from the same tracked-diff state. | strong | Latest comparable trace plus H0014 checkpointed-finalization queue. | S | M | medium | chosen because it is the smallest resume mechanism that preserves the finalization context across interruptions. |
| B | explore | Recast the agent loop as a LangGraph state machine with short-term memory and a checkpointer, so the ready-to-finish state is managed by graph persistence. | medium | LangGraph persistence / fault-tolerance docs and the same no-patch trace. | M | L | medium | deferred because it is broader than the one-task gate and harder to attribute on a single trace. |
| C | bridge | Rehydrate the last diff-confirmation snapshot at startup and replay the last observation before continuing, similar to time-travel / forked resume. | medium | LangGraph time-travel docs plus the same no-patch trace. | M | M | low | deferred because it overlaps A but adds replay semantics that are not needed for the smallest test. |

## Proposed Change

- Smallest surface: `src/evolve2_agent_bench/agent/base.py`.
- Persist a compact checkpoint outside the task repo, keyed to the run workspace, after each turn.
- Include the current conversation state, iteration number, and finalization checkpoint metadata in that persisted state.
- On startup, reload the checkpoint if it exists so a resumed run continues from the last edit-confirmation state instead of rebuilding context from scratch.
- Keep the current action protocol and benchmark harness unchanged.

Non-goals:

- Do not add new agent actions or tools.
- Do not change SWE-bench evaluation or the patch extraction step.
- Do not edit the task repository to store checkpoint files.
- Do not widen the benchmark profile or token limits.

## Test Plan

- Validation commands:
  - `uv run python -m compileall -q src scripts`
  - focused unit test for checkpoint save/load and resume state
  - `uv run evolve2 model-check`
- Benchmark task ids:
  - one-task gate: `astropy__astropy-12907`
- Validation stage: one-task gate
- Max iterations / timeout: `--max-iterations 100 --evaluation-timeout 1800`
- Agent max tokens: unset
- Metrics to compare:
  - resolved instances
  - patch bytes
  - empty patch instances
  - wall seconds
  - prompt, completion, and total tokens
  - invalid actions
  - tool calls
- Stop condition:
  - one decision-grade candidate run completes, or a concrete runtime blocker is documented as inconclusive.

## Expected Pareto Movement

- Primary metric: lower `empty_patch_instances` and higher `patch_bytes`
- Secondary metrics: stable `resolved_instances`, no material invalid-action regression, no large increase in tool calls
- Regression risks: checkpoint persistence may add a small amount of prompt context, but it should preserve useful finalization state across interruptions.

## Result

The one-task gate was started as run `20260521-095642-astropy__astropy-12907`, but the harness stalled before the first LLM call and produced no `result.json`, `patch.diff`, or evaluation report. The trace currently stops after `agent_start`, so this branch has no decision-grade benchmark outcome yet.

## Metrics

| Metric | Baseline | Candidate | Delta |
| --- | --- | --- | --- |
| Resolved instances | 0 | n/a, gate incomplete | n/a |
| Patch published / patch bytes | 0 / 0 | no `patch.diff` produced | n/a |
| Empty patch instances | 1 | n/a, no evaluation report | n/a |
| Wall seconds | 26.002 | n/a | n/a |
| Prompt tokens | n/a | 0 partial | n/a |
| Completion tokens | n/a | 0 partial | n/a |
| Total tokens | n/a | 0 partial | n/a |
| Invalid actions | n/a | 0 partial | n/a |
| Tool calls | n/a | 0 partial | n/a |

## Pareto Assessment

Inconclusive. The code path compiles and the checkpoint resume test passes locally, but the benchmark gate stalled before the first model response, so there is no comparison data for patch publication, solve rate, or trace-health movement.

## Decision

Keep unmerged pending rerun.

## Search node (MCTS)

- Parent state: `main` @ `0cf10077bb2d447f8216e3c6f7c671e6d6f627c3`, parent hypothesis context `H0011`.
- State fingerprint: no-patch finalization failure with an early stop after four iterations and zero patch bytes.
- Children considered: A expanded on this branch; B and C deferred.
- Rollout depth: `one-task`.
- Value summary: the branch is intended to preserve the finalization checkpoint across interruptions so the agent can resume from the same edit-confirmation context instead of losing progress; the current gate did not reach a model call.
- Revisit queue:
  - If checkpointed resume still yields clean exits, defer to the harder diff-gated finalization branch in H0014/H0016.

## Evidence Links

- Candidate trace: `artifacts/runs/20260517-124357-astropy__astropy-12907/trace.jsonl`
- Candidate result: `artifacts/runs/20260517-124357-astropy__astropy-12907/result.json`
- Partial run: `artifacts/runs/20260521-095642-astropy__astropy-12907/trace.jsonl`
- Parent hypothesis: `artifacts/meta/hypotheses/H0011-hard-finalization-diff-gate.md`
- LangGraph references: `docs/references/langchain/curated/langgraph-fault-tolerance.md`, `docs/references/langchain/curated/langgraph-add-memory.md`, `docs/references/langchain/curated/langgraph-time-travel.md`
