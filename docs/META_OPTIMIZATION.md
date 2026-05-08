# Meta-Optimization Manual

This is the operating manual for the meta-LLM. The meta-LLM does not solve SWE-bench tasks directly. It improves the evolving agent and harness, tests hypotheses on branches, and records every result so the project does not repeat failed experiments.

## System Model

There are two layers:

- Evolving agent: code under `src/evolve2_agent_bench/agent/`. This is the agent evaluated on SWE-bench Verified and evolved over time.
- Meta layer: this manual, `artifacts/meta/experiment-ledger.jsonl`, git branches, and run traces. This layer decides which hypothesis to test next.

The benchmark runner under `src/evolve2_agent_bench/bench/` prepares a task repository, runs the evolving agent, writes a patch, sends the patch to the SWE-bench harness, and records traces.

Do not treat chat memory as the source of truth. Use repository files, `trace.jsonl`, `result.json`, git history, branch names, and the experiment ledger.

## Git Workflow For Hypotheses

Git is part of the experimental method.

- `main` contains the mainstream version of the evolving agent.
- Every hypothesis gets its own branch from current `main`.
- Branch names should be stable and descriptive: `hyp/<YYYYMMDD>-<short-hypothesis>`.
- Commit all code, doc, and ledger changes for the hypothesis branch.
- Merge into `main` only if the hypothesis is confirmed by the agreed benchmark comparison.
- Do not delete failed hypothesis branches. They are historical evidence and may be revisited.
- Failed branches must still end with a commit that records the tested hypothesis, run ids, metrics, failure class, and decision in `artifacts/meta/experiment-ledger.jsonl`.
- Do not start a new hypothesis branch from an unconfirmed hypothesis branch. Start from `main` unless the ledger explicitly records a dependency.

Branch lifecycle:

1. Start clean on `main`.
2. Create `hyp/<date>-<slug>`.
3. Add a pending ledger record or write the hypothesis in the commit message before implementation.
4. Implement one narrow change.
5. Run validation and benchmark comparison.
6. Update the ledger with final metrics and decision.
7. Commit the complete hypothesis artifact.
8. If confirmed, merge the branch into `main` with a merge commit whose message summarizes the evidence.
9. If rejected, leave the branch unmerged and keep it available.

Merge commit descriptions must be exhaustive enough for a future meta-agent to understand the decision without reading chat. Include:

- hypothesis id and branch name;
- parent baseline run ids and candidate run ids;
- task ids;
- code surfaces changed;
- metric deltas;
- Pareto assessment;
- decision and rationale;
- known residual risks.

Rejected branch final commit messages should include the same fields and clearly state `Decision: rejected`.

## Central Hypothesis Artifact

The central artifact is:

```text
artifacts/meta/experiment-ledger.jsonl
```

It is append-only JSONL. Every hypothesis must have a record, including failed, inconclusive, and infrastructure-only experiments.

Required fields:

```json
{
  "experiment_id": "YYYYMMDD-HHMMSS-short-label",
  "branch": "hyp/YYYYMMDD-short-label",
  "status": "baseline | pending | confirmed | rejected | inconclusive",
  "parent_branch": "main",
  "parent_agent_git_sha": "git sha before the change, or uncommitted",
  "candidate_git_sha": "git sha after the change, or uncommitted",
  "hypothesis": "Specific expected improvement and metric.",
  "change_summary": "Files changed and behavior changed.",
  "task_ids": ["astropy__astropy-12907"],
  "baseline_run_ids": ["previous comparable run id"],
  "candidate_run_ids": ["new run id"],
  "metrics": {
    "baseline": {
      "resolved": 0,
      "wall_seconds": 119.284,
      "llm_calls": 1,
      "tool_calls": 1,
      "invalid_action_count": 0,
      "prompt_tokens": 685,
      "completion_tokens": 1800,
      "patch_bytes": 0,
      "failure_class": "no_patch"
    },
    "candidate": {
      "resolved": 0,
      "wall_seconds": 80.0,
      "llm_calls": 1,
      "tool_calls": 1,
      "invalid_action_count": 0,
      "prompt_tokens": 600,
      "completion_tokens": 900,
      "patch_bytes": 0,
      "failure_class": "no_patch"
    }
  },
  "pareto_assessment": "Dominates baseline on completion_tokens and wall_seconds; no solve-rate improvement.",
  "finding": "What happened and the evidence path.",
  "decision": "keep unmerged | merge to main | expand task set | superseded by experiment id",
  "next_action": "One concrete next step."
}
```

Evidence paths should point to files such as `artifacts/runs/<run_id>/trace.jsonl`. Do not copy full traces into the ledger.

## First Commands

From the repo root:

```bash
uv sync
export OPENROUTER_API_KEY=...
uv run evolve2 model-check
```

Run one benchmark task:

```bash
uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 8 --evaluation-timeout 1800
```

Summarize a run:

```bash
uv run python scripts/summarize_trace.py 20260508-164503-astropy__astropy-12907
```

