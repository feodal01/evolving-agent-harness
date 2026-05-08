# Agent Evolution Literature Frame

This note gives the meta-LLM a research frame for generating future hypotheses. It is not a hypothesis backlog. Do not implement an idea just because it appears here. Convert literature ideas into one narrow branch hypothesis only after inspecting a local trace and identifying a failure class.

## Source Set

Core sources to start from:

- SWE-bench: Can Language Models Resolve Real-World GitHub Issues?
  https://arxiv.org/abs/2310.06770
- SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering
  https://arxiv.org/abs/2405.15793
- Reflexion: Language Agents with Verbal Reinforcement Learning
  https://arxiv.org/abs/2303.11366
- SWE-Search: Enhancing Software Agents with Monte Carlo Tree Search and Iterative Refinement
  https://arxiv.org/abs/2410.20285
- GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning
  https://arxiv.org/abs/2507.19457
- SWE-rebench: An Automated Pipeline for Task Collection and Decontaminated Evaluation of Software Engineering Agents
  https://arxiv.org/abs/2505.20411
- SWE-Dev: Building Software Engineering Agents with Training and Inference Scaling
  https://arxiv.org/abs/2506.07636
- SWE-Exp: Experience-Driven Software Issue Resolution
  https://arxiv.org/abs/2507.23361
- Saving SWE-Bench: A Benchmark Mutation Approach for Realistic Agent Evaluation
  https://arxiv.org/abs/2510.08996
- SWE-Skills-Bench: Do Agent Skills Actually Help in Real-World Software Engineering?
  https://arxiv.org/abs/2603.15401
- Toward Training Superintelligent Software Agents through Self-Play SWE-RL
  https://arxiv.org/abs/2512.18552

Use web search for newer papers, but this source set is enough to generate first-order research directions offline.

## How To Read Papers For Hypothesis Generation

Extract mechanisms, not claims.

For each paper, write:

- What control surface changed? Examples: interface, tool schema, memory, search, evaluator, prompt, trajectory reflection, task distribution.
- What feedback signal was used? Examples: unit tests, benchmark pass/fail, execution logs, natural-language reflection, trajectory comparisons.
- What artifact was retained? Examples: prompt mutation, tool trace, experience memory, skill, branch, generated test, failed trajectory.
- What metric improved? Examples: solve rate, pass@1, invalid actions, search depth, token cost, wall time, reproducibility.
- What could fail in this project? Examples: token overhead, stale memories, overfitting one task, benchmark leakage, too much branching.

Then map the mechanism to a local failure class in `trace.jsonl`. If there is no local failure class match, do not create a branch.

## Research Directions

### Agent-Computer Interface

SWE-agent argues that agents need interfaces designed for their own strengths and weaknesses, not only raw shell access. For this project, interface means the tool set, tool schemas, observations, edit APIs, and validation affordances exposed to the evolving agent.

Failure classes to inspect:

- `invalid_action_protocol`
- `repeated_action`
- `bad_localization`
- `no_patch`

Possible direction, not a hypothesis:

- Make repository navigation and editing more structured than free-form shell commands.
- Separate inspect, edit, test, and finish actions so traces reveal where the loop fails.
- Design tool observations that are compact, stable, and difficult for the model to misread.

### Trace Reflection And Verbal Learning

Reflexion-style systems use task feedback and natural-language reflections as memory for later attempts. GEPA-style systems use trace-level reflection to mutate textual components and keep Pareto-efficient variants.

Failure classes to inspect:

- `bad_patch`
- `repeated_action`
- `local_test_failure`
- `invalid_action_protocol`

Possible direction, not a hypothesis:

- Generate compact post-run reflections from `trace.jsonl`.
- Store lessons in the central ledger or a dedicated experience bank.
- Separate evidence from advice: evidence points to trace events; advice states a reusable rule.
- Treat reflections as candidate textual parameters that must be validated on branches.

### Pareto-Efficient Text Evolution

GEPA motivates evolving textual components with natural-language reflection and Pareto selection rather than reducing every run to one scalar reward. In this repo, textual components include system prompt, action protocol, tool descriptions, memory instructions, finalization rules, and trace summarization prompts.

Failure classes to inspect:

- any repeated failure class across comparable runs.

Possible direction, not a hypothesis:

