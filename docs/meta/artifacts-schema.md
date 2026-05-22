# Meta artifacts schema

Canonical data and file layout for meta-optimization. All role prompts in `docs/meta/prompt-*.md` reference this document for structures they must not redefine ad hoc.

## 1. Central hypotheses board

**Path:** `artifacts/meta/hypotheses-board.json`

**Format:** JSON object with a top-level array `rows` (list of hypothesis row objects). The orchestrator is the **only** writer of this file.

### Row object (schema)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `hypothesis_id` | string | yes | Stable id, e.g. `H0001` |
| `title` | string | yes | Short title |
| `status` | string | yes | One of: `idea`, `queued`, `running`, `analyzed`, `merged`, `rejected`, `superseded` |
| `fix_type` | string | yes | One of: `mechanical`, `hypothesis`. Determines validation path and budget. |
| `branch` | string | no | e.g. `hyp/H0001-slug` (set when execution starts) |
| `dossier_path` | string | no | e.g. `artifacts/meta/hypotheses/H0001-slug.md` |
| `parent_hypothesis_id` | string \| null | no | Parent state in search tree |
| `parent_commit` | string \| null | no | `main` SHA at branch creation when pinning harness state |
| `correlation_id` | string \| no | Round id tying board row to `meta-events.jsonl` |
| `baseline_run_id` | string \| null | no | Baseline SWE-bench run directory name under `artifacts/runs/` |
| `candidate_run_id` | string \| null | no | Candidate run id after execution |
| `analysis_report_path` | string \| null | no | Path to analyzer markdown report |
| `value_headline` | string \| no | One-line outcome for MCTS backprop / round summaries |
| `revisit_refs` | array of string | no | Links or ids of deferred child actions |
| `updated_at` | string | yes | ISO date `YYYY-MM-DD` |

### Status transitions (informal state machine)

- `idea` → `queued` (orchestrator accepts proposer payload)
- `queued` → `running` (orchestrator records `sample.selected` and assigns work)
- `running` → `analyzed` (orchestrator after analyzer report accepted)
- `analyzed` → `merged` | `rejected` | `superseded` (orchestrator merge/registry decision)

Invalid transitions are reconciled via `meta-events` rows and board corrections.

## 2. Append-only event log: `meta-events.jsonl`

**Path:** `artifacts/meta/meta-events.jsonl`

**Rules:** Append **only** new lines. Never edit or delete prior lines. Each line is one JSON object.

### Line schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ts` | string | yes | ISO-8601 timestamp |
| `actor` | string | yes | `orchestrator` \| `executor` \| `analyzer` \| `proposer` — **not** `sampler` (sampler does not write this file) |
| `event` | string | yes | Event type name (see catalog below) |
| `correlation_id` | string | yes | Round / session identifier for joins |
| `hypothesis_id` | string \| null | no | When the event concerns one row |
| `payload` | object | yes | Event-specific data |

### Event catalog and allowed writers

| `event` | Who may append | Notes |
|---------|----------------|-------|
| `round.opened` | orchestrator | Start of orchestration round |
| `proposal.accepted` | orchestrator | After validating Proposer JSON; precedes board row writes for new ideas |
| `sample.selected` | **orchestrator only** | Single source of truth for which hypothesis was chosen; payload includes `hypothesis_id`, `sampler_rationale` (echo from sampler output), `board_row_hash` or `updated_at` snapshot |
| `executor.started` | executor | Entering execution phase |
| `executor.finished` | executor | Include `run_id`, `commit_sha`, `ok` |
| `analyzer.started` | analyzer | Entering analysis phase |
| `analyzer.finished` | analyzer | Include `report_path` |
| `merge.decided` | orchestrator | `merged` \| `rejected` \| `keep_unmerged` + rationale |
| `round.closed` | orchestrator | |
| `reconcile` | orchestrator | Correcting prior ambiguity |

Sampler selection policy produces JSON only; `sample.selected` is appended during the orchestration phase. Optional helper: `scripts/meta_append_event.py`.

Use one `correlation_id` per round (e.g. ULID or `round-YYYYMMDD-HHMM`). All related events share it.

## 3. Phase context (what to load at each phase)

At each phase, the unified agent loads a **context snapshot** containing at minimum:

- `correlation_id`
- `main_sha` — current `origin/main` (or local `main`) HEAD the round is pinned to
- `hypotheses_board` — full or relevant subset of `hypotheses-board.json`
- `board_version` — max `updated_at` or content hash for staleness detection
- For execution phase: `hypothesis_id`, `branch`, `dossier_path`, gates to run
- For analysis phase: `candidate_run_id`, optional `baseline_run_id`, paths to `trace.jsonl` / `result.json`

