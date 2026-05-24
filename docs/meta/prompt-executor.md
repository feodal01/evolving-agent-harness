# Executor reference prompt

Detailed instructions for Phase 3 (execution). Implement **one** hypothesis on **one** branch, **run** the validation ladder (benchmark gates), fill the dossier, and push the branch.

Append executor events to `meta-events.jsonl` per `docs/meta/artifacts-schema.md`.

Dossier template and index shape: `artifacts-schema.md` Appendices A and B.

---

## Autonomy (executor)

Work through the checklist without stopping for routine approval. Ask the user only for **hard blockers** (model down, missing `.env`, broken Docker/SWE-bench, conflicting local edits, unreadable artifacts).

Full evolution set and test set runs require **explicit user approval**. One-task and batch gates run autonomously. The test set is **ABSOLUTELY FORBIDDEN** without human consent — see `docs/VALIDATION_POLICY.md`.

If a blocker occurs after code changes: finish as `rejected` in the dossier, commit and push if possible, append `executor.finished` with `ok: false`.

---

## Git workflow for hypotheses

- `main` contains the mainstream agent. Every hypothesis branches from current `main`: `hyp/HXXXX-<short-hypothesis>`.
- In orchestrated runs, use the assigned worktree/branch/hypothesis id. In standalone, create your branch from `main`.
- Push every hypothesis branch to `origin`, whether confirmed, rejected, or rejected. Never delete failed branches.
- Do not merge to `main` until analysis (Phase 4) confirms improvement per `prompt-unified.md` §Phase 5.
- Failed branches must end with a commit recording the hypothesis, run ids, metrics, failure class, and decision in the dossier.
- Do not branch from an unconfirmed hypothesis branch. Start from `main` unless the dossier records a dependency.

Merge commit descriptions (standalone flows only) must include: hypothesis id, branch, parent state (`main` sha / `parent_hypothesis_id`), baseline/candidate run ids, task ids, code surfaces changed, metric deltas, Pareto assessment, decision, rationale, residual risks. Rejected branches: same fields plus `Decision: rejected`.

---

## First commands

```bash
uv sync
set -a
source .env
set +a
uv run evolve2 model-check
uv run evolve2 dataset-status
```

`.env` provides the OpenRouter key. Never print, commit, or copy it. If `dataset-status` fails, run `uv run evolve2 materialize-dataset` first.

Run one benchmark task (MLflow tracing is auto-enabled):

```bash
uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 100 --evaluation-timeout 1800
```

Useful inspection commands:

```bash
uv run evolve2 mlflow-ui                    # then open http://localhost:5000
uv run python scripts/summarize_trace.py <run_id>
jq -r '[.event,.stream,.iteration,.tool_name] | @tsv' artifacts/runs/<run_id>/trace.jsonl
jq 'select(.stream == "llm")' artifacts/runs/<run_id>/trace.jsonl
jq 'select(.event == "invalid_action")' artifacts/runs/<run_id>/trace.jsonl
uv run python -m compileall -q src scripts   # validate syntax
```

---

## Run artifacts

Each run writes `artifacts/runs/<run_id>/`. See `prompt-analyzer.md` §Run artifacts for the full file listing and `trace.jsonl` event names.

---

## Benchmark run profile

Use this stable profile unless the hypothesis explicitly changes a parameter:

```text
model: google/gemma-4-26b-a4b-it
temperature: 0
agent_max_tokens: unset
max_iterations: 100
evaluation_timeout: 1800
```

`max_iterations` is an emergency guardrail, not a work budget. Caps of 4/8/16/32 are smoke checks only, not decision runs. If a candidate reaches the cap before publishing a patch, increase it or classify the run as rejected unless the trace proves repeated non-progress.

`agent_max_tokens` controls per-call reasoning budget. Leave unset for normal decision runs; set only when testing completion-budget hypotheses, and keep fixed across baseline and candidate.

---

## Validation scale (you run these gates)

Read `artifacts/meta/validation-sets.json` at the start of each validation round. The **active batch** is the lowest-numbered batch whose status is `active` or `expanded`. Use instance IDs from the active batch for all gates.

### Mechanical fixes (`fix_type: mechanical`)

1. Work iteratively: implement, compile, run one-task gate, read trace if error persists, fix, repeat.
2. No baseline comparison needed — the fix is objectively correct or not.
3. Merge immediately on success.
4. If the problem resists multiple iterations, reclassify to `hypothesis`.

### Hypothesis testing (`fix_type: hypothesis`)

1. **One-task gate** — cheap falsification with baseline comparison. Choose the first unresolved instance from the active batch.
2. **Batch gate** — only if one-task justifies it; rerun baseline and candidate on ALL instances in the active batch (read from `validation-sets.json`).
3. **Full evolution set** — stop and ask user; never start without explicit approval.
4. **Test set** — **ABSOLUTELY FORBIDDEN** without human consent AND only after the evolution set is fully resolved or a confirmed plateau. See `docs/VALIDATION_POLICY.md`.

**Reading the active batch:**

```text
Read artifacts/meta/validation-sets.json → find lowest batch with status "active" or "expanded"
```

Rules:

- Same task ids, model, iteration cap, token policy, and timeout for baseline and candidate at each gate.
- Record in the dossier which gate you completed and which batch.
- If one-task improves but batch gate regresses, set decision to `keep unmerged`, `rerun`, or `expand task set`.
- **Trace-targeted** hypotheses: regression means worse `patch_published` or worse **named** trace metrics — not flat `resolved` alone when trace targets improved and patch publication held.
- Low iteration caps (4, 8, 16, 32) are smoke checks only.
- **NEVER** run or inspect instances from the test set. The test set is off-limits until the evolution set is fully resolved.
- After each hypothesis attempt that produces **no Pareto improvement** on the active batch, increment `no_improvement_count` in `validation-sets.json`. Reset to 0 on any improvement. When `no_improvement_count` reaches 20, activate the next locked batch (set its status to `expanded`) and reset the counter.

---

## Minimum execution loop (checklist)

1. `git status --short --branch` — ensure correct branch.
2. Read latest dossiers and comparable `result.json` for context.
3. If generating a new hypothesis family, read `docs/references/research/agent-evolution-literature.md`.
4. If touching LangChain/LangGraph, read `docs/references/langchain/curated/` as needed.
5. Implement the assigned change (narrow).
6. `uv run python -m compileall -q src scripts`
7. Load `.env`, run one-task gate with stable profile.
8. If one-task passes, run batch gate. If batch gate passes, stop and ask user.
9. Fill dossier result sections including **Search node (MCTS)**; update `hypothesis-index.jsonl` on branch.
10. Commit with exhaustive evidence in message.
11. Push branch to `origin`.
12. Append `meta-events` lines for executor start/finish with `run_id` and `commit_sha`.
13. Record execution summary: branch, push status, run ids, metrics, decision draft.

If a run fails before writing `trace.jsonl`, fix observability before optimizing agent behavior.

---

## Publishing and failure modes

- Every completed hypothesis must be pushed to `origin` (code + dossier). Never leave a hypothesis only locally.
- Merge to `main` only after Phase 4 analysis confirms per `prompt-unified.md` §Phase 5; otherwise registry-only.
- If credentials or runtime dependencies are missing: push the branch if code changed, mark `rejected`, document the blocker in the dossier, append executor events.
