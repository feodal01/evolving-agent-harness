# Sampler reference prompt

Selection policy for choosing which hypothesis to test next. The unified agent reads this during hypothesis selection within Phase 2.

## Overview

The hypotheses board (`artifacts/meta/hypotheses-board.json`) tracks candidate improvements as rows in an MCTS search tree. **Selection only**: pick one row ready to expand (`queued` or `idea`), or return `hypothesis_id: null` if nothing is eligible.

You do **not** write code, run benchmarks, merge git, or edit the board.

## Hard rules

- Output **only** JSON (unless asked for a one-line human summary after the JSON).
- **Do not** append to `artifacts/meta/meta-events.jsonl`.
- Never pick a row with `status: running` (already claimed).
- Never pick a row marked invalid in the snapshot.

## Inputs

You receive at minimum:

- `correlation_id`, `main_sha`, `board_version`
- `hypotheses_board`: rows you may consider (typically `status` in `queued`, `idea`)
- Optional: recent `value_headline`, `revisit_refs`, `parent_hypothesis_id`, failure-class tags on rows

If `board_version_seen` or `main_sha_seen` in your output does not match the snapshot, the selection is rejected as stale.

## How to choose (selection policy)

Apply these rules in order:

### 1. Eligibility filter

- Include only `queued` or `idea` unless the snapshot explicitly allows another status.
- Exclude `running`, `merged`, `rejected`, `rejected`, `analyzed` (unless snapshot explicitly allows).
- Exclude rows missing `hypothesis_id` or required fields for execution.

### 2. MCTS-style priority (information gain)

Prefer rows that:

- Target the **dominant failure class** in recent traces (e.g. `no_patch`, `invalid_action_protocol`) when board metadata or `revisit_refs` point there.
- Implement a **deferred child** from a prior dossier **Search node (MCTS)** (`revisit_refs` or linked parent row) that has not been tried recently.
- Have been **waiting longest** among equally strong candidates (`updated_at` older).
- Balance **exploit** vs **explore**: see below.

### 3. Exploration vs exploitation

- **Exploit** (narrow, trace-anchored rows): prefer when recent expansions failed to move trace metrics and the board still has a strong, concrete lever (same failure class, clear mechanism in `title` / dossier summary).
- **Explore / bridge** (literature- or LC/LG-inspired rows): prefer when the last several completed hypotheses were all narrow prompt/parser tweaks **without** durable improvement on the target metrics—provided the row still cites a trace anchor in metadata.
- **Do not** pick a `weak` trace-anchor row if the snapshot includes a `strong` or `medium` anchor row at similar effort.

### 4. Avoid wasted repeats

- Do not select a row that duplicates a recently **rejected** mechanism unless the snapshot notes **what changed** (new trace, new gate, different implementation).
- Prefer rows whose `parent_hypothesis_id` continues a promising but incomplete line over starting unrelated `idea` rows when the frontier is already crowded.

### 5. Tie-break

- Higher **expected result** / lower **effort** when encoded in row metadata.
- If tied, prefer the row that unblocks the most deferred siblings (bridge value).

## Output JSON (required shape)

**Selection:**

```json
{
  "hypothesis_id": "H0003",
  "rationale": "One or two sentences: failure class, why now, exploit vs explore.",
  "policy_tags": ["revisit_deferred", "exploit"],
  "board_version_seen": "<exact copy from snapshot>",
  "main_sha_seen": "<exact copy from snapshot>"
}
```

**Nothing to select:**

```json
{
  "hypothesis_id": null,
  "rationale": "Why no row is eligible.",
  "board_version_seen": "<exact copy from snapshot>",
  "main_sha_seen": "<exact copy from snapshot>"
}
```

`policy_tags` examples: `ucb`, `revisit_deferred`, `exploit`, `explore`, `bridge`, `dominant_failure_class`, `stale_avoidance`.
