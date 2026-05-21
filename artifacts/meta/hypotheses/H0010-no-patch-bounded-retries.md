# H0010 No-Patch Control with Bounded Retries

Status: inconclusive

Branch: `hyp/H0010-no-patch-bounded-retries`

Created: 2026-05-16
Updated: 2026-05-17

## Hypothesis

If the loop tracks consecutive turns with an empty tracked `git diff` and injects a short control hint after a threshold, and emits a bounded JSON template reminder after repeated parse failures, then the agent reaches productive `write_file` edits sooner on `astropy__astropy-12907`, measured by patch bytes / resolved vs baseline without unacceptable invalid-action regressions.

## Motivation

Combines observation discipline themes (H0005/H0006 dossiers) with explicit git-diff awareness so `finish` cannot succeed while the benchmark-visible patch stays empty.

## Baseline Evidence

- Related dossiers: H0005, H0006, H0007 (inconclusive cluster).
- One-task gate attempts on this branch are recorded below; neither produced `artifacts/runs/<id>/result.json` (no resolved / SWE-bench report).

## Proposed Change

- `src/evolve2_agent_bench/agent/base.py`: `_tracked_git_diff_snapshot`, streak counters, `_NO_PATCH_CONTROL_HINT`, `_INVALID_JSON_TEMPLATE_REMINDER`, `finish_rejected_empty_diff` tracing.

Non-goals: widening action schema, SWE-bench harness edits.

## Test Plan

- Validation commands: `uv run python -m compileall -q src scripts`, `uv run evolve2 model-check`, `uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 100 --evaluation-timeout 1800`
- Benchmark task ids: `astropy__astropy-12907`
- Validation stage: **one-task gate** (attempted; incomplete — see Result)
- Max iterations / timeout: 100 / 1800s evaluation timeout
- Agent max tokens: unset (stable profile)
- Metrics to compare: patch publication, invalid actions, tokens, resolved when `result.json` exists
- Stop condition: harness writes `result.json` or hard infrastructure failure

## Expected Pareto Movement

- Primary metric: patch publication / solve on `astropy__astropy-12907`
- Secondary metrics: invalid-action rate, token cost
- Regression risks: hint spam, extra invalid-action churn from reminders

## Result

Rescue executor (`correlation_id` `round-20260516-54863b3a3530`) ran `model-check` (**ok**).

Two one-task attempts under `artifacts/worktrees/H0010-no-patch` (paths relative to that worktree):

1. **`20260517-085043-astropy__astropy-12907`** — trace grows through **iteration 86** (`invalid_action` last event); **no `result.json`**. Long wall-clock session ended without harness completion (process teardown; leaked multiprocessing semaphore warning). Trace shows **3×** `no_patch_control_hint` events.
2. **`20260517-130951-astropy__astropy-12907`** — trace reaches **iteration 89** then **`run-task` exits code 1**: OpenRouter/LangChain stack raised **`JSONDecodeError: Expecting value`** while parsing the HTTP response body (`httpx` → `response.json()`). **No `result.json`.** Trace shows **3×** `no_patch_control_hint` events.

**Conclusion:** One-task gate **not completed** — no SWE-bench evaluation artifact; inconclusive for merge/Pareto claims.

## Metrics

| Metric | Run `20260517-085043…` | Run `20260517-130951…` | Notes |
| --- | --- | --- | --- |
| Resolved instances | — | — | No `result.json` |
| Patch published / patch bytes | — | — | No `result.json` |
| Invalid actions (trace) | 53 | 59 | From `summarize_trace.py` |
| Max iteration observed | 86 | 89 | Trace-derived |
| Total tokens (trace usage fields) | 1,878,504 | 2,742,708 | LLM usage sums in trace |
| Wall seconds | — | — | Not recorded |

## Pareto Assessment

Cannot assess — evaluation never finalized.

## Decision

**Keep unmerged** pending a clean one-task rerun that produces `result.json` (watch for transient OpenRouter/gateway empty bodies). Same branch tip remains the candidate harness state.

## Search node (MCTS)

- **Parent state**: no-patch / control-hint cluster under H0007 correlation round.
- **Rollout depth**: `one-task` **attempted**, inconclusive (two partial traces; no evaluation).
- **Value summary**: Hypothesis mechanism emits trace-visible `no_patch_control_hint` under empty tracked diff; **no end-to-end benchmark value** due to infrastructure/session failures.
- **Revisit queue**: rerun one-task gate when API/runtime stable; compare `invalid_action` vs baseline on completed runs only.

## Evidence Links

- Candidate traces (worktree-relative): `artifacts/runs/20260517-085043-astropy__astropy-12907/trace.jsonl`, `artifacts/runs/20260517-130951-astropy__astropy-12907/trace.jsonl`
- Implementation previously landed at `5d58df2e48a9117607af9a4f6aad2602aef9fe35`; follow-on commit records this executor measurement attempt.
