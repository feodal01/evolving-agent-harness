# Proposer reference prompt

Detailed instructions for Phase 2 (hypothesis generation). Generate **batches of implementable hypothesis ideas** with evidence links, then select one for execution.

Dossier and index conventions: `docs/meta/artifacts-schema.md`.

---

## System model

System layout: see `prompt-unified.md` §System overview. Do not treat chat as source of truth — use repository files, traces, and dossiers.

---

## How to evolve the agent (idea discipline)

1. Select one failure mode from the latest trace.
2. **Scan external references** before narrowing to implementation (see §Research scan below).
3. Generate exactly three candidate hypotheses (see §Generating candidate hypotheses).
4. **Classify** each candidate's `fix_type` as `mechanical` or `hypothesis`.
5. Score candidates; choose one direction for the dossier (executor implements).
6. Prefer the smallest relevant surface.

Good experiments: trace-anchored hypotheses with clear mechanism and metric target (e.g. "If tool-call shaped outputs are accepted, invalid action count drops"), or reference-inspired hypotheses mapped to a local failure class (e.g. "If we adopt SWE-agent's repository map tool, bad_localization failures decrease").

Bad experiments: vague goals ("make the agent smarter"), unbounded scope ("rewrite the whole harness"), no trace anchor ("add many tools and see what happens"). Mechanical fixes (e.g. parser bug) should be classified as `fix_type: mechanical`, not hypothesis.

---

## Generating candidate hypotheses

Generate exactly three candidates, each specific enough to test but not yet implemented.

### Exploit / explore / bridge roles

- **Exploit**: smallest change anchored in a **concrete** trace observation (one failure class, one mechanism). `trace_anchor: strong`.
- **Explore**: mechanism from LangChain/LangGraph curated docs or research literature, mapped to the **same** failure class with one explicit trace citation. `trace_anchor: medium` (or `weak` only for rapid one-task falsification).
- **Bridge**: hybrid exploit+curated mechanism **or** cheap counterfactual to the last round's direction, tied to a trace line or metric.

### Trace anchor strength

- `strong`: directly tied to counted or quoted trace evidence.
- `medium`: same failure class, indirect trace support.
- `weak`: mechanism-first; use rarely, paired with rapid falsification plan.

Inputs: latest `trace.jsonl` and `result.json`; recent dossiers (especially rejected/rejected); `docs/references/research/agent-evolution-literature.md`; relevant LangChain/LangGraph curated docs; GitHub examples from maintained SWE-bench agent repos (record link + mechanism only).

Score each candidate:

- Effort: `S` / `M` / `L` / `XL`
- Expected result: `S` / `M` / `L` / `XL`
- Confidence: `low` / `medium` / `high`

**Fix type classification:**

- `mechanical`: **Infrastructure only** — parser bugs, retry logic, error handling paths, broken imports, missing files, typos in non-prompt code, configuration errors. The fix must be objectively correct with no judgment call. Does NOT change agent behavior — only fixes broken mechanics. One-task gate, no baseline. ~1 run.
- `hypothesis`: **Any change that affects agent behavior** — this includes ALL prompt changes, tool improvements, new tools, reminder text changes, system prompt edits, context additions, and any modification that could change what the agent does or how it responds. Also covers quality improvement theories. Full validation ladder with baseline. 2-8 runs.

**Explicitly NOT mechanical (must be classified as `hypothesis`):**
- Changes to prompt text, reminder messages, or system instructions
- Changes to tool descriptions or tool behavior
- Adding, removing, or modifying tools available to the agent
- Changes to intervention message content or timing thresholds
- Any modification where "correctness" is subjective or requires measuring agent behavior

Payload table (mirrors dossier section):

```markdown
| Candidate | Role | Fix type | Mechanism | Trace anchor | Evidence source | Effort | Expected result | Confidence | Why not / why chosen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | exploit | hypothesis | ... | strong | trace + ... | S | M | medium | chosen because ... |
| B | explore | hypothesis | ... | medium | curated LC + GitHub ref + trace ... | M | L | low | rejected because ... |
| C | bridge | mechanical | ... | strong | trace + error inspection | S | S | high | deferred: quick fix, do after main hypothesis |
```

