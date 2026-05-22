# H0022: Block untracked file writes

## Hypothesis ID
H0022

## Title
Block untracked file writes and inject tracked-path sed guidance

## Fix type
mechanical

## Parent hypothesis
None (root cause fix from trace analysis)

## Parent commit
b913423b6d3518416bc6b938778db9efa8b55f1c

## Correlation ID
round-20260521-b5a63a

## Dominant failure class
no_patch — 100% of runs produce patch_bytes=0 because the agent writes reproduction scripts instead of editing tracked source files.

## Trace anchor
strong — Every run since H0001 shows the same pattern:
- 20260508-190035: 32 iterations, all write_file to scratch files
- 20260521-140643: 67 iterations, first 4 tool calls are correct (search+read), then write_file to reproduce_issue.py, then pytest retry loop for remaining 60+ iterations
- 20260521-143435: 6 iterations, same pattern — search, read, write scratch, run scratch, crash

## Proposed Change
1. In `write_file` tool: check if the target path is tracked by git (`git ls-files`). If not tracked AND not under the project package directory, reject the write with a clear message directing the agent to edit an existing tracked file using `sed` or `write_file` on a tracked path.
2. In `run_shell` tool: detect pytest/pip attempts that fail and append a stronger redirect message (the current `_PYTEST_UNAVAILABLE` constant exists on H0021 but is missing from main).
3. In `after_model` middleware hook: detect repeated identical shell commands (same command within last 3 actions) and inject a break message.

This is a mechanical fix: the agent structurally cannot produce patches if it never edits tracked source files. By blocking the path to scratch-file writes and providing clear redirect guidance, the agent is forced to use the correct edit path.

## Expected result
patch_published goes from 0% to >0% on the one-task gate. The agent should produce a non-empty diff because it can no longer waste iterations on scratch files.

## Search node (MCTS)
- Value headline: Block the dominant no-patch failure path by constraining write_file to tracked paths only
- Deferred children:
  - H0022-B: Add dedicated `edit_file` tool with line-range editing (SWE-agent ACI style)
  - H0022-C: Add repeated-action detection with forced break messages

## Validation plan
- One-task gate on astropy__astropy-12907
- Success criterion: patch_bytes > 0 (any non-empty tracked source diff)
- No baseline comparison needed (mechanical fix)
