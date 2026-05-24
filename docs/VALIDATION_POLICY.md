# Validation Policy

## Goal

Achieve **full resolution of the evolution set** (336/336 SWE-bench Verified instances), **or** reach a state where no Pareto improvement is possible for **20 consecutive hypothesis attempts** on the active batch.

## Set Definitions

| Set | Size | Purpose |
|-----|------|---------|
| **Evolution set** | 336 instances (2/3 of 500) | Training ground for agent improvement. All hypothesis validation happens here. |
| **Test set** | 164 instances (1/3 of 500) | Final control. Measures whether improvements on the evolution set generalize. |

The split is **stratified by project**: each Python repository contributes proportionally 2/3 to the evolution set and 1/3 to the test set. This ensures both sets contain representative difficulty distributions across all projects.

Instance assignments are fixed in [`artifacts/meta/validation-sets.json`](artifacts/meta/validation-sets.json). No instance ever moves between sets. The meta-agent may update batch `status` and `no_improvement_count`, but never the instance assignments themselves.

## Batch Organization

The evolution set is divided into **56 batches of 6 instances** each.

- **Batch 0**: contains the 3 already-resolved instances (astropy\_\_astropy-12907, astropy\_\_astropy-14309, django\_\_django-10097) plus 3 additional evolution-set instances. Status: `active`.
- **Batches 1–55**: status `locked` until activated.

The agent works through batches one at a time. Only the **active batch** is used for validation gates.

## Expanding Batch Rules

A new batch activates (transitions from `locked` to `active`) when either condition is met:

1. **Full resolution**: All instances in the current active batch are resolved.
2. **Plateau**: 20 consecutive hypothesis attempts produce **no Pareto improvement** on the active batch. A "Pareto improvement" is any of: a new instance resolved, a measurable trace-metric improvement on an unresolved instance in the active batch (per the analyzer's Pareto ladder). The `no_improvement_count` in `validation-sets.json` tracks this and **resets to 0** whenever any improvement occurs.

When a batch activates via the plateau rule, its status is set to `expanded` rather than `active`, recording that it was opened due to stagnation rather than success.

Multiple batches can be active simultaneously if plateau expansions accumulate. The meta-agent should focus validation on the **lowest-numbered active batch**.

## Test Set Isolation

The test set is **strictly off-limits** during evolution:

- The meta-agent **MUST NOT** run, reference, or inspect test-set instances.
- Test set evaluation occurs **ONLY** after: (a) the entire evolution set is fully resolved, **or** (b) 20 consecutive no-improvement attempts on the current active batch have been reached and **confirmed by the human operator** as a terminal plateau.
- Test set evaluation requires **explicit human consent** before any run is started.
- Test set results are the **final control**: they measure whether improvements on the evolution set generalize to unseen instances.

## Batch Status Lifecycle

```
locked → active → resolved
              ↘ expanded (activated via plateau)
```

| Status | Meaning |
|--------|---------|
| `locked` | Not yet activated. The meta-agent cannot run these instances. |
| `active` | Currently being worked on. Validation gates use instances from this batch. |
| `resolved` | All instances in this batch are resolved. |
| `expanded` | Activated due to the 20-attempt plateau rule (rather than full resolution of the previous batch). |

## Validation Gates

| Gate | Scope | Consent required |
|------|-------|-----------------|
| **One-task gate** | Single instance from the active batch | No (autonomous) |
| **Batch gate** | All instances in the active batch | No (autonomous) |
| **Full evolution set** | All 336 evolution-set instances | Yes (human) |
| **Test set** | All 164 test-set instances | Yes (human + evolution completion/plateau) |

The one-task gate is cheap falsification. The batch gate is the primary decision point for merge/reject. Full evolution set and test set runs measure generalization and require human approval.

## Termination

The evolution loop terminates when:

1. **Full evolution set resolved** (336/336): trigger test set evaluation with human consent.
2. **Confirmed plateau**: 20 consecutive no-improvement attempts on the active batch, confirmed by the human operator as terminal. Trigger test set evaluation.
3. **Budget exhausted**: stop and report current state.

After test set evaluation, the project's final score is the test set resolve rate — the only number that matters for generalization claims.
