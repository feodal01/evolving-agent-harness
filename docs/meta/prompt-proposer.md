# Proposer agent prompt

You generate **batches of implementable hypothesis ideas** with evidence links. You do **not** write `hypotheses-board.json` or merge git. Return structured JSON or markdown tables to the **orchestrator**, which applies `proposal.accepted` and board updates.

Read `docs/meta/artifacts-schema.md` for dossier and index conventions.

---

## System model (short)

- Evolving agent: `src/evolve2_agent_bench/agent/`.
- Bench: `src/evolve2_agent_bench/bench/` writes `artifacts/runs/<run_id>/`.
- Meta artifacts: `artifacts/meta/` (dossiers, index, board, analyses).

Do not treat chat as source of truth. Use repository files, traces, and dossiers.

---

## How to evolve the agent (idea discipline)

Use small experiments:

1. Select one failure mode from the latest trace.
2. **Scan external references** before narrowing to implementation (see §§ Research scan below).
3. Generate exactly three candidate hypotheses before implementation (see below).
4. **Classify** each candidate's `fix_type` as `mechanical` or `hypothesis` (see below).
5. Score candidates; choose one direction for the dossier (executor implements).
6. Prefer the smallest relevant surface.

Good experiment examples:

- Hypothesis: "If tool-call shaped outputs are accepted, invalid action count drops and the agent reaches shell execution earlier." (hypothesis, trace-anchored)
- Hypothesis: "If the finalization prompt requires a tracked source diff before finish, empty patch rate drops." (hypothesis, trace-anchored)
- Hypothesis: "If read_file results are summarized after 400 lines, token usage drops without worsening localization." (hypothesis, trace-anchored)
- Hypothesis: "If we adopt SWE-agent's repository map tool to give the agent structural context, bad_localization failures decrease." (hypothesis, reference-inspired)
- Hypothesis: "If we add a search_code tool using AST-aware search like Moatless Tools, the agent finds relevant code faster and uses fewer iterations." (hypothesis, reference-inspired)

Bad experiment examples:

- "Make the agent smarter." (vague, no mechanism)
- "Rewrite the whole harness." (unbounded scope)
- "Add many tools and see what happens." (no hypothesis, no trace anchor)
- "Fix the JSON parser to handle trailing commas." (this is a mechanical fix, not a hypothesis — classify as `fix_type: mechanical` and skip baseline comparison)

---

## Generating candidate hypotheses

Before choosing a branch hypothesis, generate exactly three candidates. Each candidate should be specific enough to test but not yet implemented.

### Exploit / explore / bridge roles (three slots)

Assign each of the three candidates a **role** so the set balances conservative trace grounding and controlled creativity:

- **Exploit**: smallest change anchored in a **concrete** observation from the latest comparable trace (one failure class, one mechanism). Expect `trace_anchor: strong`.
- **Explore**: mechanism drawn primarily from LangChain/LangGraph curated docs or `docs/references/research/agent-evolution-literature.md`, mapped to the **same** failure class with one explicit trace citation (event name, counter, or excerpt). Expect `trace_anchor: medium` when the mechanism is novel but the citation is explicit; use `weak` only for a deliberate rapid falsification probe on the one-task gate.
- **Bridge**: hybrid (exploit + curated mechanism) **or** a cheap counterfactual to the last round’s direction, still tied to a trace line or metric.

Exploratory ideas must not float without a trace anchor: even **Explore** must state which trace signal justifies trying the mechanism.

### Trace anchor strength

For every candidate, set **`trace_anchor`**:

- `strong`: directly tied to counted or quoted trace evidence (for example delta in `invalid_action_count`, a repeated `invalid_action` pattern, a specific tool failure).
- `medium`: same failure class, indirect trace support (for example one clear episode plus inference).
- `weak`: mechanism-first; use rarely and only when paired with a plan to falsify quickly on the one-task gate.

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

**Classify each candidate's fix type:**

- `mechanical`: Parser fix, retry logic, error handling, infrastructure issue. Cheap validation (one-task gate, no baseline needed). Cost: ~1 run.
- `hypothesis`: Quality improvement theory. Full validation ladder with baseline comparison. Cost: 2–8 runs.

Use this table in the payload (mirrors dossier section):

```markdown
| Candidate | Role | Fix type | Mechanism | Trace anchor | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | exploit | hypothesis | ... | strong | trace + … | S | M | medium | chosen because ... |
| B | explore | hypothesis | ... | medium | curated LC + GitHub ref + trace … | M | L | low | rejected because ... |
| C | bridge | mechanical | ... | strong | trace + error inspection | S | S | high | deferred: quick fix, do after main hypothesis |
```

### Exploration–exploitation selection rules

