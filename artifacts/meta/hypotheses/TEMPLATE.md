# HXXXX Short Hypothesis Title

Summary: One-sentence human-readable description for the public showcase page.

Status: proposed

Branch: `hyp/HXXXX-short-slug`

Created: YYYY-MM-DD
Updated: YYYY-MM-DD

## Hypothesis

If ..., then ..., measured by ...

## Motivation

What trace failure or literature mechanism motivates this?

## Baseline Evidence

- Baseline branch/commit:
- Baseline run ids:
- Trace paths:
- Failure class:
- Key observed events:

## Candidate Hypotheses Considered

| Candidate | Role (exploit / explore / bridge) | Mechanism | Trace anchor (strong / medium / weak) | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | exploit | ... | strong | trace + … | S | M | medium | chosen because ... |
| B | explore | ... | medium | curated LC + trace … | M | L | low | rejected because ... |
| C | bridge | ... | strong | trace + literature | L | L | medium | rejected because ... |

## Proposed Change

Smallest code/doc surface to change. Include non-goals. If the hypothesis is **trace-targeted**, name the trace metrics or events you expect to move (see **Trace-targeted hypotheses and rejection** under **Pareto Optimization** in `docs/meta/prompt-analyzer.md`).

## Test Plan

- Validation commands:
- Benchmark task ids:
- Validation stage: one-task gate | three-task promotion gate | full benchmark approval request
- Max iterations / timeout:
- Agent max tokens:
- Metrics to compare:
- Stop condition:

## Expected Pareto Movement

- Primary metric:
- Secondary metrics:
- Regression risks:

## Result

Fill after running.

## Metrics

| Metric | Baseline | Candidate | Delta |
| --- | --- | --- | --- |
| Resolved instances | | | |
| Patch published / patch bytes | | | |
| Empty patch instances | | | |
| Wall seconds | | | |
| Prompt tokens | | | |
| Completion tokens | | | |
| Total tokens | | | |
| Invalid actions | | | |
| Tool calls | | | |

## Pareto Assessment

Fill after running.

## Decision

One of: merge to main, keep unmerged, rerun, expand task set, superseded by Hxxxx. For **trace-targeted** hypotheses, prefer `merge to main` when named trace metrics improved and `patch_published` did not regress vs baseline at the completed gate; do not choose `rejected` solely for flat or worse `resolved` without such a regression (see `docs/meta/prompt-analyzer.md`).

## Search node (MCTS)

Fill after running (see `docs/meta/artifacts-schema.md` Appendix B).

- **Parent state**: `main` @ `<sha>` and/or `parent_hypothesis_id: Hxxxx` (or `null` if root-from-main only).
- **State fingerprint**: one line (failure class + which traces or summaries define this node).
- **Children considered**: for each row in **Candidate Hypotheses Considered**, mark `expanded`, `deferred`, or `abandoned` (explain).
- **Rollout depth**: `one-task` | `three-task` | `full-benchmark-pending`; list baseline and candidate run ids used as samples.
- **Value summary**: one paragraph pointing to **Metrics** and **Pareto Assessment**.
- **Revisit queue**: deferred child actions or follow-ups for a future hypothesis id.

## Evidence Links

- Candidate run:
- Candidate trace:
- Commit:
