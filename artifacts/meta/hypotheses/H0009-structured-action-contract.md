# H0009 Structured Action Contract for Tool Args

Status: rejected

Branch: `hyp/H0009-structured-action-contract`

Created: 2026-05-16
Updated: 2026-05-17

## Hypothesis

If JSON turns are parsed through an intermediate schema (`thought`, `action`, loose `args`) and each action’s `args` are validated with the existing Pydantic tool-arg models before constructing `AgentAction`, then invalid tool arguments surface earlier with clearer errors and fewer ambiguous failures on `astropy__astropy-12907`, measured against baseline invalid-action and patch publication counts.

## Motivation

Prior parser-focused hypotheses (H0003/H0004) failed merge criteria but pointed at protocol fragility. This branch narrows the surface: enforce typed args per action without changing the outward JSON protocol seen by the model.

## Baseline Evidence

- Parent context: H0007 rejected; dominant failure classes remain `invalid_action_protocol` / `no_patch` on the gate task.
- Baseline run id for this gate: **not recorded** in this executor session (parent `main` @ `1df90f1f759c8bf6b7fcb682da422271fd4c6fcc` per board); compare future runs against an explicit baseline at the same profile.

## Proposed Change

- `src/evolve2_agent_bench/agent/base.py`: `_LooseAgentTurn`, `_agent_action_from_payload`, validate `args` via `_ARGS_SCHEMAS`.
- `src/evolve2_agent_bench/agent/actions.py`: minor adjustments supporting the validation path (see commit).

Non-goals: new tools, harness changes, LangGraph migration.

## Test Plan

- `uv run python -m compileall -q src scripts`
- `uv run evolve2 model-check`
- One-task: `astropy__astropy-12907`, `--max-iterations 100 --evaluation-timeout 1800`

## Result

**One-task gate attempt (`astropy__astropy-12907`)** — rescue executor 2026-05-17.

Harness **aborted mid-rollout** during agent iteration 46: OpenRouter / chat-completions path raised `JSONDecodeError: Expecting value` while parsing the HTTP response body (non-JSON or truncated response at client). **No** `result.json`, **no** `patch.diff`, **no** SWE-bench evaluation report.

Partial trace was written (`trace.jsonl`, `llm_calls.jsonl`, `agent_events.jsonl`). Summarize output (see **Metrics**) reflects activity **up to failure** — not a completed gate outcome.

## Metrics

Source: `uv run python scripts/summarize_trace.py 20260517-085014-astropy__astropy-12907` (partial run).

| Metric | Baseline | Candidate | Delta |
| --- | --- | --- | --- |
| Resolved instances | — | — (no eval) | — |
| Patch published / patch bytes | — | none | — |
| Wall seconds | — | — | — |
| Invalid actions (trace) | — | 28 | — |
| LLM calls (trace) | — | 46 | — |
| Agent actions (trace) | — | 18 | — |
| Tool: read_file / write_file / shell | — | 6 / 6 / 6 | — |
| Prompt / completion / total tokens | — | 419_062 / 707_313 / 1_126_375 | — |

## Pareto Assessment

**Inconclusive.** The candidate cannot be ranked against baseline on `resolved` or trace-targeted protocol metrics: the run did not reach patch publication or evaluation. **Infrastructure / provider response parsing failure** is the blocker — rerun the gate after confirming OpenRouter availability and stable JSON responses for `google/gemma-4-26b-a4b-it`.

## Decision

**Keep unmerged** — no decisive task outcome; treat as **blocked** until a full one-task gate completes without provider JSON errors.

## Search node (MCTS)

- **Parent state**: `main` / H0007 lineage / parser fragility cluster (`parent_commit` on board: `1df90f1f759c8bf6b7fcb682da422271fd4c6fcc`).
- **Rollout depth**: `one-task` attempted; **sample incomplete** (harness crash).
- **Value summary**: Partial trace shows continued tool use through iteration 46; token and `invalid_action` counts are **not** decision-grade without baseline at same profile and without completed evaluation.
- **Revisit queue**: Rerun one-task gate; optional: capture HTTP status/body on parse failure in harness for faster diagnosis.

## Evidence Links

- Candidate run (partial): `artifacts/runs/20260517-085014-astropy__astropy-12907/`
- Trace: `artifacts/runs/20260517-085014-astropy__astropy-12907/trace.jsonl`
- Branch: `hyp/H0009-structured-action-contract`
