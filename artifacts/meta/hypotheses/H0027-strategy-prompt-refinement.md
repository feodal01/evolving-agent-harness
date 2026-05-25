# Hypothesis dossier: H0027

## Identity

| Field | Value |
|-------|-------|
| hypothesis_id | H0027 |
| title | Strategy prompt refinement for better edit quality |
| branch | hyp/H0027-strategy-prompt-refinement |
| parent_hypothesis_id | H0026 |
| parent_commit | eee1ef9 |
| correlation_id | round-20260525-batch0-gate |
| fix_type | hypothesis |
| status | rejected |

## Problem statement

The agent often stops after a single edit even when the fix requires multiple changes. The current strategy prompt says "Stop once you have made the edit" which discourages multi-edit fixes.

## Proposed change

Refine the system prompt to: (1) identify ALL locations that need to change before editing, (2) read back after each edit to verify, (3) continue editing if more changes needed. Also update _NO_EDIT_REMINDER to reference edit_file instead of sed -i.

## Results

**Run 1**: astropy-13236 (20260525-161755)
- 24 iters (was 8), 1587 bytes (was 787), resolved=false (same)
- Agent made multi-file edits (table.py + test_mixin.py) — behavior improved but fix still incorrect

**Run 2**: astropy-13398 (20260525-165330)
- 60 iters, GraphRecursionError, 30 edit_file calls, resolved=false
- Agent made 30 edits — way too many, stuck in edit loop

**Run 3** (regression test): astropy-13033 (20260525-170658)
- 26 iters (was 13), 4348 bytes (was 1307), resolved=FALSE (was TRUE)
- **REGRESSION**: Agent made larger, more complex patch that broke the previously-correct fix
- Original minimal patch (1307 bytes) was correct; new larger patch (4348 bytes) is incorrect

## Verdict

REJECTED. The strategy prompt refinement causes regression on previously-solved tasks. Instructing the agent to "identify ALL locations" leads to over-editing and larger, less correct patches. The minimal edit strategy ("Stop once you have made the edit") actually produces better results with this model.

Key learning: for weaker models (glm5-fp8), minimal edit instructions produce better patches than comprehensive multi-edit instructions. The model doesn't have the reasoning capability to correctly identify all needed changes — it just adds more noise.