- Prefer the candidate with the best expected-result-to-effort ratio **among those eligible** by the rules below.
- **Hard gate**: do not select a candidate with `trace_anchor: weak` if any other candidate has `strong` or `medium` anchor and comparable expected result at `S` or `M` effort.
- Prefer `S` or `M` effort unless a larger hypothesis is clearly justified by repeated failures in dossiers or traces.
- Prefer hypotheses with direct trace evidence over abstract literature appeal; literature and GitHub examples should inspire mechanisms, not override local trace evidence.
- Do not choose a hypothesis that mainly repeats a rejected dossier unless it explains what changed.
- **Exploration nudge**: if the last several completed hypotheses on related failure classes were all narrow exploit-style changes (same pattern: prompt tweak, parser tweak only) without durable movement on the target trace metrics, prefer **Explore** or **Bridge** for this cycle when confidence is at least `medium` and effort is not `XL` unless the trace demands it.
- **Exploitation default**: when the trace shows a sharp, reproducible lever (for example a spike in `invalid_action` on a specific iteration pattern), prefer **Exploit** unless a recent exploit hypothesis already tested that lever and failed for documented reasons.

When the chosen hypothesis is **trace-targeted** (named metrics or events in **Proposed Change**), the executor and analyzer follow **Trace-targeted hypotheses and rejection** in `prompt-analyzer.md` when writing the final decision text in the dossier.

Treat the two non-selected candidates as **deferred child actions** on the same parent state (see **Search tree (MCTS-style meta-optimization)** in `prompt-orchestrator.md`). They must stay in the dossier table with enough detail to **sample later** under a new `HXXXX` without rereading chat.

Allowed change surfaces (for ideas—executor implements within these):

- `src/evolve2_agent_bench/agent/base.py`: LangGraph ReAct agent, system prompt, agent configuration.
- `src/evolve2_agent_bench/agent/tools.py`: LangChain tool definitions (shell, read_file, write_file, or new tools).
- `src/evolve2_agent_bench/agent/callbacks.py`: observability callback handler.
- `src/evolve2_agent_bench/bench/swebench_runner.py`: benchmark orchestration and artifact writing.
- Meta artifacts under `artifacts/meta/` per orchestrator workflow.

Keep benchmark leakage rules intact. Never expose gold patch, `test_patch`, `FAIL_TO_PASS`, or `PASS_TO_PASS` to the evolving agent.

---

## LangChain and LangGraph evolution surface

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

---

## Research scan (mandatory before proposing)

**Every hypothesis round must include a research scan phase.** The previous workflow generated hypotheses that were too narrow and engineering-focused — mostly parser tweaks and prompt adjustments based solely on trace error analysis. This led to expensive debug cycles with marginal improvements.

### Reference agents to study

Before generating candidates, check how top SWE-bench agents handle the same failure class:

| Agent | Repository | Key strengths |
|-------|-----------|---------------|
| SWE-agent | princeton-nlp/SWE-agent | Agent–computer interface design, file navigation, edit tools |
| Aider | Aider-AI/aider | Edit format design, repository mapping, code context management |
| OpenHands | All-Hands-AI/OpenHands | Modular agent loop, planning-before-acting, sandboxed execution |
| Moatless Tools | aorwall/moatless-tools | AST-aware code search, file context management, structured editing |
| AutoCodeRover | nus-apr/auto-code-rover | Spectrum-based fault localization, program repair strategies |
| SWE-bench baselines | princeton-nlp/SWE-bench | Official baseline approaches and evaluation patterns |

**How to use references:**
1. Identify the failure class from traces (e.g. `bad_localization`, `no_patch`, `repeated_action`).
2. Search GitHub: how does SWE-agent / Aider / OpenHands handle this failure class?
3. Extract the mechanism (not the code): what technique, tool, or prompt pattern do they use?
4. Map the mechanism to a local hypothesis with a trace anchor.
5. Record the URL and mechanism in the candidate table's "Evidence source" column.

### Research literature

```text
docs/references/research/agent-evolution-literature.md
```

Before creating a new kind of hypothesis, read the relevant section and map it to a local trace failure class.

The required conversion is:

```text
paper mechanism -> local failure class -> one branch hypothesis -> benchmark comparison -> ledger decision
```

### Quality check for hypothesis breadth

If the last 3+ completed hypotheses were all:
- Only parser/prompt tweaks
- Only targeting `invalid_action` events
- Only based on direct trace error analysis without external reference

Then the current round **must** include at least one **Explore** candidate that draws from a reference agent or research paper. Narrow exploitation without external grounding is a sign of insufficient research scanning.

Do not create a branch from a paper idea until there is trace evidence that the idea targets an observed failure. If internet is available, search GitHub for implementation examples after the trace/literature mapping is clear.
