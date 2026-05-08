# H0002 Block Reproduction File Writes

Status: rejected

Branch: `hyp/H0002-block-repro-writes`

Created: 2026-05-08
Updated: 2026-05-08

## Hypothesis

If the workspace write tool rejects throwaway reproduction-script filenames, then the agent will spend fewer iterations creating untracked scratch files and will be more likely to inspect or edit tracked source/test files, measured by fewer `write_file` calls to reproduction files and any movement from `empty_patch_instances=1` toward a non-empty patch on `astropy__astropy-12907`.

## Motivation

The current baseline failure class is `no_patch` with evidence of unproductive reproduction-file planning. In the latest usable trace, the model response contains a planned `write_file` action to `reproduce_issue.py` followed by a planned command to run that file. The harness executes one parsed action per iteration and, for the one-iteration baseline run, stopped after a harmless `ls` with a zero-byte patch. The response content still shows the model's next intended behavior was a large root-level reproduction script, which would not be included by `git diff` and therefore would not help SWE-bench evaluation.

## Baseline Evidence

- Baseline branch/commit: `main` / `a82e5a854a80391fbdfbcfe82441aaf79351573b`
- Baseline run ids: `20260508-164503-astropy__astropy-12907`
- Trace paths: `artifacts/runs/20260508-164503-astropy__astropy-12907/trace.jsonl`
- Failure class: `no_patch`; `empty_patch_instances=1`; `patch_bytes=0`
- Key observed events:
  - `agent_iterations=1`
  - one parsed action: `run_shell` with `ls astropy/modeling/separable.py`
  - LLM response also included a planned `write_file` to `reproduce_issue.py`
  - run stopped without a finish action and generated an empty patch

## Proposed Change

Add a small guard in `WorkspaceTools.write_file` that rejects likely reproduction or scratch files by filename. The rejection should return a normal tool observation explaining that reproduction should be done with shell heredocs or inline commands, while source and test edits should target tracked project files.

Non-goals:

- Do not add a new editing API.
- Do not change benchmark evaluation.
- Do not alter model selection, token budgets, or parser behavior.
- Do not block legitimate source or test files under project package/test directories.

## Test Plan

- Validation commands:
  - `uv run python -m compileall -q src scripts`
- Benchmark task ids:
  - `astropy__astropy-12907`
- Max iterations / timeout:
  - candidate: `--max-iterations 4 --evaluation-timeout 1800`
- Metrics to compare:
  - `patch_bytes`
  - `empty_patch_instances`
  - `resolved_instances`
  - write attempts to reproduction files
  - wall time and iteration count
- Stop condition:
  - one candidate run, or document the exact credential/runtime blocker if OpenRouter execution cannot start.

## Expected Pareto Movement

- Primary metric: reduce reproduction-file writes and improve chance of non-empty source patch.
- Secondary metrics: keep validation passing; avoid evaluation errors.
- Regression risks: some tasks may benefit from persisted reproduction scripts. The guard allows inline shell reproduction and normal source/test edits, but it could reject a legitimate project file whose basename looks like a scratch reproduction script.

## Result

Implemented the root-level reproduction-file write guard in `WorkspaceTools.write_file`.

Validation passed:

- `uv run python -m compileall -q src scripts`
- local behavioral check that `write_file("reproduce_issue.py", ...)` is rejected and `write_file("src/pkg/module.py", ...)` is still allowed
- `uv run evolve2 model-check`

Candidate run `20260508-174807-astropy__astropy-12907` completed with `--max-iterations 4 --evaluation-timeout 1800`.

The guard worked locally and in the candidate run: iteration 1 attempted `write_file` to `repro.py`, and the tool rejected it with guidance to use inline shell reproduction or edit tracked source/test files. The agent then routed around the guard on iteration 2 by using `run_shell` with `cat <<EOF > repro.py`, creating an untracked scratch file outside `git diff`. Iterations 3 and 4 produced invalid non-JSON tool-call syntax while trying to install `erfa`. The final patch remained empty.

## Metrics

| Metric | Baseline | Candidate | Delta |
| --- | --- | --- | --- |
| Resolved instances | 0 | 0 | 0 |
| Empty patch instances | 1 | 1 | 0 |
| Patch bytes | 0 | 0 | 0 |
| Agent iterations | 1 | 4 | +3 |
| Invalid actions | 0 | 2 | +2 |
| Reproduction-file writes executed | 0 parsed / 1 planned in LLM response | 1 blocked `write_file`; 1 shell-created untracked `repro.py` | guard bypassed |
| Wall seconds | 119.284 | 146.186 | +26.902 |

## Pareto Assessment

Rejected. The implementation is small and the targeted `write_file` behavior changed as intended, but there was no Pareto improvement on the benchmark comparison. The primary metric stayed unchanged (`patch_bytes=0`, `empty_patch_instances=1`, `resolved_instances=0`) and secondary behavior worsened with two invalid actions and an untracked scratch file created through shell redirection.

## Decision

Keep unmerged. Do not merge to `main`. A future hypothesis should target scratch-file creation more generally, likely by sandboxing or cleaning untracked reproduction artifacts and by improving command guidance/parser recovery, rather than guarding only `write_file`.

## Evidence Links

- Candidate run: `artifacts/runs/20260508-174807-astropy__astropy-12907/result.json`
- Candidate trace: `artifacts/runs/20260508-174807-astropy__astropy-12907/trace.jsonl`
- Commit: branch HEAD commit for `hyp/H0002-block-repro-writes`
