# Meta-Optimization Manual

This is the operating manual for the meta-LLM. The meta-LLM does not solve SWE-bench tasks directly. It improves the evolving agent and harness, tests hypotheses on branches, and records every result so the project does not repeat failed experiments.

## System Model

There are two layers:

- Evolving agent: code under `src/evolve2_agent_bench/agent/`. This is the agent evaluated on SWE-bench Verified and evolved over time.
- Meta layer: this manual, `artifacts/meta/hypothesis-index.jsonl`, per-hypothesis dossiers, git branches, and run traces. This layer decides which hypothesis to test next.

The benchmark runner under `src/evolve2_agent_bench/bench/` prepares a task repository, runs the evolving agent, writes a patch, sends the patch to the SWE-bench harness, and records traces.

Do not treat chat memory as the source of truth. Use repository files, `trace.jsonl`, `result.json`, git history, branch names, the hypothesis index, and hypothesis dossiers.

## Autonomy Contract

During a meta-optimization session, the meta-agent works autonomously. The user has already granted permission to:

- choose the next hypothesis id and branch name;
- create and switch branches;
- edit code, docs, and meta artifacts within the repository rules;
- run validation and benchmark commands;
- commit hypothesis branches;
- push hypothesis branches;
- publish registry-only updates on `main`;
- merge confirmed hypotheses into `main` when the dossier evidence supports the merge.

Do not stop to ask the user for routine approval. Ask the user only for hard blockers that cannot be resolved from repository context, such as:

- the OpenRouter model/API is unavailable after retrying the documented check;
- required credentials are missing from `.env`;
- Docker, git, uv, or SWE-bench infrastructure is unavailable in a way that prevents the run;
- the worktree has conflicting user changes that would be overwritten;
- the benchmark result is impossible to interpret because required artifacts are missing or corrupt.

If a blocker occurs after code changes were made, finish the hypothesis lifecycle as `inconclusive`: push the hypothesis branch if possible, publish a registry-only result to `main`, and document the blocker in the dossier.

## Git Workflow For Hypotheses

Git is part of the experimental method.

- `main` contains the mainstream version of the evolving agent.
- Every hypothesis gets its own branch from current `main`.
- Branch names should be stable and descriptive: `hyp/HXXXX-<short-hypothesis>`.
- Commit all code, doc, and hypothesis artifact changes for the hypothesis branch.
- Push every hypothesis branch to `origin`, whether it is confirmed, rejected, or inconclusive.
- Merge into `main` only if the hypothesis is confirmed by the agreed benchmark comparison.
- Do not delete failed hypothesis branches. They are historical evidence and may be revisited.
- Failed branches must still end with a commit that records the tested hypothesis, run ids, metrics, failure class, and decision in its dossier under `artifacts/meta/hypotheses/`.
- Do not start a new hypothesis branch from an unconfirmed hypothesis branch. Start from `main` unless the hypothesis dossier explicitly records a dependency.

Branch lifecycle:

1. Start clean on `main`.
2. Create `hyp/HXXXX-<slug>`.
3. Create a hypothesis dossier before implementation.
4. Implement one narrow change.
5. Run validation and benchmark comparison.
6. Update the dossier and compact hypothesis index with final metrics and decision.
7. Commit the complete hypothesis artifact.
8. Push the hypothesis branch to `origin`.
9. If confirmed, merge the branch into `main` with a merge commit whose message summarizes the evidence, then push `main`.
10. If rejected or inconclusive, do not merge the code. Copy or cherry-pick only the final dossier and index status into `main` as a registry-only commit, then push `main`.
11. Leave rejected and inconclusive branches available on `origin`.

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

## Publishing Results

Every completed hypothesis has two durable locations:

1. The hypothesis branch on `origin`, containing the exact tested code and the full dossier.
2. The `main` branch meta registry, containing the central index entry and final dossier text.

The publishing rule depends on the decision:

- Confirmed: merge the hypothesis branch into `main`; push the branch and `main`.
- Rejected: push the hypothesis branch; do not merge its code; update only `artifacts/meta/hypothesis-index.jsonl` and the hypothesis dossier on `main`; push `main`.
- Inconclusive: push the hypothesis branch; do not merge its code; update only the index and dossier on `main`; push `main`.
- Superseded: push the branch if it contains unique work; update the index/dossier on `main` with the superseding hypothesis id; push `main`.

Do not leave a completed hypothesis only in a local branch. If the branch is not pushed, future meta-agents cannot inspect the tested code. If `main` is not updated, future meta-agents cannot discover the result from the central registry.

## Hypothesis Artifacts

Hypotheses have two artifact levels:

```text
artifacts/meta/hypothesis-index.jsonl
artifacts/meta/hypotheses/<hypothesis-id>-<slug>.md
```

The index is compact JSONL. It exists for fast scanning and status lookup. The dossier is the full lifecycle document and should hold the long text.

Every hypothesis must have a stable id before code changes begin. Use `H0001`, `H0002`, and so on. The branch slug should match the dossier slug when practical:

```text
hyp/H0002-structured-edit-tool
artifacts/meta/hypotheses/H0002-structured-edit-tool.md
```

