# Hypothesis dossier: H0028

## Identity

| Field | Value |
|-------|-------|
| hypothesis_id | H0028 |
| title | Fix reminder messages to reference edit_file instead of sed -i |
| branch | hyp/H0028-reminder-text-fix |
| parent_hypothesis_id | H0026 |
| parent_commit | 97723ed |
| correlation_id | round-20260525-batch0-gate |
| fix_type | hypothesis |
| status | in_progress |

## Problem statement

The agent has `edit_file` as its primary editing tool (added in H0023, improved in H0024), but all intervention messages still reference `sed -i` or `write_file` as the editing method:
- _SCRATCH_WRITE_BLOCKED: "Use `sed -i` to edit..."
- _PYTEST_UNAVAILABLE: "Apply the fix directly with sed -i or write_file..."
- _NO_EDIT_REMINDER: "You MUST apply a fix now using `sed -i` or `write_file`."
- _REPEATED_COMMAND_BREAK: "Break out by editing the source file now with `sed -i`."

This is contradictory — the system prompt says "Use `edit_file` for targeted edits" but the reminders say "use sed -i".

## Proposed change

Update all reminder messages to reference `edit_file` instead of `sed -i`/`write_file`.

**Note on classification**: Initially classified as `mechanical`, but per updated protocol, any change to text the agent reads (prompts, reminders, tool descriptions) is a `hypothesis` — it affects agent behavior, and its correctness is subjective (requires measuring whether the agent actually uses edit_file more effectively).

## Candidates

| Candidate | Role | Fix type | Mechanism | Trace anchor | Effort | Expected result | Confidence | Why not / why chosen |
|-----------|------|----------|-----------|--------------|--------|-----------------|------------|---------------------|
| A: fix reminder text | exploit | hypothesis | Update _SCRATCH_WRITE_BLOCKED, _PYTEST_UNAVAILABLE, _NO_EDIT_REMINDER, _REPEATED_COMMAND_BREAK to reference edit_file | strong | S | S | high | CHOSEN: text is simply wrong, contradicts system prompt |
| B: add edit_file examples to reminders | explore | hypothesis | Include example edit_file call syntax in reminders | weak | S | S | medium | DEFERRED: would make reminders longer, H0027 showed more text can hurt |

## Validation plan

- Fix type: hypothesis → full validation ladder with baseline comparison
- One-task gate: astropy__astropy-13236 (baseline on main vs candidate on branch)
- Batch gate: all 6 instances in batch 0 (baseline and candidate)
- Use: `uv run python scripts/run_validation_batch.py --fix-type hypothesis` (and `--baseline` for main)
- Success criterion: no regression in resolved count, agent uses edit_file when prompted by reminders

## Search node (MCTS)

| Action | Value headline | Status | Deferred child |
|--------|---------------|--------|---------------|
| A (chosen) | Fix contradictory tool references in reminder messages | in_progress | — |
| B | Add edit_file call examples to reminders | — | H0028-B |
