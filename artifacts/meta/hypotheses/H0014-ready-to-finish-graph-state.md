# H0014 Ready-To-Finish Graph State

Status: running

Branch: `hyp/H0014-ready-to-finish-graph-state`

Created: 2026-05-21
Updated: 2026-05-21

## Hypothesis

If the agent exposes an explicit `ready_to_finish` control state that is recomputed from the tracked source diff and patch confirmation before termination, then the model will stop treating finish as a prompt convention and will be more likely to produce a real tracked patch before finalization on `astropy__astropy-12907`, measured by lower `empty_patch_instances`, higher `patch_bytes`, and stable `resolved_instances`.

## Motivation

The latest comparable trace on `astropy__astropy-12907` stopped after four iterations with `patch_bytes = 0`, `empty_patch_instances = 1`, and no finish action. H0011 already hardened finish on a clean diff, but that still leaves the control flow implicit; this branch makes the termination condition an explicit state transition.

## Baseline Evidence

- Baseline branch/commit: `main` @ `0cf10077bb2d447f8216e3c6f7c671e6d627c3`
- Baseline run ids: `20260517-124357-astropy__astropy-12907`
- Trace paths: `artifacts/runs/20260517-124357-astropy__astropy-12907/trace.jsonl`
- Result paths: `artifacts/runs/20260517-124357-astropy__astropy-12907/result.json`
- Failure class: clean worktree / empty patch / early stop without finish
- Key observed events: `agent_stop` after 4 iterations, `patch_bytes=0`, `empty_patch_instances=1`, `resolved_instances=0`

## Candidate Hypotheses Considered

| Candidate | Role (exploit / explore / bridge) | Mechanism | Trace anchor (strong / medium / weak) | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | exploit | Add an explicit `ready_to_finish` state to the loop, recompute it from tracked source diff / patch confirmation, and block finish until that state is true. | strong | Latest comparable trace plus H0011 revisit queue. | S | M | medium | chosen because it is the smallest state-control refinement that directly targets the no-patch termination path. |
| B | explore | Rewrite the agent loop as a more explicit graph-style state machine with separate observe/edit/finish phases and a dedicated finish node. | medium | LangGraph control docs plus the same no-patch trace. | M | L | medium | deferred because it is broader than the one-task gate needs. |
| C | bridge | Keep the current loop but add a forced checkpoint after iteration 3 that must report patch confirmation before any finish path can execute. | strong | Latest comparable trace and prior source-edit-finalization hypotheses. | S | M | medium | deferred because it is a weaker version of explicit state gating. |

## Proposed Change

- Smallest surface: `src/evolve2_agent_bench/agent/base.py`.
- Add a compact control-state snapshot with `ready_to_finish` and update it after each action from the tracked diff / patch confirmation.
- Include the state snapshot in the model context so finish becomes a visible state transition rather than an implicit prompt rule.
- Keep the existing action protocol and tool surface unchanged.
- Non-goals: do not add new tools, do not expand retries, do not redesign the benchmark harness.

## Test Plan

- Validation stage: `one-task` gate.
- Benchmark task ids: `astropy__astropy-12907`
- Validation commands:
  - `uv run python -m compileall -q src scripts`
  - `set -a; source .env; set +a`
  - `uv run evolve2 model-check`
  - `uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 100 --evaluation-timeout 1800`
- Max iterations / timeout: `100` / `1800`
- Agent max tokens: unset
- Metrics to compare: `patch_bytes`, `empty_patch_instances`, `resolved_instances`, `invalid_actions`, `tool_calls`

## Expected Pareto Movement

- Primary metric: lower `empty_patch_instances` and higher `patch_bytes`
- Secondary metrics: stable or improved `resolved_instances`, no material invalid-action regression, no large increase in tool calls
- Regression risks: an explicit state snapshot may add prompt overhead, but it should reduce false finalization and empty exits

## Result

Pending one-task validation.

## Metrics

| Metric | Baseline | Candidate | Delta |
| --- | --- | --- | --- |
| Resolved instances | 0 | pending | pending |
| Patch published / patch bytes | 0 | pending | pending |
| Empty patch instances | 1 | pending | pending |
| Wall seconds | 26.002 | pending | pending |
| Prompt tokens | pending | pending | pending |
| Completion tokens | pending | pending | pending |
| Total tokens | pending | pending | pending |
| Invalid actions | pending | pending | pending |
| Tool calls | pending | pending | pending |

## Pareto Assessment

Pending benchmark completion.

## Decision

pending

## Search node (MCTS)

- Parent state: `main` @ `0cf10077bb2d447f8216e3c6f7c671e6d627c3`, parent hypothesis context `H0011`.
- State fingerprint: no-patch finalization failure on the latest comparable trace.
- Children considered: A expanded on this branch; B and C deferred.
- Rollout depth: `one-task`.
- Value summary: the branch is intended to make `ready_to_finish` explicit before termination, so the benchmark can only finish after a real tracked source diff is visible.
- Revisit queue: hard diff gate from H0011 if this branch still produces clean exits.

## Evidence Links

- Candidate trace: `artifacts/runs/20260517-124357-astropy__astropy-12907/trace.jsonl`
- Candidate result: `artifacts/runs/20260517-124357-astropy__astropy-12907/result.json`
- Parent hypothesis: `artifacts/meta/hypotheses/H0011-hard-finalization-diff-gate.md`
- LangGraph references: `docs/references/langchain/curated/langgraph-overview.md`, `docs/references/langchain/curated/langgraph-thinking.md`
