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

3. Use LangChain/LangGraph as the agent framework.
   The evolving agent is a LangGraph ReAct agent with native tool calling. The meta-agent improves it by editing ordinary Python code: prompts, tool definitions, callbacks, memory, context handling, and LangGraph control flow.

4. Use SWE-bench as the pressure test.
   SWE-bench Verified gives real repository tasks, established evaluation tooling, and a large body of public literature. The meta-agent is expected to use relevant research, reference agents, and LangChain/LangGraph patterns when generating hypothesis families.

5. Keep rollouts cheap.
   The default evaluated model is a small OpenRouter model: `google/gemma-4-26b-a4b-it`. This keeps iteration cost low and helps measure how far harness improvements can push a smaller model.

6. Markdown is the meta-agent interface.
   The meta-agent workflow, research frame, local references, and operating rules live in markdown files. This keeps the project easy to inspect, fork, and resume.

## Repository Map

- `src/evolve2_agent_bench/agent/`: evolving LangGraph ReAct coding agent.
- `src/evolve2_agent_bench/bench/`: SWE-bench runner and evaluation (offline only).
- `docs/meta/README.md`: entry point for meta-optimization prompts and artifact schemas.
- `docs/meta/prompt-unified.md`: single-agent meta-optimization operating manual.
- `artifacts/meta/hypotheses-board.json`: operational hypothesis board.
- `artifacts/meta/hypothesis-index.jsonl`: compact index of hypothesis dossiers and statuses.
- `artifacts/meta/hypotheses/`: full hypothesis dossiers, from proposal through result.
- `docs/references/langchain/`: offline LangChain and LangGraph documentation.
- `docs/references/research/agent-evolution-literature.md`: research frame for generating hypothesis families.
- `artifacts/runs/<run_id>/`: local run traces and benchmark outputs (git-ignored).
- `artifacts/mlflow.db`: default local MLflow tracking store (git-ignored).

## Setup

```bash
uv sync
set -a
source .env
set +a
```

The OpenRouter key is expected in local `.env` as `OPENROUTER_API_KEY=...`. `.env` is ignored by git. The default model is `google/gemma-4-26b-a4b-it` through OpenRouter.

### SWE-bench Verified Dataset (offline, required)

The dataset must be materialized locally before running tasks. No HuggingFace Hub fallback.

```bash
uv run evolve2 materialize-dataset
uv run evolve2 dataset-status
```

Default location: `datasets/SWE-bench_Verified`. Override with `EVOLVE2_SWEBENCH_DATASET_ROOT`.

## Smoke Check

```bash
uv run evolve2 model-check
```

## Run One SWE-bench Verified Task

```bash
uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 100 --evaluation-timeout 1800
```

MLflow tracing is **auto-enabled** for every run. Disable with `--no-mlflow` or `EVOLVE2_MLFLOW_TRACING=0`.

Each run writes a directory under `artifacts/runs/<run_id>/` containing:

- `trace.jsonl`: local unified timeline export mirrored into MLflow.
- `task.json`: public SWE-bench instance fields given to the agent.
- `agent_events.jsonl`: high-level agent decisions.
- `llm_calls.jsonl`: model-specific slice of the unified trace.
- `shell_events.jsonl`: shell-specific slice of the unified trace.
- `patch.diff`: generated prediction patch.
- `prediction.jsonl`: SWE-bench prediction input.
- `evaluation_stdout.log` and `evaluation_stderr.log`: SWE-bench harness output.
- `result.json`: compact outcome summary.

Inspect a trace:

```bash
uv run evolve2 trace-view artifacts/runs/<run_id> --stream llm --stream agent
```

### MLflow UI

View full span hierarchies for every LLM call, tool invocation, and evaluation:

```bash
uv run evolve2 mlflow-ui
# prints the command to launch MLflow UI
# then open http://localhost:5050
```

MLflow is the primary observability surface. Each benchmark run creates an MLflow run with nested spans showing the benchmark rollout, agent session, individual LLM iterations, tool calls, evaluation, and mirrored `trace.jsonl` events.

## Meta-Agent Workflow

A **single unified agent** handles all meta-optimization phases. Start at [docs/meta/README.md](docs/meta/README.md), use [docs/meta/prompt-unified.md](docs/meta/prompt-unified.md) as the `/goal` prompt.

The meta-optimization loop:

1. **Round setup**: Checkout main, verify env, read hypothesis board.
2. **Research scan**: Review reference agents (SWE-agent, Aider, OpenHands, Moatless), LangChain/LangGraph docs, research literature.
3. **Hypothesis generation**: Generate three candidates (exploit/explore/bridge), classify as `mechanical` or `hypothesis`, select one.
4. **Execution**: Branch, implement, validate according to fix type.
5. **Analysis**: Pareto comparison starting from MLflow span analysis, with JSONL exports for scripted summaries and durable evidence paths.
6. **Decision**: Merge / reject / keep, publish to registry.

### Fix Types

- **Mechanical** (`fix_type: mechanical`): Parser bugs, retry logic, infrastructure. One-task gate only, no baseline comparison. Cost: ~1 run.
- **Hypothesis** (`fix_type: hypothesis`): Quality improvements. Full validation ladder with baseline comparison. Cost: 2-8 runs.

This distinction prevents burning budget on expensive baseline comparisons for trivial fixes.

## Offline References

The project includes local references so the meta-agent can work without internet access:

- LangChain/LangGraph docs: [docs/references/langchain/README.md](docs/references/langchain/README.md)
- Research frame: [docs/references/research/agent-evolution-literature.md](docs/references/research/agent-evolution-literature.md)

The research frame is intentionally not a backlog. It describes directions such as agent-computer interfaces, reflection, Pareto text evolution, bounded search, experience banks, skills, synthetic tasks, and evaluation robustness. A paper idea only becomes a branch after it maps to an observed trace failure.
