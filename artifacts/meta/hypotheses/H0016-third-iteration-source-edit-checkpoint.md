# H0016 Third Iteration Source-Edit Checkpoint

Status: inconclusive

Branch: `hyp/H0016-third-iteration-source-edit-checkpoint`

Created: 2026-05-21
Updated: 2026-05-21

## Hypothesis

If iteration 3 injects an explicit checkpoint reminder when no tracked source diff exists under `src/`, then the agent will pivot from reproduction-only loops into an actual source edit sooner, measured by lower `empty_patch_instances` and higher `patch_bytes` on `astropy__astropy-12907`.

## Motivation

The local one-task evidence shows the agent spends its first three turns reproducing and inspecting, then still exits with `patch_bytes=0` and `empty_patch_instances=1`. A checkpoint at iteration 3 is the smallest place to interrupt that pattern without changing the tool surface or benchmark harness.

## Baseline Evidence

- Baseline branch/commit: `main` @ `0cf10077bb2d447f8216e3c6f7c671e6d627c3`
- Baseline run ids: `20260517-124357-astropy__astropy-12907`
- Trace paths: `mlruns-e2e-verify/629660148408137329/traces/tr-08b71f29d5c11c7b4f2807a9f661be13/artifacts/traces.json`
- Failure class: `no_patch`
- Key observed events: iteration 1 wrote a reproduction script; iterations 2-3 stayed in reproduction / environment recovery; the run ended after 4 iterations with no tracked source patch and `empty_patch_instances=1`.

## Candidate Hypotheses Considered

| Candidate | Role (exploit / explore / bridge) | Mechanism | Trace anchor (strong / medium / weak) | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | exploit | Add a third-iteration checkpoint message that explicitly tells the agent to edit tracked `src/` files when no source diff exists yet. | strong | local trace + result summary | S | M | medium | chosen because it is the smallest intervention at the point where the loop has already spent three turns on repro and still has no patch. |
| B | explore | Make iteration 3 a hard stop until a tracked source diff exists under `src/`, forcing a source edit before any further inspection or finalization. | medium | local trace + H0011-style finish gating | M | M | low | rejected for now because it is more intrusive than the checkpoint reminder and could overconstrain useful debugging. |
| C | bridge | Combine the checkpoint reminder with a finish gate that blocks `finish` until a tracked `src/` diff exists. | strong | local trace + prior finish-gate hypothesis | M | M | medium | deferred because H0011 already tested the harder gate shape and this run is meant to isolate the iteration-3 pivot first. |

## Proposed Change

Smallest code surface: `src/evolve2_agent_bench/agent/base.py`.

Add an iteration-3 checkpoint in the agent loop that checks whether the workspace has any tracked diff under `src/`; if not, append a targeted conversation reminder that a source edit is now required before more reproduction or finalization. Do not change the tool schema, benchmark runner, or artifact layout.

Non-goals:

- No new tools or parser changes.
- No benchmark harness changes.
- No board edits.

## Test Plan

- Validation commands: `uv run python -m compileall -q src scripts`; `set -a; source /Users/user/Documents/repos/evolve2/.env; set +a; uv run evolve2 model-check`; `uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 100 --evaluation-timeout 1800`
- Benchmark task ids: `astropy__astropy-12907`
- Validation stage: one-task gate
- Max iterations / timeout: `100 / 1800`
- Agent max tokens: unset
- Metrics to compare: `patch_bytes`, `empty_patch_instances`, `resolved_instances`, `invalid_actions`, `tool_calls`, `wall_seconds`
- Stop condition: accept only if the run yields a real patch artifact and does not regress into another empty-patch result.

## Expected Pareto Movement

- Primary metric: lower `empty_patch_instances` and higher `patch_bytes`
- Secondary metrics: `resolved_instances`, `invalid_actions`, `tool_calls`
- Regression risks: the checkpoint could add another conversational turn without changing behavior, or it could steer the model into more inspection without a source edit.

## Result

The implementation and validations ran, but the one-task gate did not yield a final patch artifact in time for handoff.

The first gate attempt, `20260521-095552-astropy__astropy-12907`, failed immediately because the new checkpoint helper was missing a `subprocess` import. That was fixed and revalidated locally.

The rerun, `20260521-100931-astropy__astropy-12907`, progressed through the agent loop but had not produced `result.json`, `patch.diff`, or an evaluation report at the time of handoff.

## Metrics

| Metric | Baseline | Candidate | Delta |
| --- | --- | --- | --- |
| Resolved instances | 0 | pending | pending |
| Patch published / patch bytes | no / 0 | pending | pending |
| Empty patch instances | 1 | pending | pending |
| Wall seconds | 26.002 | pending | pending |
| Prompt tokens |  | pending | pending |
| Completion tokens |  | pending | pending |
| Total tokens |  | pending | pending |
| Invalid actions | 0 | pending | pending |
| Tool calls | 3 | pending | pending |

## Pareto Assessment

No completed candidate comparison is available yet. The run is inconclusive because the benchmark session did not hand back a finished patch/eval artifact during this turn.

## Decision

inconclusive

## Search node (MCTS)

Fill after running.

- **Parent state**: `main` @ `0cf10077bb2d447f8216e3c6f7c671e6d627c3`
- **State fingerprint**: `no_patch` on `astropy__astropy-12907` after three reproduction-heavy iterations and no tracked `src/` diff.
- **Children considered**: A `expanded`; B `deferred`; C `deferred`
- **Rollout depth**: `one-task`; baseline sample `20260517-124357-astropy__astropy-12907`, candidate run `20260521-100931-astropy__astropy-12907` still in flight at handoff
- **Value summary**: This node is currently judged only on implementation and partial trace evidence; the gate has not yet produced a patch artifact to validate the expected Pareto movement.
- **Revisit queue**: If this reminder fails, sample the harder `finish` gate or a source-diff-aware stop rule as the next hypothesis.

## Evidence Links

- Candidate run: `artifacts/runs/20260521-100931-astropy__astropy-12907/`
- Candidate trace: `artifacts/runs/20260521-100931-astropy__astropy-12907/trace.jsonl`
- Commit: pending

