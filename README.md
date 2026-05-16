# evolving-agent-harness

`evolving-agent-harness` is a Python project for evolving an agent harness on SWE-bench Verified using Pareto-driven experiments.

The core idea: keep the base coding agent intentionally simple and cheap to run, then let a meta-agent improve the harness around it through controlled hypotheses. Each hypothesis changes the agent or harness code, runs benchmark rollouts, compares metrics, and is merged only if it improves the Pareto frontier.

## Why This Exists

Agent performance is not only a model problem. The harness around the model - tools, context, memory, action protocol, tracing, validation, and recovery behavior - strongly shapes what the agent can do.

This project is a small laboratory for pushing harness engineering as far as possible with a small LLM. Small models make rollouts cheaper and faster, and they make harness improvements easier to see: if the agent gets better, the surrounding engineering likely mattered.

## Design Principles

1. Git is the experiment control system.
   `main` contains the mainstream agent. Every hypothesis gets its own `hyp/HXXXX-<slug>` branch. Failed branches are not deleted; they remain as evidence. Only Pareto-improving hypotheses are merged.

2. The central memory is explicit.
   `artifacts/meta/hypothesis-index.jsonl` gives a compact status index, while `artifacts/meta/hypotheses/` stores full hypothesis dossiers from proposal through result. The project should not rely on chat history.

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
- `src/evolve2_agent_bench/meta/`: helpers for meta artifacts.
- `docs/meta/README.md`: entry point for meta-optimization role prompts and artifact schemas.
- `artifacts/meta/hypotheses-board.json`: operational hypothesis board (orchestrator-owned; see `docs/meta/artifacts-schema.md`).
- `artifacts/meta/hypothesis-index.jsonl`: compact index of hypothesis dossiers and statuses.
- `artifacts/meta/hypotheses/`: full hypothesis dossiers, from proposal through result.
- `docs/references/langchain/`: offline LangChain and LangGraph documentation, including curated Python references.
- `docs/references/research/agent-evolution-literature.md`: research frame for generating hypothesis families.
- `artifacts/runs/<run_id>/`: ignored local run traces and benchmark outputs.
- `artifacts/worktrees/<run_id>/`: ignored local task repositories.

## Setup

```bash
uv sync
set -a
source .env
set +a
```

The OpenRouter key is expected in local `.env` as `OPENROUTER_API_KEY=...`. `.env` is ignored by git. The default model is `google/gemma-4-26b-a4b-it` through OpenRouter.

## Smoke Check

```bash
uv run evolve2 model-check
```

## Run One SWE-bench Verified Task

```bash
uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 100 --evaluation-timeout 1800
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

Large traces stay in per-run JSONL files; hypothesis dossiers store references and metrics, not copied traces.

## Meta-Agent Workflow

Start at [docs/meta/README.md](docs/meta/README.md). For a single hypothesis branch, follow [docs/meta/prompt-executor.md](docs/meta/prompt-executor.md) and [docs/meta/artifacts-schema.md](docs/meta/artifacts-schema.md).

For a top-level `/goal` that coordinates multiple hypothesis workers, use [docs/meta/prompt-orchestrator.md](docs/meta/prompt-orchestrator.md). That prompt is only for the orchestrator, not for a single hypothesis-testing subagent.

The single-hypothesis worker loop:

1. Start from `main`.
2. Inspect the latest `result.json` and `trace.jsonl`.
3. Classify the failure mode.
4. Read relevant local references, papers, and useful GitHub examples if the hypothesis needs them.
5. Generate three candidate hypotheses with effort/result/confidence scores.
6. Choose the best effort/result tradeoff.
7. Create `hyp/HXXXX-<slug>`.
8. Make one narrow code or prompt change.
9. Run the one-task gate first.
10. If it passes, run the fixed three-task promotion gate.
11. If the three-task gate passes, ask the user before any full SWE-bench Verified run.
12. Fill the result section in the hypothesis dossier and update `artifacts/meta/hypothesis-index.jsonl`.
13. Push the hypothesis branch.
14. Merge into `main` only if the hypothesis improves Pareto efficiency. For rejected or inconclusive hypotheses, keep the branch and publish only the central hypothesis artifacts back to `main`.

Pareto efficiency means the change improves at least one important metric without an unacceptable regression elsewhere. Patch publication is a gating metric, the primary metric is SWE-bench solve rate, and secondary metrics include wall time, token usage, invalid actions, tool calls, patch size, and failure class.

Wall time and token usage are required but noisy. They are merge evidence only for comparable terminal runs, especially when both baseline and candidate publish a patch. If a run does not publish a patch or stops on the iteration cap, time and tokens are diagnostic rather than proof of better efficiency. Use the stable benchmark profile from `docs/meta/prompt-executor.md`; low iteration caps such as 4, 8, 16, or 32 are smoke checks, not decision runs. Do not set an agent completion-token cap unless the hypothesis is specifically about response budget.

Validation scales in stages: first `astropy__astropy-12907`, then the fixed three-task set `astropy__astropy-12907`, `django__django-11099`, and `sympy__sympy-20590` if the first gate passes. A full benchmark run is only a next-step recommendation after the three-task gate and requires explicit user approval.

## Offline References

The project includes local references so the meta-agent can work without internet access:

- LangChain/LangGraph docs: [docs/references/langchain/README.md](docs/references/langchain/README.md)
- Research frame: [docs/references/research/agent-evolution-literature.md](docs/references/research/agent-evolution-literature.md)

The research frame is intentionally not a backlog. It describes directions such as agent-computer interfaces, reflection, Pareto text evolution, bounded search, experience banks, skills, synthetic tasks, and evaluation robustness. A paper idea only becomes a branch after it maps to an observed trace failure.
