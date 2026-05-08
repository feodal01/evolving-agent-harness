# evolving-agent-harness

`evolving-agent-harness` is a Python project for evolving an agent harness on SWE-bench Verified using Pareto-driven experiments.

The core idea: keep the base coding agent intentionally simple and cheap to run, then let a meta-agent improve the harness around it through controlled hypotheses. Each hypothesis changes the agent or harness code, runs benchmark rollouts, compares metrics, and is merged only if it improves the Pareto frontier.

## Why This Exists

Agent performance is not only a model problem. The harness around the model - tools, context, memory, action protocol, tracing, validation, and recovery behavior - strongly shapes what the agent can do.

This project is a small laboratory for pushing harness engineering as far as possible with a small LLM. Small models make rollouts cheaper and faster, and they make harness improvements easier to see: if the agent gets better, the surrounding engineering likely mattered.

## Design Principles

1. Git is the experiment control system.
   `main` contains the mainstream agent. Every hypothesis gets its own `hyp/<date>-<slug>` branch. Failed branches are not deleted; they remain as evidence. Only Pareto-improving hypotheses are merged.

2. The central memory is explicit.
   `artifacts/meta/experiment-ledger.jsonl` records hypotheses, branches, run ids, metrics, findings, Pareto assessment, and decisions. The project should not rely on chat history.

3. Use LangChain instead of inventing an agent framework.
   The evolving agent is written on LangChain. The meta-agent improves it by editing ordinary Python code: prompts, tool schemas, parsing, memory, context handling, middleware, LangGraph control flow, and evaluation hooks.

4. Use SWE-bench as the pressure test.
   SWE-bench Verified gives real repository tasks, established evaluation tooling, and a large body of public literature. The meta-agent is expected to use relevant research, including arXiv papers, when generating hypothesis families.

5. Keep rollouts cheap.
   The default evaluated model is a small OpenRouter model: `google/gemma-4-26b-a4b-it`. This keeps iteration cost low and helps measure how far harness improvements can push a smaller model.

6. Markdown is the meta-agent interface.
   The meta-agent workflow, research frame, local references, and operating rules live in markdown files. This keeps the project easy to inspect, fork, and resume.

## Repository Map

- `src/evolve2_agent_bench/agent/`: evolving LangChain coding agent.
- `src/evolve2_agent_bench/bench/`: SWE-bench runner and evaluation orchestration.
- `src/evolve2_agent_bench/meta/`: helpers for experiment ledger updates.
- `docs/META_OPTIMIZATION.md`: self-contained operating manual for the meta-agent.
- `artifacts/meta/experiment-ledger.jsonl`: central hypothesis and result ledger.
- `docs/references/langchain/`: offline LangChain and LangGraph documentation, including curated Python references.
- `docs/references/research/agent-evolution-literature.md`: research frame for generating hypothesis families.
- `artifacts/runs/<run_id>/`: ignored local run traces and benchmark outputs.
- `artifacts/worktrees/<run_id>/`: ignored local task repositories.

## Setup

```bash
uv sync
export OPENROUTER_API_KEY=...
```

The default model is `google/gemma-4-26b-a4b-it` through OpenRouter.

## Smoke Check

```bash
uv run evolve2 model-check
```

## Run One SWE-bench Verified Task

```bash
uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 8
```

Each run writes a directory under `artifacts/runs/<run_id>/` containing:

- `trace.jsonl`: canonical unified timeline with task input, LLM messages, model responses, parsed actions, tool calls, tool outputs, errors, patch, prediction, and evaluation summary.
- `task.json`: public SWE-bench instance fields given to the agent. Gold patches and hidden evaluator fields are not written to run artifacts.
- `agent_events.jsonl`: high-level agent decisions.
- `llm_calls.jsonl`: model-specific slice of the unified trace.
- `shell_events.jsonl`: shell-specific slice of the unified trace.
- `patch.diff`: generated prediction patch.
- `prediction.jsonl`: SWE-bench prediction input.
- `evaluation_stdout.log` and `evaluation_stderr.log`: SWE-bench harness output.
- `result.json`: compact outcome summary.

Large traces stay in per-run JSONL files; the meta ledger stores references and metrics, not copied traces.

## Meta-Agent Workflow

Read [docs/META_OPTIMIZATION.md](docs/META_OPTIMIZATION.md) before changing the agent.

The intended loop:

1. Start from `main`.
2. Inspect the latest `result.json` and `trace.jsonl`.
3. Classify the failure mode.
4. Read relevant local references or papers if the hypothesis needs them.
5. Create `hyp/<date>-<slug>`.
6. Make one narrow code or prompt change.
7. Run the same comparison task set.
8. Append the result to `artifacts/meta/experiment-ledger.jsonl`.
9. Merge into `main` only if the hypothesis improves Pareto efficiency.

Pareto efficiency means the change improves at least one important metric without an unacceptable regression elsewhere. Primary metric is SWE-bench solve rate; secondary metrics include wall time, token usage, invalid actions, tool calls, patch size, and failure class.

## Offline References

The project includes local references so the meta-agent can work without internet access:

- LangChain/LangGraph docs: [docs/references/langchain/README.md](docs/references/langchain/README.md)
- Research frame: [docs/references/research/agent-evolution-literature.md](docs/references/research/agent-evolution-literature.md)

The research frame is intentionally not a backlog. It describes directions such as agent-computer interfaces, reflection, Pareto text evolution, bounded search, experience banks, skills, synthetic tasks, and evaluation robustness. A paper idea only becomes a branch after it maps to an observed trace failure.
