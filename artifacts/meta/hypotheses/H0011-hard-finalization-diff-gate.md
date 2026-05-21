# H0011 Hard Finalization Diff Gate

Status: inconclusive

Branch: `hyp/H0011-hard-finalization-diff-gate`

Created: 2026-05-21
Updated: 2026-05-21

## Hypothesis

If the agent blocks `finish` unless a tracked source diff exists and `patch_bytes > 0`, then the no-patch loop ends earlier and the benchmark reaches real edit publication more often on `astropy__astropy-12907`, measured by `patch_bytes`, `empty_patch_instances`, and `resolved_instances`.

## Motivation

The latest comparable trace (`20260517-124357-astropy__astropy-12907`) stopped after 4 iterations with `patch_bytes=0` and `empty_patch_instances=1`. H0006 and H0010 already point at the same no-patch / finalization failure class; this branch hardens the termination path rather than widening retries.

## Baseline Evidence

- Latest comparable trace: `artifacts/runs/20260517-124357-astropy__astropy-12907/trace.jsonl`
- Latest comparable result: `artifacts/runs/20260517-124357-astropy__astropy-12907/result.json`
- Related dossiers: `artifacts/meta/hypotheses/H0006-source-edit-finalization.md`, `artifacts/meta/hypotheses/H0010-no-patch-bounded-retries.md`
- Failure class: clean worktree / empty patch / early stop without finish action

## Candidate Hypotheses Considered

| Candidate | Role (exploit / explore / bridge) | Mechanism | Trace anchor (strong / medium / weak) | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | exploit | Add a hard finalization gate that blocks `finish` unless a tracked source diff exists and `patch_bytes > 0`; if the worktree is still clean, force another edit/observe cycle instead of retrying recovery. | strong | Latest comparable trace: `stopped after 4 iterations without finish action; patch_bytes=0; empty_patch_instances=1; resolved_instances=0` plus H0006/H0010 dossiers. | S | M | medium | chosen because it targets the exact observed failure with the smallest surface change and avoids repeating the prior retry-focused ideas. |
| B | explore | Replace ad hoc loop control with an explicit LangGraph-style `ready_to_finish` state keyed on `has_patch` and `diff_confirmed`, so termination is a graph transition rather than a prompt convention. | medium | Same trace failure class, plus LangGraph control mechanism for explicit state gating. | M | L | medium | deferred because it is more structural than necessary for the one-task gate, but it may generalize better if the finish-path remains fragile. |
| C | bridge | Keep the current loop, but insert one forced “source-edit checkpoint” after the third iteration: require a diff summary and changed-file count before any final answer or exit path can fire. | strong | Latest comparable trace + prior no-patch / source-edit-finalization dossiers (`H0006`, `H0010`). | S | M | medium | deferred because it is a cheaper counterfactual to the recent no-patch pattern, but it is weaker than A since it still depends on loop discipline rather than an explicit guard. |

## Proposed Change

- Smallest surface: `src/evolve2_agent_bench/agent/base.py` finalization path.
- Non-goal: do not broaden retries, add new tools, or redesign the whole loop.
- Exact guard: when the model emits `finish`, require a tracked `git diff` under `src/` before allowing terminal exit; if the tree is still clean, append a blocking observation and continue the loop.
- Expected movement: reduce `patch_bytes = 0` and `empty_patch_instances`, increase successful finish actions without needing a larger retry budget.

## Test Plan

- Validation stage: `one-task` gate.
- Metrics to compare: `patch_bytes`, `empty_patch_instances`, `resolved_instances`, `invalid_actions`, and total tool calls.
- Stop condition: one-task run shows a real patch-diff checkpoint before finish and no regression in agent stability.

## Expected Pareto Movement

- Primary metric: lower `empty_patch_instances` and higher `patch_bytes`
- Secondary metrics: stable or better `resolved_instances`, no major invalid-action regression
- Regression risks: extra guard logic might delay finish, but the target is to prevent false finalization rather than widen the loop

## Result

The one-task gate started as run `20260521-092445-astropy__astropy-12907`, but it had not produced `result.json` or `patch.diff` at handoff time. The trace reached `agent_start` only; there was no candidate patch/eval artifact to compare against the baseline.

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

No completed candidate artifact was available, so no Pareto comparison could be made.

## Decision

inconclusive

## Search node (MCTS)

- **Parent state**: `main` @ `0cf10077bb2d447f8216e3c6f7c671e6d6f627c3`, parent hypothesis context `H0010`.
- **State fingerprint**: no-patch finalization failure on the latest comparable trace.
- **Children considered**: A expanded on this branch; B and C deferred.
- **Rollout depth**: `one-task`; baseline trace/result above, candidate run `20260521-092445-astropy__astropy-12907` started but did not complete during handoff.
- **Value summary**: the branch landed the hard `finish` gate, but no run artifact completed yet, so the current signal is limited to the code change and partial trace start.
- **Revisit queue**: explicit LangGraph `ready_to_finish` state; forced source-edit checkpoint after iteration 3.

## Evidence Links

- Candidate trace: `artifacts/runs/20260517-124357-astropy__astropy-12907/trace.jsonl`
- Candidate result: `artifacts/runs/20260517-124357-astropy__astropy-12907/result.json`
- Commit: `0cf10077bb2d447f8216e3c6f7c671e6d6f627c3`
