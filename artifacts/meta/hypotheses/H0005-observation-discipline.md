# H0005 Observation Discipline For No-Patch Loops

Status: inconclusive

Branch: `hyp/H0005-observation-discipline`

Created: 2026-05-09
Updated: 2026-05-09

## Candidate Hypotheses Considered

| Candidate | Mechanism | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- |
| A | Add compact per-turn tracked-diff status and repeated-action metadata to agent observations, with a no-patch progress hint after several iterations without tracked edits. | H0004 trace summary shows the agent reached relevant source and described a likely fix but still produced `patch_bytes=0`; LangChain context-engineering docs emphasize lifecycle context between model and tool calls. | S | M | medium | Chosen because it directly targets `no_patch` and low-value repetition without adding a new tool or changing the benchmark profile. |
| B | Truncate and classify shell output by command type so reproduction outputs are summarized more aggressively than source reads. | H0002/H0004 reported repeated reproduction shell commands and noisy outputs. | M | M | medium | Rejected for this cycle because output summarization changes more behavior and risks hiding useful failure details before the agent has a patch. |
| C | Reject exact duplicate shell commands after the first execution unless a tracked diff changed. | H0004 extended run executed many actions while preserving `patch_bytes=0`; ACI literature supports interfaces that prevent low-value loops. | S | S | medium | Rejected because hard rejection may block legitimate reruns after environment changes; observation nudging is less invasive for a first test. |

## Hypothesis

If each tool observation includes compact tracked-patch status and repeated-action metadata, then the agent will notice when reproduction work has not created a tracked source diff and will be more likely to edit tracked source before finishing or exhausting the iteration budget, measured by movement from `empty_patch_instances=1` toward non-empty `patch_bytes` on `astropy__astropy-12907`.

## Motivation

Prior branch dossiers identify the dominant failure class as `no_patch`. H0002 showed that blocking one reproduction-file write path was bypassed through shell redirection. H0004 showed the agent could execute more actions, inspect relevant source, and even state the likely Astropy fix in natural language, but still produced an empty patch. This suggests the loop is missing lifecycle context about whether its actions have produced benchmark-relevant tracked changes.

LangChain's local context-engineering reference frames agent reliability as a function of the right information being passed at model-call and lifecycle boundaries. Here the missing lifecycle context is simple and local: after every action, the model should know whether `git diff` is still empty and whether it is repeating the same command.

## Baseline Evidence

- Baseline branch/commit: `main` / `0a79213`
- Baseline run ids:
  - `20260508-182634-astropy__astropy-12907`
  - related extended candidate evidence: `20260508-190035-astropy__astropy-12907`
- Trace paths:
  - `artifacts/runs/20260508-182634-astropy__astropy-12907/trace.jsonl`
  - `artifacts/runs/20260508-190035-astropy__astropy-12907/trace.jsonl`
- Failure class: `no_patch`, with repeated low-value reproduction behavior.
- Key observed events:
  - Baseline 16-step run: `patch_bytes=0`, `empty_patch_instances=1`, `invalid_action_count=10`.
  - H0004 candidate reached source inspection and natural-language localization but still did not edit tracked source.
  - H0002 proved a narrow reproduction-file write guard could be bypassed through shell commands.

## Proposed Change

Change only `src/evolve2_agent_bench/agent/base.py`:

- Track exact repeated `run_shell` command counts within the agent loop.
- After each executed action, compute a compact tracked patch status from `git diff --shortstat` and `git status --short`.
- Add that status to the observation payload sent to the next model call and to the trace.
- After at least three iterations with no tracked diff, add a short progress hint that the next useful step should be reading or editing tracked source rather than repeating reproduction.

Non-goals:

- Do not add or remove action types.
- Do not reject shell commands.
- Do not change model, temperature, token policy, benchmark runner, or evaluation.
- Do not expose hidden SWE-bench fields.

## Test Plan

- Validation commands:
  - `uv run python -m compileall -q src scripts`
  - Local smoke check for observation metadata construction in a temporary git repo.
  - `uv run evolve2 model-check`
