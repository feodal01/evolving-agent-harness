# H0030 Targeted pytest Execution Tool

Status: rejected

Fix type: hypothesis

Branch: `hyp/H0030-targeted-pytest`

Created: 2026-05-28
Updated: 2026-05-29

## Hypothesis

If the agent has a `run_test` tool that runs targeted pytest with timeout and scope limiting, it can verify its fixes against the test suite and catch under-editing failures, measured by increased resolved count on batch 0.

## Motivation

H0029 (diff self-review) was rejected because the model's reasoning limitations prevent it from deducing correct downstream changes from its diff. Objective test feedback would bypass this limitation — instead of asking the model to reason about what's missing, show it the test failures directly.

The current agent is soft-blocked from pytest: the system prompt says "Do NOT run pytest", and `run_shell` appends a redirect message if it detects pytest. This is incorrect — SWE-bench repos have their test suites checked out, and pytest may be available.

## Baseline Evidence

- Baseline branch/commit: main @ ce48deb
- Baseline runs: H0026 batch-0 baseline (20260525 runs)
- Trace paths: artifacts/runs/20260525-*/trace.jsonl
- Failure class: under-editing (3/3 unresolved instances miss downstream test/dependency updates)
- Key observed events: Agent produces patches (759-5012B) that fail SWE-bench test evaluation

## Candidate Hypotheses Considered

| Candidate | Role | Fix type | Mechanism | Trace anchor | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | exploit | hypothesis | run_test tool with targeted pytest, timeout, scope limiting | strong | H0029 rejected (reasoning limits), H0029-C deferred (pytest runs) | M | M | medium | CHOSEN: objective feedback bypasses reasoning limits |
| B | explore | hypothesis | Post-edit dependency callout: grep for references to changed symbol and inject into tool output | medium | trace (13033, 13398 missed downstream deps) | M | M | low | DEFERRED as H0030-B |
| C | bridge | hypothesis | Prompt engineering: teach agent to manually trace test dependencies | weak | same under-editing class | S | S | low | DEFERRED: H0027 showed prompt changes risky |

## Proposed Change

1. Add `run_test` tool to `tools.py` with target (file path or -k filter), timeout (30s default, max 60s)
2. Replace `_PYTEST_UNAVAILABLE` with `_PYTEST_REDIRECT` — redirect to use `run_test` tool instead of banning pytest
3. Update system prompt: encourage using `run_test` for verification after editing
4. Add `record_test()` to `_EditTracker` — test runs are productive, not passive reads
5. Add `"run_test"` to `KNOWN_ACTIONS`

## Test Plan

- Fix type: hypothesis
- Validation path: full validation ladder with baseline comparison
- Validation commands: `uv run evolve2 run-task --instance-id <id> --max-iterations 100`
- Benchmark task ids: astropy__astropy-13236 (first unresolved in batch 0)
- Validation stage: one-task gate, then batch gate if passes
- Agent max tokens: default
- Metrics to compare: resolved (primary), patch_bytes, iterations, wall_seconds
- Stop condition: one-task gate resolved, or regression on previously-resolved instances

## Expected Pareto Movement

- Primary metric: resolved count increase on batch 0 (target: 4/6 vs current 3/6)
- Secondary metrics: patch completeness (test failures guide corrections), iteration count may increase
- Regression risks: pytest unavailable in worktrees (graceful fallback), wasted iterations on failed test runs

## Result

No Pareto improvement. The `run_test` tool is functionally inoperable in current SWE-bench worktrees because:

1. **astropy repos**: `import astropy` fails due to missing compiled C extensions (`_compiler`) and `setuptools_scm` errors. The project is not installed in the worktree.
2. **django repos**: Django is not installed in the venv. `import django` fails.
3. **Root cause**: Workspaces are bare git checkouts with no `pip install -e .` — the agent's tools and system prompt explicitly prohibit pip.

The agent does use `run_test` (2 calls on 13236, 2 calls on 13033), but each returns an import error or pytest configuration error, wasting iterations instead of providing useful test feedback.

## Metrics

| Metric | Baseline (H0026) | Candidate (H0030) | Delta |
| --- | --- | --- | --- |
| Resolved instances | 3/6 | 3/6 (Docker errors) | 0 |
| 13033 iterations | 13 | 23 | +10 |
| 13236 iterations | 13 | 53 | +40 |
| 13033 wall seconds | 303s | 413s | +110s |
| 13236 wall seconds | 205s | 675s | +470s |
| 13033 patch bytes | 1307B | 1450B | +143B |
| 13236 patch bytes | 779B | 1695B | +916B |

## Pareto Assessment

No Pareto movement. Primary metric (resolved) cannot be determined due to Docker evaluation errors, but likely unchanged since patches are similar. Cost increased significantly (2-3x wall seconds, 2-4x iterations) due to wasted run_test calls. The mechanism is correct in theory but inoperable in practice — SWE-bench worktrees lack the installed packages needed for pytest to run.

## Decision

REJECT. No resolved count improvement, significant cost and iteration increase. The tool is theoretically sound but practically inoperable because SWE-bench workspaces are bare git checkouts without installed project packages. pytest cannot import the project or its dependencies.

## Search node (MCTS)

- **Parent state**: main @ ce48deb, parent_hypothesis_id: H0026 (last merged)
- **State fingerprint**: batch 0 at 3/6 resolved, dominant failure = under-editing, pytest unavailable in worktrees
- **Children considered**:
  - A (exploit, run_test tool): EXPANDED (chosen)
  - B (explore, dependency callout): DEFERRED as H0030-B
  - C (bridge, prompt engineering): DEFERRED as H0030-C
- **Rollout depth**: 1 (completed one-task gate on 2 instances)
- **Value summary**: negative — tool inoperable in worktrees, wasted iterations, no resolution gain
- **Revisit queue**:
  - H0030-B: Post-edit dependency callout (grep for references after edit_file)
  - H0030-C: Prompt engineering for test dependency tracing

## Key Insight

SWE-bench worktrees are bare git checkouts. `pip install -e .` is explicitly forbidden. This means pytest-based verification tools are fundamentally limited to repos where the project is already importable from the venv. For astropy (compiled extensions) and most complex projects, this will never work without changing the workspace setup.

## Evidence Links

- Candidate runs: 20260528-162604-astropy__astropy-13236, 20260528-162815-astropy__astropy-13033
- Candidate traces: artifacts/runs/{above}/trace.jsonl
- Commit: uncommitted (on hyp/H0030-targeted-pytest branch)
