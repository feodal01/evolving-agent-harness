# H0023: Add edit_file tool with line-range editing

## Hypothesis ID
H0023

## Title
Add edit_file tool with line-range editing (SWE-agent ACI style)

## Fix type
hypothesis

## Parent hypothesis
H0022 (block-untracked-writes)

## Parent commit
b9af953954c592bfba8bd6aaeca1b2208e769c98

## Correlation ID
round-20260523-edit-file

## Dominant failure class
bad_patch — agent writes test functions instead of editing source code. After H0022 blocked untracked writes, the agent pivoted to appending tests via `cat >> test_separable.py` instead of using `sed -i` on the source file `separable.py`.

## Trace anchor
strong — H0022 run (20260522-102940): tool call timeline shows agent used `cat <<EOF >> test_separable.py` and `cat <<<EOFEOF >> test_separable.py` to write test functions. It never edited `separable.py` because `sed -i` syntax is hard for small models. Post-H0022 runs (20260522-110703, 20260522-112113) also never edited source files.

## Proposed Change
1. Add a new `edit_file` tool that accepts `path`, `start_line`, `end_line`, and `replacement` parameters. This allows surgical line-range replacement without requiring `sed -i` or `cat >>` shell commands.
2. Update the system prompt to list `edit_file` as the primary editing tool and de-emphasize `sed -i`.
3. Keep `write_file` for full-file rewrites and `run_shell` for search, but make `edit_file` the recommended editing mechanism.

Mechanism: SWE-agent's ACI principle — provide structured editing primitives that make the correct action (editing source) easier than the incorrect action (appending tests). Small models struggle with `sed -i` syntax; a parameterized tool eliminates this friction.

## Expected result
- Agent uses `edit_file` on source files instead of `cat >>` on test files.
- `patch_bytes` on tracked source (non-test) files increases.
- `resolved` rate improves because patches target the actual bug.

## Search node (MCTS)
- Value headline: Replace sed/cat editing with structured edit_file tool to make source editing the path of least resistance
- Deferred children:
  - H0023-B: Block `cat >>` appending to test files (mechanical, Candidate C from this round)
  - H0023-C: Contextual file-target reminder after read_file (prompt enrichment, Candidate B from this round)

## Validation plan
- One-task gate on astropy__astropy-12907
- Baseline: H0022 run 20260522-102940 (patch_bytes=1591, resolved=false, agent wrote test instead of source edit)
- Success criterion: agent edits the source file (separable.py), not just test files
- If one-task passes: promote to three-task gate