Compact timeline:

```bash
jq -r '[.event,.stream,.iteration,.tool_name] | @tsv' artifacts/runs/<run_id>/trace.jsonl
```

Read one event stream:

```bash
jq 'select(.stream == "llm")' artifacts/runs/<run_id>/trace.jsonl
jq 'select(.stream == "tool")' artifacts/runs/<run_id>/trace.jsonl
jq 'select(.event == "invalid_action")' artifacts/runs/<run_id>/trace.jsonl
```

Validate repository code:

```bash
uv run python -m compileall -q src scripts
```

## Run Artifacts

Each run writes `artifacts/runs/<run_id>/`.

- `trace.jsonl`: canonical unified timeline. Start here.
- `result.json`: compact outcome, wall time, patch size, and SWE-bench report.
- `patch.diff`: patch generated by the evolving agent.
- `prediction.jsonl`: SWE-bench prediction file.
- `evaluation_stdout.log` and `evaluation_stderr.log`: SWE-bench harness output.
- `agent_events.jsonl`, `llm_calls.jsonl`, `shell_events.jsonl`: secondary slices for focused inspection.

`trace.jsonl` is JSONL, one event per line. Important event names:

- `run_start`: run id, model, dataset, task id.
- `task_loaded`: public task input available to the agent.
- `workspace_prepare_start` and `workspace_prepare_finish`: repository checkout.
- `agent_start`: agent task input and workspace.
- `llm_call`: full system/user messages, raw model response, latency, and token usage if provided.
- `invalid_action`: model output that could not be parsed into an action.
- `agent_action`: parsed action and arguments.
- `tool_call`: tool name and input before execution.
- `shell_command` or `tool_result`: tool output.
- `agent_observation`: observation appended back into the agent loop.
- `patch_created`: generated patch and patch byte size.
- `evaluation_start` and `evaluation_finish`: SWE-bench harness execution and report.
- `run_finish`: final result object.

The task artifact intentionally excludes SWE-bench gold patch and hidden evaluator fields. Do not add them to the agent input or trace. The benchmark may use hidden fields internally through the official SWE-bench harness, but the evolving agent must not see them.

## How To Analyze A Trace

Use this order every time:

1. Open `result.json`. Record `resolved_instances`, `empty_patch_instances`, `error_instances`, `patch_bytes`, and `wall_seconds`.
2. Run `scripts/summarize_trace.py <run_id>`. Record LLM calls, tool calls, invalid actions, and token usage.
3. Read the `trace.jsonl` timeline from the first failure point, not only from the final event.
4. Compare `llm_call.response` with the next `agent_action` or `invalid_action`.
5. For each tool call, inspect the matching tool output and the next LLM input. Check whether useful evidence was lost, truncated, or ignored.
6. Inspect `patch_created`. If the patch is empty, classify why the agent never edited tracked files.
7. Inspect `evaluation_finish.report`. If SWE-bench failed with errors, inspect `evaluation_stdout.log` and `evaluation_stderr.log`.
8. Write one failure class and one candidate hypothesis. Do not implement multiple unrelated fixes in one experiment.

Common failure classes:

- `no_patch`: no tracked source change was produced.
- `invalid_action_protocol`: the model response did not match the action schema.
- `repeated_action`: the agent repeats the same unproductive action.
- `bad_localization`: the agent looked in the wrong files or missed the relevant code path.
- `bad_patch`: patch exists but does not address the issue.
- `local_test_failure`: focused tests fail before SWE-bench evaluation.
- `evaluation_error`: SWE-bench harness did not complete normally.
- `resolved`: SWE-bench marks the instance resolved.

## Pareto Optimization

Pareto optimization means a change is preferred only when it improves at least one important metric without an unacceptable regression in another important metric.

Primary metric:

- `resolved`: number of SWE-bench tasks solved.

Secondary metrics:

- `wall_seconds`: lower is better.
- `prompt_tokens`, `completion_tokens`, `total_tokens`: lower is better at equal or better solve rate.
- `llm_calls`: lower is better unless extra calls materially improve solve rate.
- `tool_calls`: lower is better unless extra calls are targeted validation.
- `patch_bytes`: smaller is usually better for narrow fixes, but not if correctness drops.
- `invalid_action_count`: lower is better.
- `failure_class`: moving from `evaluation_error` to `bad_patch`, or from `no_patch` to `bad_patch`, can be progress even before resolution improves.

A candidate is Pareto-dominant when it has equal or better `resolved` and improves at least one secondary metric without materially worsening the rest. A candidate is not automatically better if it only adds complexity, cost, or wall time without changing failure class or solve rate.

When tradeoffs are unclear, keep both candidates and run a larger fixed task set. Do not declare a global improvement from one task unless the failure mode is purely infrastructural, such as action parsing or trace completeness.

## How To Evolve The Agent

Use small experiments:

