# H0010 No-Patch Control with Bounded Retries

Status: inconclusive

Branch: `hyp/H0010-no-patch-bounded-retries`

Created: 2026-05-16
Updated: 2026-05-16

## Hypothesis

If the loop tracks consecutive turns with an empty tracked `git diff` and injects a short control hint after a threshold, and emits a bounded JSON template reminder after repeated parse failures, then the agent reaches productive `write_file` edits sooner on `astropy__astropy-12907`, measured by patch bytes / resolved vs baseline without unacceptable invalid-action regressions.

## Motivation

Combines observation discipline themes (H0005/H0006 dossiers) with explicit git-diff awareness so `finish` cannot succeed while the benchmark-visible patch stays empty.

## Baseline Evidence

- Related dossiers: H0005, H0006, H0007 (inconclusive cluster).
- Benchmark runs for this branch: **not executed** — stranded executor phase.

## Proposed Change

- `src/evolve2_agent_bench/agent/base.py`: `_tracked_git_diff_snapshot`, streak counters, `_NO_PATCH_CONTROL_HINT`, `_INVALID_JSON_TEMPLATE_REMINDER`, `finish_rejected_empty_diff` tracing.

Non-goals: widening action schema, SWE-bench harness edits.

## Test Plan

- `compileall`, `model-check`, one-task gate as standard profile.

## Result

Implementation committed via orchestrator rescue; **benchmark not run** in this session fragment.

## Decision

Keep unmerged pending measurement.

## Search node (MCTS)

- **Parent state**: no-patch / control-hint cluster under H0007 correlation round.
- **Value summary**: mechanism coded; no rollout value yet.
- **Revisit queue**: executor gate rerun.

## Evidence Links

- Branch tip: `hyp/H0010-no-patch-bounded-retries`
