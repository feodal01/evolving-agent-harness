# Hypothesis dossier: H0026

## Identity

| Field | Value |
|-------|-------|
| hypothesis_id | H0026 |
| title | Read-search loop detection and intervention |
| branch | hyp/H0026-read-search-loop-detection |
| parent_hypothesis_id | H0025 |
| parent_commit | 34b41b4 |
| correlation_id | round-20260525-batch0-gate |
| fix_type | mechanical |
| status | in_progress |

## Problem statement

The agent gets stuck in read/search loops, spending dozens of iterations reading code and running rg without ever editing files. This wastes iteration budget and causes GraphRecursionError crashes.

Trace evidence:
- astropy-13398 (20260525-112754): 100 iterations, 60+ were rg/read with only 1 edit (at iteration 95). Hit GraphRecursionError at recursion limit 200.
- django-10097 (20260523): 20+ iterations of repeated empty rg searches before switching approach.
- astropy-13033 (20260525-103022): 16 iterations but several consecutive reads without editing.

Impact: The agent burns through its entire iteration budget without making progress, hitting GraphRecursionError. On astropy-13398, the agent produced 9826 bytes of patch (mostly from search output artifacts), but the core issue was never edited.

## Root cause

There is no mechanism to detect when the agent has spent many consecutive iterations reading/searching without making any edits. The existing `_CommandHistory` detects exact repeated commands (same command 3x), but not *similar* commands producing the same loop pattern (e.g., rg with different flags, read_file on different sections).

The `_NO_EDIT_REMINDER` constant already exists in tools.py (lines 28-32) but is never used.

## Proposed change

Add an `_EditTracker` class that counts consecutive read/search tool calls (run_shell, read_file) without any edit tool calls (edit_file, write_file). When the count reaches a threshold (5 consecutive reads without an edit), append `_NO_EDIT_REMINDER` to the tool output. The reminder fires once per loop episode and resets when an edit occurs.

This is a mechanical fix: the infrastructure for the reminder already exists, it just needs to be wired up.

## Candidates

| Candidate | Role | Fix type | Mechanism | Trace anchor | Effort | Expected result | Confidence | Why not / why chosen |
|-----------|------|----------|-----------|--------------|--------|-----------------|------------|---------------------|
| A: edit tracker with reminder | exploit | mechanical | _EditTracker counts consecutive reads, appends _NO_EDIT_REMINDER at threshold 5 | strong | S | M | high | CHOSEN: directly addresses the observed loop pattern, reminder text already exists |
| B: escalating reminders | explore | hypothesis | Show progressively stronger reminders at 5, 10, 15 reads without edit | weak | S | M | medium | DEFERRED: may annoy the agent, single reminder is simpler to validate |
| C: force-edit graph node | bridge | hypothesis | Add a LangGraph node that forces edit_file call when no edits for N iterations | weak | L | M | low | DEFERRED: requires graph architecture change, much more complex than output annotation |

## Validation plan

- Fix type: mechanical -> one-task gate, no baseline comparison
- Instance: astropy__astropy-13398 (chose this because its trace clearly shows the read-search loop: 60+ iterations with only 1 edit)
- Success criterion: agent receives the NO_EDIT_REMINDER after 5 consecutive reads and starts editing earlier; ideally does NOT hit GraphRecursionError

## Search node (MCTS)

| Action | Value headline | Status | Deferred child |
|--------|---------------|--------|---------------|
| A (chosen) | Break read-search loops by reminding agent to edit after 5 consecutive reads | in_progress | — |
| B | Escalating reminders at multiple thresholds | — | H0026-B |
| C | Force-edit LangGraph node | — | H0026-C |
