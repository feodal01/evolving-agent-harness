# H0022-B: Dedicated edit_file tool for line-range editing

## Hypothesis ID
H0022-B

## Title
Add dedicated `edit_file` tool with line-range editing (SWE-agent ACI style)

## Fix type
mechanical

## Parent hypothesis
H0022

## Parent commit
f0045ce (main after H0022 merge)

## Correlation ID
round-20260522-h0022b

## Dominant failure class
Agent reads source file but never edits it — writes to test files or scratch instead. H0022 blocked scratch files; agent then wrote tests via `cat >>` with broken heredoc syntax (EOFEOF garbage in patch). The agent has no ergonomic tool for targeted line-range editing.

## Trace anchor
strong — H0022 one-task gate (run_id: 20260522-102940-astropy__astropy-12907):
- Agent read separability.py (iter 3) but never edited it
- 0 of 20 iterations attempted source file edit
- Agent tried `cat <<EOF >> test_separable.py` which produced garbage (EOFEOF in patch)
- 10 iterations wasted on python3 -c import attempts

## Proposed Change
1. Add `edit_file` tool to `tools.py` with signature: `edit_file(path: str, start_line: int, end_line: int, new_content: str)` — replaces lines [start_line, end_line] inclusive with new_content.
2. Update `SYSTEM_PROMPT` to recommend `edit_file` as the primary editing method instead of `sed -i`.
3. The tool reads the file, replaces the specified line range, and writes the result. Validates the file is tracked before editing.

This is mechanical: the agent structurally cannot produce correct source edits without a line-range editing tool. sed -i is too error-prone for LLM tool use; write_file overwrites the entire file (dangerous for large files).

## Expected result
Agent uses edit_file to make targeted fixes to the source file. patch_bytes > 0 with source file edits (not just test additions). resolved rate improves because the patch targets the actual bug location.

## Search node (MCTS)
- Value headline: Give the agent a proper line-range edit tool so it can fix source files instead of writing tests
- Deferred children:
  - H0022-C: Stronger repeated-action detection with forced break messages

## Validation plan
- One-task gate on astropy__astropy-12907
- Success criterion: patch contains edits to a source file (not just test files) AND patch_bytes > 0
- No baseline comparison needed (mechanical fix)
