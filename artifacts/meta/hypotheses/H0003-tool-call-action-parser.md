# H0003 Tool Call Action Parser

Status: rejected

Branch: `hyp/H0003-tool-call-action-parser`

Created: 2026-05-08
Updated: 2026-05-08

## Hypothesis

If the action parser accepts the tool-call-shaped responses observed in `H0002`, then `invalid_action_count` will decrease and the agent will continue executing concrete actions instead of spending iterations on protocol repair, measured on `astropy__astropy-12907`.

## Motivation

The latest candidate trace for `H0002` shows two invalid actions after the model emitted non-JSON tool-call syntax:

- `<|tool_call>call:run_shell{command: "pip install erfa"}<tool_call|>`
- `call:run_shell{command: "pip install erfa"}`

Both are structurally clear tool calls, but the current parser only accepts JSON objects. This created the `invalid_action_protocol` failure class on top of the existing `no_patch` result. LangChain's local tool and structured-output references describe tools as callable functions with well-defined input schemas, which supports treating provider-style tool-call syntax as a parseable action when it maps cleanly to the local schema.

## Baseline Evidence

- Baseline branch/commit: `main` / `9cf4404`
- Baseline run ids: `20260508-174807-astropy__astropy-12907`
- Trace paths: `artifacts/runs/20260508-174807-astropy__astropy-12907/trace.jsonl`
- Failure class: `no_patch` plus `invalid_action_protocol`
- Key observed events:
  - `invalid_action_count=2`
  - invalid raw responses were both `run_shell` calls in provider-style syntax
  - final patch was empty: `patch_bytes=0`, `empty_patch_instances=1`

## Proposed Change

Add a narrow parser fallback in `BaselineLangChainAgent._parse_action` that recognizes a single provider-style local tool call:

- optional `<|tool_call>` wrappers
- `call:<action>{...}` payload
- JSON-object-like arguments where keys may be bare identifiers

The fallback should build the existing `AgentAction` model and should not add new tools, change prompt content, or relax validation beyond the current action schema.

Non-goals:

- Do not migrate the agent to LangChain `create_agent`.
- Do not add provider-native tool execution.
- Do not change benchmark orchestration, model selection, token limits, or workspace tools.
- Do not merge code unless benchmark evidence confirms a Pareto improvement.

## Test Plan

- Validation commands:
  - `uv run python -m compileall -q src scripts`
  - local parser checks for observed tool-call syntax and malformed syntax rejection
- Benchmark task ids:
  - `astropy__astropy-12907`
- Max iterations / timeout:
  - candidate: `--max-iterations 4 --evaluation-timeout 1800`
- Metrics to compare:
  - `invalid_action_count`
  - `resolved_instances`
  - `empty_patch_instances`
  - `patch_bytes`
  - `agent_iterations`
  - `wall_seconds`
- Stop condition:
  - one candidate run, or document the exact credential/runtime blocker if OpenRouter execution cannot start.

## Expected Pareto Movement

- Primary metric: lower `invalid_action_count`.
- Secondary metrics: equal or better `resolved_instances`, no increase in empty patches, and no evaluation errors.
- Regression risks: accepting tool-call syntax may execute low-value commands that the previous parser rejected, increasing wall time or preserving the same `no_patch` outcome.

## Result

Implemented a narrow parser fallback in `BaselineLangChainAgent._parse_action` for the provider-style tool-call shape observed in `H0002`.

Validation completed:

- `uv run python -m compileall -q src scripts`
- local parser checks confirmed both observed forms parse as `run_shell` actions:
  - `<|tool_call>call:run_shell{command: "pip install erfa"}<tool_call|>`
  - `call:run_shell{command: "pip install erfa"}`
- local malformed syntax check confirmed `call:run_shell[]` remains invalid.

Model and benchmark execution completed with variables loaded from `.env`:

- `uv run evolve2 model-check`
- `uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 4 --evaluation-timeout 1800`

Candidate run `20260508-180609-astropy__astropy-12907` completed. The run still produced an empty patch and did not resolve the task. The parser fallback was not exercised in the candidate trace: iterations 1-3 parsed existing JSON blocks and executed shell commands; iteration 4 received an empty model response and remained invalid. The candidate therefore does not demonstrate that accepting provider-style tool-call syntax improves benchmark behavior.

## Metrics

| Metric | Baseline | Candidate | Delta |
| --- | --- | --- | --- |
| Resolved instances | 0 | 0 | 0 |
| Empty patch instances | 1 | 1 | 0 |
| Patch bytes | 0 | 0 | 0 |
| Invalid actions | 2 | 1 | -1 |
| Agent iterations | 4 | 4 | 0 |
| Tool calls | 2 | 3 | +1 |
| Prompt tokens | 7833 | 5280 | -2553 |
| Completion tokens | 2156 | 5011 | +2855 |
| Total tokens | 9989 | 10291 | +302 |
| Wall seconds | 146.186 | 280.574 | +134.388 |

## Pareto Assessment

Rejected. Although invalid actions decreased from 2 to 1, the target provider-style tool-call syntax did not recur in the candidate trace, so the local parser change has no benchmark evidence of causality. The primary task outcome did not improve (`resolved_instances=0`, `empty_patch_instances=1`, `patch_bytes=0`), while wall time and total token usage worsened.

## Decision

Keep unmerged. Do not merge the parser fallback into `main`. A future hypothesis should target the observed dominant behavior more directly: repeated low-value reproduction shell scripts, missing dependency handling for `erfa`, empty model responses, or stronger requirements to inspect/edit tracked source files before iteration budget is exhausted.

## Evidence Links

- Candidate run: `artifacts/runs/20260508-180609-astropy__astropy-12907/result.json`
- Candidate trace: `artifacts/runs/20260508-180609-astropy__astropy-12907/trace.jsonl`
- Commit: branch HEAD commit for `hyp/H0003-tool-call-action-parser`