1. Start on `main` and create a hypothesis branch.
2. Select one failure mode from the latest trace.
3. Write a hypothesis before editing code.
4. Change the smallest relevant surface.
5. Run the same task again.
6. Compare metrics against the parent run.
7. Record the result in `artifacts/meta/experiment-ledger.jsonl`.
8. Commit the branch with the complete hypothesis evidence.
9. Merge only if the hypothesis is confirmed.

Good experiment examples:

- Hypothesis: "If tool-call shaped outputs are accepted, invalid action count drops and the agent reaches shell execution earlier."
- Hypothesis: "If the finalization prompt requires a tracked source diff before finish, empty patch rate drops."
- Hypothesis: "If read_file results are summarized after 400 lines, token usage drops without worsening localization."

Bad experiment examples:

- "Make the agent smarter."
- "Rewrite the whole harness."
- "Add many tools and see what happens."

Allowed change surfaces:

- `src/evolve2_agent_bench/agent/base.py`: loop, prompt, parsing, action protocol.
- `src/evolve2_agent_bench/agent/actions.py`: action schema.
- `src/evolve2_agent_bench/agent/tools.py`: tool behavior and observations.
- `src/evolve2_agent_bench/bench/swebench_runner.py`: benchmark orchestration and artifact writing.
- this manual and meta ledger under `artifacts/meta/`.

Keep benchmark leakage rules intact. Never expose gold patch, `test_patch`, `FAIL_TO_PASS`, or `PASS_TO_PASS` to the evolving agent.

## LangChain And LangGraph Evolution Surface

This project intentionally uses LangChain. Before proposing changes to the agent loop, memory, tools, context, structured output, or graph control flow, inspect the offline official references under:

```text
docs/references/langchain/
```

The raw official docs are:

- `docs/references/langchain/llms.txt`
- `docs/references/langchain/llms-full.txt`
- `docs/references/langchain/langgraph-llms.txt`

The curated Python subset is under `docs/references/langchain/curated/`. Start with `docs/references/langchain/README.md` to choose the relevant file.

Use these references to formulate implementation hypotheses. Examples:

- Tool protocol hypothesis: read `curated/langchain-tools.md` and `curated/langchain-structured-output.md`, then test whether native LangChain tools or structured outputs reduce `invalid_action_count`.
- Context hypothesis: read `curated/langchain-context-engineering.md`, then test whether summarized tool observations reduce token usage without worsening `failure_class`.
- Middleware hypothesis: read `curated/langchain-middleware-built-in.md` and `curated/langchain-middleware-custom.md`, then test model-call or tool-call middleware for retries, output repair, or guardrails.
- Memory hypothesis: read `curated/langchain-short-term-memory.md`, `curated/langchain-long-term-memory.md`, and `curated/langgraph-add-memory.md`, then test whether persistent run memory helps avoid repeated failed actions across attempts.
- Graph-control hypothesis: read `curated/langgraph-overview.md`, `curated/langgraph-thinking.md`, and `curated/langgraph-fault-tolerance.md`, then test whether an explicit LangGraph state machine improves recovery from invalid actions, repeated actions, or evaluation errors.
- Evaluation hypothesis: read `curated/langchain-agent-evals.md` and `curated/langchain-unit-testing.md`, then add tests for agent trajectories before running expensive SWE-bench evaluations.

Do not add a LangChain or LangGraph feature because it exists. Each feature must be tied to a failure class, expected metric movement, and a branch-level hypothesis.

## Research Frame For Generating Hypotheses

Use literature to generate mechanisms, not direct to-do lists. The standing research frame is:

```text
docs/references/research/agent-evolution-literature.md
```

Before creating a new kind of hypothesis, read the relevant section of that note and map it to a local trace failure class. The note covers directions such as agent-computer interfaces, trace reflection, Pareto-efficient text evolution, bounded search, experience banks, skills, synthetic tasks, and evaluation robustness.

The required conversion is:

```text
paper mechanism -> local failure class -> one branch hypothesis -> benchmark comparison -> ledger decision
```

Do not create a branch from a paper idea until there is trace evidence that the idea targets an observed failure.

## Minimum Meta-Agent Loop

For every work cycle:

1. `git status --short --branch`
2. Ensure the starting point is `main` unless continuing a documented hypothesis branch.
3. Read this manual, latest ledger entries, and latest comparable `result.json`.
4. Summarize the latest trace with `scripts/summarize_trace.py`.
5. If generating a new hypothesis family, read `docs/references/research/agent-evolution-literature.md`.
6. If the hypothesis touches LangChain or LangGraph behavior, read the relevant local files under `docs/references/langchain/curated/`.
7. Choose one hypothesis and create `hyp/<date>-<slug>`.
8. Edit code or docs.
9. Run `uv run python -m compileall -q src scripts`.
10. Run the fixed comparison task.
11. Append or update the ledger record.
12. Commit the branch with exhaustive evidence in the commit message.
13. Report the delta: baseline run, candidate run, metric changes, Pareto assessment, and merge decision.

If a run fails before writing `trace.jsonl`, fix observability before optimizing agent behavior.
