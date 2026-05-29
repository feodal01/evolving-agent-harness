# H0029 Diff Self-Review Before Finish

Status: rejected

Fix type: hypothesis

Branch: `hyp/H0029-diff-self-review`

Created: 2026-05-27
Updated: 2026-05-28

## Hypothesis

If the agent is shown its own git diff and prompted to check for completeness before finishing, then it will catch missing downstream updates (test changes, prerequisite source edits), measured by increased resolved count on batch 0.

## Motivation

All three unresolved batch-0 instances (13033, 13236, 13398) produce patches that fail evaluation because the agent makes the core code change but misses necessary downstream updates:
- 13033: Changed error message logic but missed updating some test assertions
- 13236: Added FutureWarning but didn't update tests to expect/suppress it
- 13398: Added coordinate transforms but missed the prerequisite ITRS `location` attribute

This is the dominant failure class for current non-trivial patches. SWE-agent uses a "review_on_submit" mechanism where the agent sees its own diff before final submission.

## Baseline Evidence

- Baseline branch/commit: main @ ce48deb
- Baseline run ids: 20260526-115755-astropy__astropy-13033, 20260526-120315-astropy__astropy-13236, 20260526-120820-astropy__astropy-13398
- Trace paths: artifacts/runs/{above run ids}/trace.jsonl
- Failure class: under-editing (agent produces core fix but misses downstream updates)
- Key observed events: All 3 unresolved instances produce non-empty patches (759-9723 bytes) that fail SWE-bench test evaluation

## Candidate Hypotheses Considered

| Candidate | Role | Fix type | Mechanism | Trace anchor | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | exploit | hypothesis | Diff self-review before finish: after edits, show agent its git diff + prompt to check for completeness | strong | trace (3/3 unresolved = under-editing) + SWE-agent review_on_submit | S | M | medium | CHOSEN: smallest change, directly targets dominant failure class |
| B | explore | hypothesis | Post-edit dependency callout: after each edit_file, grep for references to changed symbol and inject matches into tool output | medium | trace (13033, 13398 missed downstream deps) + Aider lint-test | M | M | low | DEFERRED: higher token cost, unclear if model can use the info |
| C | bridge | hypothesis | Allow limited pytest runs: let agent run targeted tests with 30s timeout, feed failures back | medium | trace (13236 FutureWarning would have been caught) + Aider auto-test | M | L | low | DEFERRED: changes tool model (tests were banned), higher regression risk |

## Proposed Change

Add a diff self-review step in the agent loop. Implementation approach:

1. In `base.py`, after the agent's ReAct loop finishes, capture `git diff` from the workspace
2. If the diff is non-empty, feed it back as a follow-up message with a review prompt
3. The review prompt asks: "Here is your current diff. Before finishing, verify: (1) Did you update all test files that reference the changed code? (2) Are there prerequisite changes (imports, class attributes, config) that your edit requires? (3) Does the diff contain any unintended changes?"
4. Give the agent a small number of additional iterations (5-10) to make any follow-up edits
5. This is a prompt/context change — classified as hypothesis

Non-goals: Not adding automated test execution. Not changing tool definitions. Not adding dependency tracing.

## Test Plan

- Fix type: hypothesis
- Validation path: full validation ladder with baseline comparison
- Validation commands: `uv run evolve2 run-task --instance-id <id> --max-iterations 40`
- Benchmark task ids: astropy__astropy-13033 (first unresolved in batch 0)
- Validation stage: one-task gate, then batch gate if passes
- Max iterations: 40 (base 30 + 10 for review step)
- Agent max tokens: default
- Metrics to compare: resolved (primary), patch_bytes, iterations, wall_seconds
- Stop condition: one-task gate resolved, or regression on previously-resolved instances

## Expected Pareto Movement

- Primary metric: resolved count increase on batch 0 (target: 4/6 or better vs current 3/6)
- Secondary metrics: patch completeness (fewer under-edits), iteration count may increase slightly
- Regression risks: agent may over-edit after seeing diff (H0027 showed over-editing can regress); may waste iterations on review step without acting

## Result

No Pareto improvement. Resolved count unchanged at 3/6. Diff self-review improves patch awareness (13236 went from 759B to 1848B patch with pytest.warns added) but model cannot reliably reason about correct downstream changes. Sometimes causes regressions (erroneous code removal). Cost increased 2-4x (wall seconds) due to review phase.

## Metrics

| Metric | Baseline | Candidate | Delta |
| --- | --- | --- | --- |
| Resolved instances | 3/6 | 3/6 | 0 |
| Patch published / patch bytes | 15247 | 15609 | +362 |
| Empty patch instances | 0 | 0 | 0 |
| Wall seconds (unresolved only) | 1048s | 2631s | +1583s |
| 13033 iterations | 37 | 18 | -19 |
| 13236 iterations | 7 | 58 | +51 |
| 13398 iterations | 92 | 95 | +3 |

## Pareto Assessment

No Pareto movement. Primary metric (resolved) unchanged. Cost increased significantly (2-4x wall seconds). Patch quality slightly improved on 13236 (added test updates) but not enough to flip the instance. The mechanism correctly identifies the failure class but the model lacks reasoning capacity to act on the diff review correctly.

## Decision

REJECT. No resolved count improvement, significant cost increase. The model's reasoning limitations (not awareness limitations) are the bottleneck — seeing the diff doesn't help when the model can't deduce the correct downstream changes.

## Search node (MCTS)

- **Parent state**: main @ ce48deb, parent_hypothesis_id: H0026 (last merged)
- **State fingerprint**: batch 0 at 3/6 resolved, dominant failure = under-editing (3/3 unresolved miss downstream updates)
- **Children considered**:
  - A (exploit, diff self-review): EXPANDED (chosen)
  - B (explore, dependency callout): DEFERRED as H0029-B
  - C (bridge, pytest runs): DEFERRED as H0029-C
- **Rollout depth**: 1 (completed full validation on 3 unresolved instances)
- **Value summary**: neutral — improved patch awareness but no resolved count gain, significant cost increase
- **Revisit queue**:
  - H0029-B: Post-edit dependency callout (grep for references to changed symbols after each edit_file)
  - H0029-C: Allow limited pytest execution with timeout and feedback loop

## Evidence Links

- Candidate runs: 20260528-125708-astropy__astropy-13033, 20260528-125855-astropy__astropy-13236, 20260528-125528-astropy__astropy-13398
- Candidate traces: artifacts/runs/{above}/trace.jsonl
- Commit: uncommitted (on hyp/H0029-diff-self-review branch)