Index record shape:

```json
{
  "hypothesis_id": "H0002",
  "title": "Structured edit tool reduces no_patch failures",
  "status": "proposed | running | confirmed | rejected | inconclusive | superseded | baseline",
  "branch": "hyp/H0002-structured-edit-tool",
  "dossier": "artifacts/meta/hypotheses/H0002-structured-edit-tool.md",
  "created_at": "YYYY-MM-DD",
  "updated_at": "YYYY-MM-DD"
}
```

The index should not contain long hypotheses, detailed metrics, or findings. Put those in the dossier.

## Hypothesis Dossier Template

Create the dossier before changing code.

```markdown
# H0002 Structured Edit Tool Reduces No-Patch Failures

Status: proposed

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

## Proposed Change

Smallest code/doc surface to change. Include non-goals.

## Test Plan

- Validation commands:
- Benchmark task ids:
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

One of: merge to main, keep unmerged, rerun, expand task set, superseded by Hxxxx.

## Evidence Links

- Candidate run:
- Candidate trace:
- Commit:
```

The proposal sections can be long. The result sections are filled after the run. This separation is intentional: the meta-agent should first make a falsifiable plan, then execute it, then write the outcome.

Evidence paths should point to files such as `artifacts/runs/<run_id>/trace.jsonl`. Do not copy full traces into the dossier.

## First Commands

From the repo root:

```bash
uv sync
set -a
source .env
set +a
uv run evolve2 model-check
```

The OpenRouter key must come from local `.env`. Do not print the key, commit it, or copy it into hypothesis dossiers. `.env` is git-ignored.

Run one benchmark task:

```bash
uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 100 --evaluation-timeout 1800
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

Gating metric:

- `patch_published`: the run produced a non-empty tracked source diff that was submitted to SWE-bench evaluation. A candidate that cannot publish a patch is not mergeable as an agent improvement, even if it shows diagnostic progress such as fewer invalid actions or better localization.

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

A candidate is Pareto-dominant when it has equal or better `patch_published`, equal or better `resolved`, and improves at least one secondary metric without materially worsening the rest. Patch publication dominates diagnostic progress: if one run publishes a patch and the other does not, the patch-publishing run is the better harness candidate unless the patch path is clearly invalid or infrastructurally broken.

Diagnostic improvements belong in the dossier but are not merge criteria by themselves. Examples include lower invalid action count, more source reads, earlier shell execution, better natural-language localization, or a cleaner failure explanation. These can justify another hypothesis or a larger comparison, but they do not justify merging code to `main` unless they lead to patch publication, solve-rate improvement, or a confirmed infrastructure fix.

Wall time and token counts are required metrics, but they are noisy. Do not declare a time or token efficiency improvement from one run alone. For efficiency claims, use at least two comparable runs per side or a fixed multi-task comparison set. Time and token metrics are meaningful merge evidence only for comparable terminal states, especially when both baseline and candidate publish patches. If a run stops before publishing a patch, or stops because the iteration cap fired, time and tokens are diagnostic only.

A candidate is not automatically better if it only adds complexity, cost, or wall time without changing patch publication, failure class, or solve rate.

When tradeoffs are unclear, keep both candidates and run a larger fixed task set. Do not declare a global improvement from one task unless the failure mode is purely infrastructural, such as action parsing or trace completeness.

## Benchmark Run Profile

Use this stable comparison profile unless the hypothesis explicitly changes one of these parameters:

```text
model: google/gemma-4-26b-a4b-it
temperature: 0
agent_max_tokens: unset
max_iterations: 100
evaluation_timeout: 1800
```

`max_iterations` is an emergency guardrail for clearly broken loops, not a short work budget. A cap such as 4, 8, 16, or 32 is acceptable for smoke checks and debugging only; it is not a decision run for merge or rejection. If a candidate reaches the cap before publishing a patch, increase the cap or classify the run as inconclusive unless the trace proves repeated non-progress behavior.

`agent_max_tokens` changes agent behavior because it controls how much reasoning and action text the model can emit per call. Leave it unset for normal decision runs. Set it only when the hypothesis is specifically about completion budget, and then keep it fixed across baseline and candidate comparisons.

## How To Evolve The Agent

Use small experiments:

1. Start on `main` and create a hypothesis branch.
2. Select one failure mode from the latest trace.
3. Generate three candidate hypotheses before editing code.
4. Score the candidates by effort and expected result.
5. Choose the best effort/result tradeoff and write the dossier.
6. Change the smallest relevant surface.
7. Run the same task again.
8. Compare metrics against the parent run.
9. Fill the result sections in the hypothesis dossier.
10. Update `artifacts/meta/hypothesis-index.jsonl`.
11. Commit the branch with the complete hypothesis evidence.
12. Push the hypothesis branch.
13. Publish the result back to `main`:
    - confirmed: merge code and dossier;
    - rejected or inconclusive: registry-only update with dossier and index, no code merge.

Good experiment examples:

- Hypothesis: "If tool-call shaped outputs are accepted, invalid action count drops and the agent reaches shell execution earlier."
- Hypothesis: "If the finalization prompt requires a tracked source diff before finish, empty patch rate drops."
- Hypothesis: "If read_file results are summarized after 400 lines, token usage drops without worsening localization."

Bad experiment examples:

- "Make the agent smarter."
- "Rewrite the whole harness."
- "Add many tools and see what happens."

## Generating Candidate Hypotheses

Before choosing a branch hypothesis, generate exactly three candidates. Each candidate should be specific enough to test but not yet implemented.

Inputs to candidate generation:

- latest comparable `trace.jsonl` and `result.json`;
- current hypothesis dossiers, especially rejected and inconclusive ones;
- `docs/references/research/agent-evolution-literature.md`;
- relevant LangChain/LangGraph curated docs under `docs/references/langchain/curated/`;
- if internet is available and the idea is unclear, search for high-quality GitHub examples of similar LangChain, LangGraph, SWE-agent, or SWE-bench harness patterns for inspiration. Prefer examples from maintained repositories, official examples, or well-documented benchmark agents. Record only the link and the mechanism; do not copy large code.

Score each candidate with T-shirt sizes:

- Effort: `S`, `M`, `L`, or `XL`.
- Expected result: `S`, `M`, `L`, or `XL`.
- Confidence: `low`, `medium`, or `high`.

Use this table in the dossier before the final hypothesis:

```markdown
## Candidate Hypotheses Considered

