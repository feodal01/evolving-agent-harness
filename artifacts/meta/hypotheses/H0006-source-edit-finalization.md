# H0006 Source Edit Finalization

Status: inconclusive

Branch: `hyp/H0006-source-edit-finalization`

Created: 2026-05-09
Updated: 2026-05-09

## Hypothesis

If each agent turn reports whether a tracked git diff exists and rejects finish attempts while the diff is empty, then the agent will be more likely to edit tracked source files instead of ending or exhausting iterations with no patch, measured by movement from `empty_patch_instances=1` and `patch_bytes=0` toward a non-empty submitted patch on `astropy__astropy-12907`.

## Motivation

The assigned focus area is source-edit forcing or finalization criteria targeting empty patches and no tracked source edits. Prior hypothesis dossiers record that the dominant failure progressed from action protocol issues to `no_patch`: H0004 observed that the agent inspected relevant Astropy source and identified the likely fix in natural language, but still did not edit tracked source after 16 and 32 iterations.

Local trace files are not present in this worktree (`artifacts/runs/` is absent), so this proposal uses the branch-local dossiers as the available trace summary evidence.

## Candidate Hypotheses Considered

| Candidate | Mechanism | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- |
| A | Add tracked diff status to each observation and reject `finish` while the tracked diff is empty. | H0004 dossier: agent reached likely source fix but produced `patch_bytes=0`; SWE-agent ACI direction favors explicit interface feedback. | S | M | medium | Chosen because it directly targets no tracked edits with minimal loop/tool surface changes. |
| B | Add a dedicated `edit_source` action that only writes existing tracked files and records source-edit intent separately from scratch writes. | H0004 dossier plus Agent-Computer Interface literature direction toward structured editing. | M | L | medium | Rejected for this cycle because it changes the action schema and prompt more broadly than needed for one branch. |
| C | At patch creation time, if `git diff` is empty, synthesize a second-pass reflection prompt asking for one tracked source edit. | H0004 no-patch evidence plus trace reflection literature direction. | L | L | low | Rejected because it adds a second agent phase and complicates benchmark comparability in this narrow source-edit finalization branch. |

## Proposed Change

Change only `src/evolve2_agent_bench/agent/base.py`:

- strengthen the system prompt to state that reproduction files and untracked scratch files do not count as a patch;
- after every non-finish action, append a compact tracked-diff status observation to the conversation;
- if the model calls `finish` while `git diff --name-only` is empty, reject that finish and continue with an observation requiring a tracked source/test edit.

Non-goals:

- Do not add a new action type.
- Do not change model, token limits, benchmark runner, patch creation, or SWE-bench evaluation.
- Do not expose hidden benchmark fields.
- Do not implement broad parser changes from rejected prior branches.

## Baseline Evidence

- Baseline branch/commit: `main` / `0a79213501d5c04b08be7980142d658fce7c1753`
- Baseline run ids:
  - `20260508-182634-astropy__astropy-12907`
  - `20260508-184725-astropy__astropy-12907`
  - `20260508-190035-astropy__astropy-12907`
- Trace paths:
  - `artifacts/runs/20260508-182634-astropy__astropy-12907/trace.jsonl`
  - `artifacts/runs/20260508-184725-astropy__astropy-12907/trace.jsonl`
  - `artifacts/runs/20260508-190035-astropy__astropy-12907/trace.jsonl`
- Failure class: `no_patch`
- Key observed events:
  - H0004 same-budget candidate reduced invalid actions but still ended with `patch_bytes=0` and `empty_patch_instances=1`.
  - H0004 extended 32-step candidate executed more actions and still ended with `patch_bytes=0` and `empty_patch_instances=1`.
  - The candidate identified the likely source fix in natural language but did not edit tracked source.

## Test Plan

- Validation commands:
  - `uv run python -m compileall -q src scripts`
  - local focused smoke check for finish rejection when no tracked diff exists
