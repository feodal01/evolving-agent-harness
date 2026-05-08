# H0001 Baseline Agent And Harness Evidence

Status: baseline

Branch: `main`

## Purpose

Record the initial project state before future branch-level hypotheses. This is not a single improvement hypothesis; it is the evidence bundle that defines the starting point.

## Background

The initial agent is a simple LangChain-based coding loop around `google/gemma-4-26b-a4b-it` through OpenRouter. The harness runs one SWE-bench Verified task, records unified traces, and evaluates generated patches through the SWE-bench harness.

## Baseline Runs

| Run id | Purpose | Outcome |
| --- | --- | --- |
| `20260508-162348-astropy__astropy-12907` | first end-to-end run | empty patch, invalid action protocol dominated |
| `20260508-163201-astropy__astropy-12907` | parser and checkout infrastructure check | tool actions executed, empty patch |
| `20260508-164343-astropy__astropy-12907` | unified trace check | trace created, later found hidden fields in task event |
| `20260508-164503-astropy__astropy-12907` | no-gold-leakage trace check | trace created without gold/test patch fields |

## Findings

- The benchmark runner can execute SWE-bench evaluation and produce result artifacts.
- The unified `trace.jsonl` is now the canonical trace artifact.
- Hidden SWE-bench answer fields are excluded from public task artifacts.
- The baseline agent still fails behaviorally: it does not produce a tracked source patch on the baseline task.

## Next Useful Hypothesis Area

The next behavior-changing hypothesis should target `no_patch` and repeated unproductive reproduction-file writes. Candidate directions include stronger finalization criteria, structured edit tools, or anti-repetition control.

Do not treat this dossier as a confirmed improvement. It is baseline context for future hypotheses.