- Benchmark task ids:
  - `astropy__astropy-12907`
- Validation stage:
  - one-task gate
- Max iterations / timeout:
  - `--max-iterations 100 --evaluation-timeout 1800`
- Agent max tokens:
  - unset
- Metrics to compare:
  - `resolved_instances`
  - `patch_bytes`
  - `empty_patch_instances`
  - `invalid_action_count`
  - `tool_calls`
  - `wall_seconds`
  - prompt, completion, and total tokens
- Stop condition:
  - If one-task gate publishes a non-empty patch or resolves the task, run the fixed three-task promotion gate.
  - If credentials or infrastructure fail after retry/check, mark inconclusive with blocker evidence.

## Expected Pareto Movement

- Primary metric: non-empty tracked patch publication.
- Secondary metrics: fewer repeated low-value shell commands and clearer failure class if unresolved.
- Regression risks: extra observation fields may increase prompt tokens and could distract the model from raw tool output.

## Result

Implemented per-turn observation metadata in `BaselineLangChainAgent.run`:

- every observation now includes `patch_status` with tracked diff bytes, tracked changed files, and untracked-file preview;
- repeated exact shell commands are counted and annotated;
- after iteration 3 with no tracked diff, the agent receives a short `progress_hint` to inspect or edit tracked source/test files instead of continuing reproduction.

Validation completed:

- `uv run python -m compileall -q src scripts`
- local smoke check in a temporary git repository for zero-diff status, untracked-file status, repeated shell count, and no-patch hint behavior
- `uv run evolve2 model-check` with credentials sourced from `/Users/user/Documents/repos/evolve2/.env`, which returned `model-ok`

Candidate one-task gate was started with:

```bash
uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 100 --evaluation-timeout 1800
```

Run `20260509-082629-astropy__astropy-12907` was terminated with process exit code 143 before patch creation or SWE-bench evaluation, so there is no `result.json`, `patch.diff`, or evaluation report. The partial trace reached iteration 19 and records 19 LLM calls, 13 parsed actions, 13 tool calls, and 6 invalid actions.

Partial behavioral evidence is negative but not decision-grade:

- `patch_status.tracked_patch_bytes` stayed `0` for every logged observation.
- The progress hint appeared from iteration 3 onward.
- The agent still wrote untracked scratch/dependency files: `reproduce_issue.py`, `mock_erfa.py`, and repeated `erfa.py` writes.
- Untracked-file count grew from 1 to 4 while tracked changed-file count stayed 0.
- Prompt tokens reached 128370 in the partial trace, reflecting continued noisy trajectory growth.

Because the run did not complete patch creation or evaluation, the hypothesis is marked inconclusive rather than rejected.

## Metrics

| Metric | Baseline | Candidate | Delta |
| --- | --- | --- | --- |
| Resolved instances | 0 | unavailable, run terminated before evaluation | n/a |
| Patch published / patch bytes | no / 0 | unavailable, run terminated before patch creation | n/a |
| Empty patch instances | 1 | unavailable, run terminated before result writing | n/a |
| Wall seconds | 291.792 | unavailable, no `result.json` | n/a |
| Prompt tokens | | 128370 partial | n/a |
| Completion tokens | | 21920 partial | n/a |
| Total tokens | 80820 | 150290 partial | n/a |
| Invalid actions | 10 | 6 partial | n/a |
| Tool calls | | 13 partial | n/a |

## Pareto Assessment

Inconclusive. The one-task gate did not reach patch publication or evaluation, so it cannot establish Pareto movement. The partial trace shows the observation metadata was delivered as intended, but it did not stop the observed no-patch behavior within the first 19 iterations.

## Decision

Keep unmerged and report as inconclusive to the orchestrator. Do not run the three-task promotion gate because the one-task gate did not pass merge criteria and did not complete.

## Evidence Links

- Candidate partial run: `artifacts/runs/20260509-082629-astropy__astropy-12907/`
- Candidate trace: `artifacts/runs/20260509-082629-astropy__astropy-12907/trace.jsonl`
- Commit: branch HEAD for `hyp/H0005-observation-discipline`