- Benchmark task ids:
  - one-task gate: `astropy__astropy-12907`
  - fixed three-task promotion gate only if one-task merge criteria pass: `astropy__astropy-12907`, `django__django-11099`, `sympy__sympy-20590`
- Validation stage: one-task gate
- Max iterations / timeout: `--max-iterations 100 --evaluation-timeout 1800`
- Agent max tokens: unset
- Metrics to compare:
  - resolved instances
  - patch bytes
  - empty patch instances
  - wall seconds
  - prompt, completion, and total tokens
  - invalid actions
  - tool calls
- Stop condition:
  - candidate one-task run completes, or document credential/runtime blocker as inconclusive.

## Expected Pareto Movement

- Primary metric: non-empty tracked patch publication.
- Secondary metrics: avoid increasing invalid actions; keep wall time and token growth acceptable if patch publication improves.
- Regression risks: extra diff-status text may increase prompt tokens; rejecting finish with no diff may spend more iterations if the agent cannot identify an edit.

## Result

Implemented the selected source-edit finalization guard in `BaselineLangChainAgent`:

- the system prompt now states that tracked source/test edits are required before finishing;
- each non-finish observation appends tracked git diff status;
- `finish` is rejected when `git diff --name-only` is empty.

Validation passed:

- local smoke check with a fake agent confirmed empty-diff `finish` is rejected and the loop continues;
- `uv run python -m compileall -q src scripts`;
- `uv run evolve2 model-check` returned `model-ok`.

The documented one-task gate started as run `20260509-082701-astropy__astropy-12907` after loading credentials from `/Users/user/Documents/repos/evolve2/.env`, because this worktree did not contain its own `.env`. The run wrote a trace through iteration 2, then stalled with no trace growth for several minutes while waiting for the next provider/runtime step. I terminated the stalled process and classify the benchmark gate as inconclusive.

Partial trace evidence:

- event count: 15;
- LLM calls: 2;
- tool calls: 2 shell calls;
- invalid actions: 0;
- token usage: 1,476 prompt, 815 completion, 2,291 total;
- no `result.json`, `patch.diff`, `patch_created`, or evaluation report was produced;
- tracked git diff in the task worktree was empty at termination;
- the new patch-status observation appeared after iterations 1 and 2, so the mechanism was active before the stall.

## Metrics

| Metric | Baseline | Candidate | Delta |
| --- | --- | --- | --- |
| Resolved instances | 0 | n/a, gate incomplete | n/a |
| Patch published / patch bytes | no / 0 | no `patch.diff` produced | n/a |
| Empty patch instances | 1 | n/a, no evaluation report | n/a |
| Wall seconds | 291.792 same-budget H0004 baseline; 422.128 H0004 candidate | n/a, interrupted after stall | n/a |
| Prompt tokens | not recorded in H0004 table for baseline; 126638 total candidate | 1,476 partial | n/a |
| Completion tokens | not recorded | 815 partial | n/a |
| Total tokens | 80,820 same-budget H0004 baseline; 126,638 H0004 candidate | 2,291 partial | n/a |
| Invalid actions | 10 same-budget H0004 baseline; 6 H0004 candidate | 0 partial | n/a |
| Tool calls | 6 agent actions baseline; 10 H0004 candidate | 2 shell calls partial | n/a |

## Pareto Assessment

Inconclusive. The code path behaved locally and the live trace shows the new tracked-diff status feedback being added, but the one-task benchmark did not reach patch creation or evaluation. There is no decision-grade evidence for patch publication, resolution, or regression.

## Decision

Keep unmerged pending rerun. Do not merge H0006 based on this branch result. The branch is still useful as a narrow implementation of source-edit finalization, but the benchmark blocker prevents confirmation or rejection.

## Evidence Links

- Candidate run: no `result.json`; incomplete run directory `artifacts/runs/20260509-082701-astropy__astropy-12907/`
- Candidate trace: `artifacts/runs/20260509-082701-astropy__astropy-12907/trace.jsonl`
- Commit:
