# H0013 Forced Source-Edit Checkpoint

Status: inconclusive

Branch: `hyp/H0013-forced-source-edit-checkpoint`

Created: 2026-05-21
Updated: 2026-05-21

## Hypothesis

If the agent is interrupted immediately after its first scratch-file `write_file` when no tracked `src/` diff exists, then it will pivot into tracked source edits earlier and reduce the reproduction-only loop seen on `astropy__astropy-12907`.

## Motivation

The live trace shows the agent repeatedly creates or rewrites reproduction scripts before touching `src/`. H0016 already tried the iteration-3 version of this idea; H0013 moves the checkpoint earlier, to the first scratch-file write, which is the earliest reliable signal that the agent has entered the reproduction loop.

## Candidate Hypotheses Considered

| Candidate | Role (exploit / explore / bridge) | Mechanism | Trace anchor (strong / medium / weak) | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | exploit | Inject a checkpoint immediately after the first scratch-file `write_file` if no tracked `src/` diff exists. | strong | H0017/H0016 trace showing repeated scratch-file writes before any source edit | S | M | medium | chosen because it targets the earliest observed reproduction-only turn. |
| B | explore | Hard-block any further `write_file` actions until the agent has modified tracked `src/` files. | medium | same trace plus source-edit gating literature | M | M | low | deferred because it is more intrusive and could interfere with legitimate test scaffolding. |
| C | bridge | Keep the checkpoint reminder but also add a finalization gate that refuses `finish` without a tracked diff summary. | medium | H0011/H0014/H0015 outcomes | M | M | medium | deferred because the earliest observed leak is still the scratch-file write, not finalization. |

## Proposed Change

Smallest code surface: `src/evolve2_agent_bench/agent/base.py`.

After the first `write_file` action, if the workspace still has no tracked diff under `src/`, append a checkpoint message telling the agent to prioritize tracked source edits and stop producing scratch reproduction files. Also update the system prompt to prefer tracked `src/` edits over scratch files.

## Test Plan

- `uv run python -m unittest tests.test_forced_source_edit_checkpoint -q`
- `uv run python -m compileall -q src scripts`
- `set -a; source /Users/user/Documents/repos/evolve2/.env; set +a; uv run evolve2 model-check`
- One-task gate: `uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 100 --evaluation-timeout 1800`

## Result

The checkpoint fired after the first scratch-file write and redirected the agent into tracked source inspection, but the live run stalled before producing a patch or finish artifact.

## Decision

Inconclusive.