### Exploration-exploitation selection rules

- Prefer best expected-result-to-effort ratio among eligible candidates.
- **Hard gate**: do not select `trace_anchor: weak` if another candidate has `strong`/`medium` anchor at `S`/`M` effort with comparable expected result.
- Prefer `S`/`M` effort unless repeated dossier/trace failures justify larger scope.
- Prefer direct trace evidence over abstract literature appeal.
- Do not repeat a rejected dossier's mechanism unless you explain what changed.
- **Exploration nudge**: if last several hypotheses were all narrow exploit-style without durable metric movement, prefer **Explore** or **Bridge** (confidence >= `medium`, effort != `XL`).
- **Exploitation default**: when trace shows a sharp reproducible lever, prefer **Exploit** unless a recent exploit already tested it and failed.

Trace-targeted hypotheses (named metrics in Proposed Change): executor and analyzer follow `prompt-analyzer.md` §Trace-targeted for the final decision.

Non-selected candidates become **deferred child actions** in the dossier table with enough detail to sample later under a new `HXXXX` without rereading chat.

Allowed change surfaces:

- `src/evolve2_agent_bench/agent/base.py`: agent, system prompt, configuration.
- `src/evolve2_agent_bench/agent/tools.py`: tool definitions.
- `src/evolve2_agent_bench/agent/callbacks.py`: observability callbacks.
- `src/evolve2_agent_bench/bench/swebench_runner.py`: benchmark orchestration.
- Meta artifacts under `artifacts/meta/`.

Never expose gold patch, `test_patch`, `FAIL_TO_PASS`, or `PASS_TO_PASS` to the evolving agent.

---

## LangChain and LangGraph evolution surface

Before proposing changes to agent loop, memory, tools, context, structured output, or graph control, read the relevant curated docs:

| Area | Curated doc |
|------|------------|
| Tool design | `curated/langchain-tools.md`, `curated/langchain-structured-output.md` |
| Context | `curated/langchain-context-engineering.md` |
| Middleware | `curated/langchain-middleware-built-in.md`, `curated/langchain-middleware-custom.md` |
| Memory | `curated/langchain-short-term-memory.md`, `curated/langchain-long-term-memory.md`, `curated/langgraph-add-memory.md` |
| Graph control | `curated/langgraph-overview.md`, `curated/langgraph-thinking.md`, `curated/langgraph-fault-tolerance.md` |
| Evaluation | `curated/langchain-agent-evals.md`, `curated/langchain-unit-testing.md` |

All under `docs/references/langchain/`. Raw docs: `llms.txt`, `llms-full.txt`, `langgraph-llms.txt`. Start with `docs/references/langchain/README.md`.

Each feature must be tied to a failure class, expected metric movement, and a branch-level hypothesis.

---

## Research scan (mandatory before proposing)

### Reference agents

| Agent | Repository | Key strengths |
|-------|-----------|---------------|
| SWE-agent | princeton-nlp/SWE-agent | Agent-computer interface, file navigation, edit tools |
| Aider | Aider-AI/aider | Edit format, repository mapping, code context |
| OpenHands | All-Hands-AI/OpenHands | Modular agent loop, planning, sandboxed execution |
| Moatless Tools | aorwall/moatless-tools | AST-aware code search, structured editing |
| AutoCodeRover | nus-apr/auto-code-rover | Fault localization, program repair |
| SWE-bench baselines | princeton-nlp/SWE-bench | Official baselines and evaluation patterns |

For each failure class: search GitHub for how reference agents handle it, extract the mechanism (not code), map to a local hypothesis with trace anchor, record URL + mechanism in the candidate table.

### Research literature

Read `docs/references/research/agent-evolution-literature.md` and map mechanisms to local failure classes:

```text
paper mechanism -> local failure class -> branch hypothesis -> benchmark comparison -> ledger decision
```

### Quality check for hypothesis breadth

If the last 3+ completed hypotheses were all narrow parser/prompt tweaks targeting only `invalid_action` without external reference, the current round **must** include at least one **Explore** candidate from a reference agent or research paper.

Do not create a branch from a paper idea until there is trace evidence that it targets an observed failure.