## 4. Paths and linkage

- **Bench runs:** `artifacts/runs/<run_id>/` — `trace.jsonl`, `result.json`, `patch.diff`, etc. (see `prompt-executor.md` / `prompt-analyzer.md`).
- **Analyzer reports:** `artifacts/meta/analyses/<hypothesis_id>-<run_id>.md` (recommended pattern).
- **Dossiers:** `artifacts/meta/hypotheses/<hypothesis-id>-<slug>.md` — long-form lifecycle; board rows reference `dossier_path`.
- **Compact index:** `artifacts/meta/hypothesis-index.jsonl` on `main` for fast status lookup; `hypotheses-board.json` is the operational layer. Keep both in sync.

## 5. What not to commit

- Never commit or paste **secrets** (OpenRouter keys from `.env`).
- Do not paste **full** `trace.jsonl` bodies into dossiers or board; use **paths** and run ids only.

---

## Appendix A: `hypothesis-index.jsonl` record shape

Compact JSONL; long text lives in dossiers.

```json
{
  "hypothesis_id": "H0002",
  "title": "Structured edit tool reduces no_patch failures",
  "status": "proposed | running | confirmed | rejected | superseded | baseline",
  "fix_type": "hypothesis | mechanical",
  "branch": "hyp/H0002-structured-edit-tool",
  "dossier": "artifacts/meta/hypotheses/H0002-structured-edit-tool.md",
  "created_at": "YYYY-MM-DD",
  "updated_at": "YYYY-MM-DD"
}
```

Optional fields for search-tree navigation (omit if unknown):

- `parent_hypothesis_id`: hypothesis id of the **parent state** this run extends (often omitted when branching from `main` only).
- `parent_commit`: git sha of `main` (or other parent) at branch creation when that pins the pre-change harness state.

The index should not contain long hypotheses, detailed metrics, or findings. Put those in the dossier.

---

## Appendix B: Hypothesis dossier template (full markdown)

Create the dossier before changing code. After sampling the benchmark gates, always complete **Search node (MCTS)** so deferred branches and values stay visible for future expansions.

```markdown
# H0002 Structured Edit Tool Reduces No-Patch Failures

Status: proposed

Fix type: hypothesis | mechanical

Branch: `hyp/H0002-structured-edit-tool`

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

Paste the markdown table from **Generating Candidate Hypotheses** in `prompt-proposer.md` (three rows: exploit / explore / bridge with `trace_anchor`). Update the **Children considered** marks in **Search node (MCTS)** after you choose one row to expand.

## Proposed Change

Smallest code/doc surface to change. Include non-goals. If the hypothesis is **trace-targeted**, name the trace metrics or events you expect to move (see **Trace-targeted hypotheses and rejection** under **Pareto Optimization** in `prompt-analyzer.md`).

## Test Plan

- Fix type: mechanical | hypothesis
- Validation path:
  - mechanical: one-task gate only, no baseline comparison (fix is objectively correct)
  - hypothesis: full validation ladder with baseline comparison
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

One of: merge to main, keep unmerged, rerun, expand task set, superseded by Hxxxx. For **trace-targeted** hypotheses, prefer `merge to main` when named trace metrics improved and `patch_published` did not regress vs baseline at the completed gate; do not choose `rejected` solely for flat or worse `resolved` without such a regression (see **Trace-targeted hypotheses and rejection** in `prompt-analyzer.md`).

## Search node (MCTS)

Fill with the search-tree view of this experiment.

- **Parent state**: `main` @ `<sha>` and/or `parent_hypothesis_id: Hxxxx` (or `null` if root-from-main only).
- **State fingerprint**: one line (failure class + which traces or summaries define this node).
- **Children considered**: for each row in **Candidate Hypotheses Considered**, mark `expanded` (chosen on this branch), `deferred` (not implemented here), or `abandoned` (only if mechanism is falsified without coding—explain).
- **Rollout depth**: `one-task` | `three-task` | `full-benchmark-pending`; list baseline and candidate run ids used as samples.
- **Value summary**: one paragraph pointing to **Metrics** and **Pareto Assessment** (what signal backpropagates to the tree).
- **Revisit queue**: bullet list of `deferred` child actions or open follow-ups worth a **future** hypothesis id (link dossiers or describe the next edge).

## Evidence Links

- Candidate run:
- Candidate trace:
- Commit:
```

Proposal sections are filled before coding; result sections after the run. Evidence paths should point to files (e.g. `artifacts/runs/<run_id>/trace.jsonl`), not inline full traces.
