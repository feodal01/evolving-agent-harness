# H0009 Structured Action Contract for Tool Args

Status: inconclusive

Branch: `hyp/H0009-structured-action-contract`

Created: 2026-05-16
Updated: 2026-05-16

## Hypothesis

If JSON turns are parsed through an intermediate schema (`thought`, `action`, loose `args`) and each action’s `args` are validated with the existing Pydantic tool-arg models before constructing `AgentAction`, then invalid tool arguments surface earlier with clearer errors and fewer ambiguous failures on `astropy__astropy-12907`, measured against baseline invalid-action and patch publication counts.

## Motivation

Prior parser-focused hypotheses (H0003/H0004) failed merge criteria but pointed at protocol fragility. This branch narrows the surface: enforce typed args per action without changing the outward JSON protocol seen by the model.

## Baseline Evidence

- Parent context: H0007 inconclusive; dominant failure classes remain `invalid_action_protocol` / `no_patch` on the gate task.
- Benchmark runs for this branch: **not executed** — prior spawned executor exited before gates.

## Proposed Change

- `src/evolve2_agent_bench/agent/base.py`: `_LooseAgentTurn`, `_agent_action_from_payload`, validate `args` via `_ARGS_SCHEMAS`.
- `src/evolve2_agent_bench/agent/actions.py`: minor adjustments supporting the validation path (see commit).

Non-goals: new tools, harness changes, LangGraph migration.

## Test Plan

- `uv run python -m compileall -q src scripts`
- `uv run evolve2 model-check`
- One-task: `astropy__astropy-12907`, `--max-iterations 100 --evaluation-timeout 1800`

## Result

Orchestrator rescue commit records implementation only. **One-task gate was not run** in the stranded executor round; status remains inconclusive pending a fresh executor run.

## Decision

Keep unmerged until benchmark evidence exists.

## Search node (MCTS)

- **Parent state**: H0007 lineage / parser fragility cluster.
- **Value summary**: code landed; measurement missing — treat value as unknown.
- **Revisit queue**: rerun executor one-task gate from this branch tip.

## Evidence Links

- Branch tip: `hyp/H0009-structured-action-contract` (see `git log -1`)
