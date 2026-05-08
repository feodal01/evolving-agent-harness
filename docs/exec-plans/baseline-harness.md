# Baseline Harness Plan

## Purpose

Create a Python project that runs an observable LangChain coding agent on one SWE-bench Verified task and records artifacts that a meta-LLM can use to evolve the agent.

## Scope

- Verify OpenRouter access to `google/gemma-4-26b-a4b-it`.
- Implement the baseline agent, SWE-bench task preparation, patch generation, and local evaluation command.
- Record run traces and compact meta-experiment results.

## Validation

- `uv run evolve2 model-check`
- `uv run evolve2 run-task --instance-id astropy__astropy-12907 --max-iterations 8`