| Candidate | Mechanism | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- |
| A | ... | trace + literature/GitHub refs | S | M | medium | chosen because ... |
| B | ... | ... | M | L | low | rejected because ... |
| C | ... | ... | L | L | medium | rejected because ... |
```

Selection rule:

- Prefer the candidate with the best expected-result-to-effort ratio.
- Prefer `S` or `M` effort unless a larger hypothesis is clearly justified by repeated failures.
- Prefer hypotheses with direct trace evidence over abstract literature appeal.
- Literature and GitHub examples should inspire mechanisms, not override local trace evidence.
- Do not choose a hypothesis that mainly repeats a rejected dossier unless it explains what changed.

Allowed change surfaces:

- `src/evolve2_agent_bench/agent/base.py`: loop, prompt, parsing, action protocol.
- `src/evolve2_agent_bench/agent/actions.py`: action schema.
- `src/evolve2_agent_bench/agent/tools.py`: tool behavior and observations.
- `src/evolve2_agent_bench/bench/swebench_runner.py`: benchmark orchestration and artifact writing.
- this manual and hypothesis artifacts under `artifacts/meta/`.

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

Do not create a branch from a paper idea until there is trace evidence that the idea targets an observed failure. If internet is available, the meta-agent may also search GitHub for implementation examples after the trace/literature mapping is clear.

## Minimum Meta-Agent Loop

For every work cycle:

1. `git status --short --branch`
2. Ensure the starting point is `main` unless continuing a documented hypothesis branch.
3. Read this manual, latest hypothesis dossiers, and latest comparable `result.json`.
4. Summarize the latest trace with `scripts/summarize_trace.py`.
5. If generating a new hypothesis family, read `docs/references/research/agent-evolution-literature.md`.
6. If the hypothesis touches LangChain or LangGraph behavior, read the relevant local files under `docs/references/langchain/curated/`.
7. Generate three candidate hypotheses with effort/result/confidence scores.
8. Choose the best effort/result tradeoff and create `hyp/HXXXX-<slug>`.
9. Edit code or docs.
10. Run `uv run python -m compileall -q src scripts`.
11. Load `.env` and run the fixed comparison task with the stable benchmark profile.
12. Fill the result section in the dossier and update the hypothesis index status.
13. Commit the branch with exhaustive evidence in the commit message.
14. Push the hypothesis branch to `origin`.
15. Return to `main` and publish the central registry result:
    - for confirmed hypotheses, merge the branch and push `main`;
    - for rejected or inconclusive hypotheses, bring over only `artifacts/meta/hypothesis-index.jsonl` and the relevant dossier, commit, and push `main`.
16. Report the delta: branch, branch push status, main registry commit, baseline run, candidate run, metric changes, Pareto assessment, and merge decision.

If a run fails before writing `trace.jsonl`, fix observability before optimizing agent behavior.

## Minimal Prompt Contract For Subagents

A subagent should be able to complete a cycle from this prompt alone:

```text
Run one meta-optimization cycle using docs/META_OPTIMIZATION.md.
```

That means the subagent must discover and execute the full workflow from this file:

- read the manual and current hypothesis artifacts;
- inspect baseline traces;
- generate and score three candidate hypotheses;
- create the next `HXXXX` id;
- create and push a hypothesis branch;
- create and maintain the dossier;
- run validation and benchmark comparison when credentials are available;
- record result metrics and decision;
- publish the branch to `origin`;
- update `main` central registry and push `main`;
- avoid merging rejected or inconclusive code into `main`.

Credentials should be loaded from `.env`. If credentials or runtime dependencies are missing, the subagent must still push the hypothesis branch if code was changed, mark the hypothesis `inconclusive`, publish the registry-only result to `main`, and document the blocker in the dossier.
