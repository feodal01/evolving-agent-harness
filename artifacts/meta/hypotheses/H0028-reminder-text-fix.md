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
| status | rejected |

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
| A (chosen) | Fix contradictory tool references in reminder messages | rejected | — |
| B | Add edit_file call examples to reminders | — | H0028-B |

## Results

### Batch gate

**Baseline (main):** 3/6 resolved
| Instance | Resolved | Patch bytes | Iterations |
|---|---|---|---|
| astropy__astropy-12907 | YES | 500 | 6 |
| astropy__astropy-14309 | YES | 553 | 7 |
| django__django-10097 | YES | 632 | 16 |
| astropy__astropy-13033 | NO | 1394 | 7 |
| astropy__astropy-13236 | NO | 1859 | 52 |
| astropy__astropy-13398 | NO | 6246 | 63 |

**Candidate (H0028):** 3/6 resolved
| Instance | Resolved | Patch bytes | Iterations |
|---|---|---|---|
| astropy__astropy-12907 | YES | 500 | 6 |
| astropy__astropy-14309 | YES | 552 | 4 |
| django__django-10097 | YES | 1314 | 14 |
| astropy__astropy-13033 | NO | 4765 | 37 |
| astropy__astropy-13236 | NO | 759 | 7 |
| astropy__astropy-13398 | NO | 9723 | 92 |

### Pareto analysis

1. **patch_published**: Equal — 3/6 in both. No regression, no improvement.
2. **resolved** (primary): Equal — 3/6. No change.
3. **trace health** (secondary): Mixed. astropy-13236: significant improvement (7 iters vs 52, 759 bytes vs 1859). django-10097: patch_bytes grew (632→1314) but iters dropped (16→14). astropy-13033: worse (37 iters vs 7, 4765 bytes vs 1394). astropy-13398: worse (92 iters vs 63, 9723 bytes vs 6246).
4. **cost**: Mixed — cheaper on 13236, more expensive on 13033 and 13398.

### Decision: REJECTED

No Pareto improvement. `resolved` is flat at 3/6. While astropy-13236 showed a dramatic improvement in efficiency (7 vs 52 iterations), this is offset by regressions on 13033 and 13398. The reminder text change alone does not produce a durable, consistent improvement across the batch.

### Insights and findings

- The edit_file reminder fix may still be "correct" in isolation (messages should reference the right tool), but the model's behavior is not measurably improved by this alignment.
- astropy-13236's dramatic improvement (7 vs 52 iters) suggests the reminder may help on instances where the agent is "stuck" — but the effect is not consistent enough.
- The text changes should be bundled with a future hypothesis that has a stronger behavioral mechanism, not shipped alone.

### Run IDs

**Baseline runs:**
- astropy-12907: 20260525-194317-astropy__astropy-12907
- astropy-14309: 20260525-194654-astropy__astropy-14309
- django-10097: 20260525-195456-django__django-10097
- astropy-13033: 20260525-200539-astropy__astropy-13033
- astropy-13236: 20260525-201304-astropy__astropy-13236
- astropy-13398: 20260525-202102-astropy__astropy-13398

**Candidate runs:**
- astropy-12907: 20260526-113632-astropy__astropy-12907
- astropy-14309: 20260526-114059-astropy__astropy-14309
- django-10097: 20260526-114427-django__django-10097
- astropy-13033: 20260526-115755-astropy__astropy-13033
- astropy-13236: 20260526-120315-astropy__astropy-13236
- astropy-13398: 20260526-120820-astropy__astropy-13398