- Maintain multiple prompt or protocol variants on separate branches.
- Keep variants that improve a failure class, solve rate, or cost without unacceptable regressions.
- Use `experiment-ledger.jsonl` as the Pareto archive.

### Search And Deliberation

SWE-Search uses search and iterative refinement ideas for repository-level tasks. The general lesson is not "add MCTS immediately"; it is that single greedy trajectories can get stuck, and agent branches can be evaluated before committing to a patch.

Failure classes to inspect:

- `bad_localization`
- `bad_patch`
- `local_test_failure`

Possible direction, not a hypothesis:

- Explore multiple localization candidates before editing.
- Generate alternative patch plans and select with deterministic evidence.
- Use tests or static checks as rollout feedback when cheap.
- Keep search depth bounded and measure token/wall-time cost explicitly.

### Experience Banks

SWE-Exp frames software agents as systems that should accumulate repair experience instead of treating every issue as isolated. Experience can include successful fix patterns and failed trajectory patterns.

Failure classes to inspect:

- repeated `bad_localization` on similar repositories;
- repeated `no_patch` or `repeated_action` loop failures;
- repeated test-failure patterns.

Possible direction, not a hypothesis:

- Store concise experience records keyed by repository, package, failure class, and changed files.
- Retrieve only relevant memories into context.
- Track whether retrieved memories were used and whether they helped.
- Delete or demote memories that cause regressions.

### Skills And Procedural Knowledge

SWE-Skills-Bench warns that injected skills often have limited or negative utility unless they are tightly matched to the task and context. Skills should be treated as expensive interventions requiring paired evaluation.

Failure classes to inspect:

- `bad_localization`
- `bad_patch`
- `local_test_failure`

Possible direction, not a hypothesis:

- Create skills only for recurring, well-scoped failure modes.
- Measure token overhead and solve-rate delta with and without the skill.
- Version skills and retire them when they become stale or conflict with the repository.

### Synthetic Tasks And Self-Play

SWE-RL and related work suggest agents can learn from generated repair tasks or self-play environments. For this repo, this should not mean training model weights. It can mean building cheaper local practice tasks that exercise the harness before spending SWE-bench evaluations.

Failure classes to inspect:

- infrastructure failures;
- action protocol failures;
- edit/test/finalize loop failures.

Possible direction, not a hypothesis:

- Add tiny synthetic repo tasks to test agent loop mechanics.
- Use local tasks to validate parser, tool, memory, and trace changes before SWE-bench.
- Keep synthetic tasks separate from benchmark claims.

### Evaluation Robustness

SWE-bench, SWE-rebench, and benchmark mutation papers emphasize that benchmark design can shape what agents learn. For this repo, evaluation robustness means avoiding leakage, keeping task sets fixed for comparisons, and testing whether improvements survive prompt/query variation.

Failure classes to inspect:

- `evaluation_error`
- suspicious solve-rate improvements without trace evidence;
- high variance across repeated runs.

Possible direction, not a hypothesis:

- Use fixed comparison task sets for branch decisions.
- Repeat runs when model stochasticity or provider instability may affect conclusions.
- Record exact model, branch, commit, task ids, run ids, and trace paths.
- Treat benchmark mutation or fresh tasks as a later validation layer, not as a replacement for SWE-bench Verified.

## From Direction To Branch Hypothesis

Use this template before creating a branch:

```text
Observed failure:
Trace evidence:
Research direction:
Mechanism to test:
Smallest code/doc surface:
Expected metric movement:
Expected regression risk:
Comparison task set:
Stop condition:
```

Good branch hypotheses are narrow:

- one mechanism;
- one failure class;
- one expected metric movement;
- one comparison task set;
- one decision after the run.

Bad branch hypotheses combine many mechanisms, such as memory plus new tools plus search plus prompt rewrite. Split those into separate branches.

## Research Hygiene

- Prefer primary sources: arXiv, official paper pages, or project docs.
- Record paper links in this file or in a new focused literature note before relying on them.
- Keep summaries mechanism-oriented and short.
- Do not copy paper text into prompts or artifacts.
- Do not expose benchmark gold patches or hidden evaluator fields.
- If an idea requires many rollouts, first test whether trace summaries and local synthetic tasks can reduce cost.
