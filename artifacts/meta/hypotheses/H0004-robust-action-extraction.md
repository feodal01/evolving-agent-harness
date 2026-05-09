# H0004 Robust Action Extraction

Status: rejected

Branch: `hyp/H0004-last-json-action`

Created: 2026-05-08
Updated: 2026-05-08

## Hypothesis

If the action parser extracts the last valid action from multi-action responses and accepts provider-style `call:<action>{...}` tool calls for the existing action schema, then `invalid_action_count` will drop and the agent will execute more concrete repository actions within the same iteration budget, measured on `astropy__astropy-12907`.

## Motivation

The fresh 16-iteration baseline run on `main` shows that the old 4-step comparison was not the binding limit. The agent still produced an empty patch after 16 iterations, but the dominant failure became action extraction:

- 10 invalid actions out of 16 LLM calls.
- Multiple invalid responses were provider-style calls such as `<|tool_call>call:run_shell{command: "pip install -e ."}<tool_call|>`.
- Earlier traces showed multi-action responses where the model self-corrected later in the same response, but the parser executed the first valid JSON object.

This maps the Agent-Computer Interface research direction to the local `invalid_action_protocol` and `no_patch` failure classes: the existing interface receives usable action intent but discards it when the surface syntax differs from the strict JSON-only contract.

## Baseline Evidence

- Baseline branch/commit: `main` / `94e3f14`
- Baseline run ids:
  - `20260508-182634-astropy__astropy-12907`
  - prior shorter comparison: `20260508-180609-astropy__astropy-12907`
- Trace paths:
  - `artifacts/runs/20260508-182634-astropy__astropy-12907/trace.jsonl`
  - `artifacts/runs/20260508-180609-astropy__astropy-12907/trace.jsonl`
- Failure class: `no_patch` plus `invalid_action_protocol`
- Key observed events:
  - `agent_iterations=16`
  - `invalid_action_count=10`
  - `patch_bytes=0`
  - `empty_patch_instances=1`
  - provider-style `run_shell` calls occurred repeatedly but were rejected by the parser.

## Proposed Change

Change only `BaselineLangChainAgent._parse_action` and small parser helpers in `src/evolve2_agent_bench/agent/base.py`:

- collect all valid JSON action objects in a response and execute the last one;
- add a narrow fallback for existing provider-style tool calls:
  - optional `<|tool_call>` wrappers;
  - `call:<action>{...}` where `<action>` is an existing local action;
  - simple object arguments with quoted string values and bare keys;
  - `call:{...}` when the payload is already a full JSON action object.

Non-goals:

- Do not add new tools.
- Do not change prompt text, model, token limits, benchmark orchestration, or workspace behavior.
- Do not merge unless benchmark evidence shows a Pareto improvement.

## Test Plan

- Validation commands:
  - `uv run python -m compileall -q src scripts`
  - local parser checks for the observed provider-style calls, malformed syntax rejection, and last-valid JSON selection.
- Benchmark task ids:
  - `astropy__astropy-12907`
- Max iterations / timeout:
  - candidate: `--max-iterations 16 --evaluation-timeout 1800`
- Metrics to compare:
  - `invalid_action_count`
  - `agent_actions`
  - `resolved_instances`
  - `empty_patch_instances`
  - `patch_bytes`
  - `wall_seconds`
  - token usage
- Stop condition:
  - one candidate run with the same 16-iteration budget, or document an exact credential/runtime blocker.

## Expected Pareto Movement

- Primary metric: lower `invalid_action_count`.
- Secondary metrics: more executed actions without worsening `resolved_instances`, `empty_patch_instances`, or evaluation errors.
- Regression risks: accepting more provider-style commands may execute low-value shell actions, increasing wall time or preserving the same empty-patch outcome.

## Result

Implemented robust action extraction in `BaselineLangChainAgent._parse_action`:

- valid JSON action objects are collected across the response and the last valid action is executed;
- provider-style calls such as `<|tool_call>call:run_shell{command: "pip install -e ."}<tool_call|>` are accepted for the existing action schema;
- malformed provider syntax remains invalid.

Validation passed:

- `uv run python -m compileall -q src scripts`
- local parser checks for provider-style `run_shell`, last-valid JSON selection, and malformed syntax rejection
- `uv run evolve2 model-check`

Candidate run `20260508-184725-astropy__astropy-12907` used the same 16-iteration budget as the fresh baseline. It reduced invalid actions and increased executed actions, but still produced an empty patch. The run did reach a useful source read earlier than baseline and later identified the likely Astropy fix in natural language (`cright[-right.shape[0]:, -right.shape[1]:] = right`), but did not edit tracked source.

Because the user clarified that older low iteration limits were not important, a second candidate run `20260508-190035-astropy__astropy-12907` used `--max-iterations 32`. It executed substantially more actions and mostly wrote repeated reproduction scripts, but still ended with `patch_bytes=0` and `empty_patch_instances=1`. The larger budget confirms that robust action extraction alone does not overcome the dominant `no_patch` behavior.

## Metrics

| Metric | Baseline | Candidate | Delta |
| --- | --- | --- | --- |
| Resolved instances | 0 | 0 | 0 |
| Empty patch instances | 1 | 1 | 0 |
| Patch bytes | 0 | 0 | 0 |
| Invalid actions | 10 | 6 | -4 |
| Agent actions | 6 | 10 | +4 |
| Agent iterations | 16 | 16 | 0 |
| Total tokens | 80820 | 126638 | +45818 |
| Wall seconds | 291.792 | 422.128 | +130.336 |

Extended non-decision run:

| Metric | Baseline 16-step | Candidate 32-step | Delta |
| --- | --- | --- | --- |
| Resolved instances | 0 | 0 | 0 |
| Empty patch instances | 1 | 1 | 0 |
| Patch bytes | 0 | 0 | 0 |
| Invalid actions | 10 | 8 | -2 |
| Agent actions | 6 | 24 | +18 |
| Agent iterations | 16 | 32 | +16 |
| Total tokens | 80820 | 71297 | -9523 |
| Wall seconds | 291.792 | 1096.198 | +804.406 |

## Pareto Assessment

Rejected for merge. The parser change improved the targeted protocol metrics at equal iteration budget (`invalid_action_count` decreased from 10 to 6, executed actions increased from 6 to 10), and an extended 32-step run confirmed the agent can execute many more actions. However, the benchmark outcome did not improve (`resolved_instances=0`, `empty_patch_instances=1`, `patch_bytes=0`) and same-budget wall time and token use worsened.

The new dominant failure class is more specific than the prior parser failure: the agent can inspect relevant source and repeatedly create reproduction scripts, but it does not modify tracked source even after identifying the likely code change. Future hypotheses should target a structured tracked-source edit path or stronger source-edit finalization criteria rather than broader parsing.

## Decision

Keep unmerged. Do not merge H0004 code to `main`. Publish the hypothesis branch for evidence, then update only the central hypothesis registry and dossier on `main`.

## Evidence Links

- Baseline run: `artifacts/runs/20260508-182634-astropy__astropy-12907/result.json`
- Baseline trace: `artifacts/runs/20260508-182634-astropy__astropy-12907/trace.jsonl`
- Candidate run: `artifacts/runs/20260508-184725-astropy__astropy-12907/result.json`
- Candidate trace: `artifacts/runs/20260508-184725-astropy__astropy-12907/trace.jsonl`
- Extended candidate run: `artifacts/runs/20260508-190035-astropy__astropy-12907/result.json`
- Extended candidate trace: `artifacts/runs/20260508-190035-astropy__astropy-12907/trace.jsonl`
- Commit:
