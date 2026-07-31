# Agent eval scorecard — day-momentum-v1

> Stage 1: candidate patches inspected and quality-scored before `identity.json` was opened
> (candidate C's re-run patch was scored knowing it is Gemini's — its identity was
> learned during the first attempt's infra-failure diagnosis).

Base: `ae8dba4f4f1aeeb55604eca005927df688e5f553` (`598ee39b17f2f12cb0b7dda7a673cebded285cd9`)

## Baseline verification

| Check | Pass | Seconds |
|---|---:|---:|
| backend-relative-status | yes | — |
| typescript | yes | — |
| grace-backend | yes | — |
| diff-check | yes | — |

## Candidate-blind quality review

| Candidate | Completion / 100 | Accuracy / 100 | Critical failure | Notes |
|---|---:|---:|---|---|
| A | 95 | 100 (8/8) | no | Correct math, excellent boundary/rounding/mode tests, contracts regenerated. Weaker typing: `momentum` declared `\| None = None` — the wire admits `null` for a field the spec defines as always one of four values. |
| B | 100 | 100 (8/8) | no | Correct math, exact-enum schema (default `"insufficient"`, never null), parametrized tests incl. wire-alias check and mode-consistency, matrix updated in-place. |
| C | 85 | 100 (8/8) | **yes** | The strictest, spec-exact contract (required fields, no defaults) — but that forced a fixture edit in `__tests__/today/day-summary-card.test.tsx`, which is **outside the allowed scope**. Prompt's escape hatch (stop and report) was not taken. GRACE header of `schemas/day.py` left stale. |

Use `evals/tasks/day-momentum-v1/rubric.md`. Do not use cost to score quality.

### Process notes

- Candidate C's first attempt terminated after 48 s with an empty patch (rc=0,
  mid-exploration) — the same runner-side anomaly as in grace-event-registry-v1.
  Re-run solo; the re-run patch and metrics are what is scored here.

## Objective evidence (open after quality scoring)

| Candidate | Agent outcome | Seconds | Patch bytes | Control valid | Verification | Input | Cached | Cache write | Output | Reasoning | Normalized cost |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| A | rc=0 | 430 | 16791 | yes | 4/4 | 72403 | 3330944 | 0 | 13717 | 25161 | 0.0233 |
| B | rc=0 | 506 | 15924 | yes | 4/4 | 2191102 | 2093056 | 0 | 18896 | 9933 | 0.0841 |
| C | rc=0 (re-run) | 190 | 13788 | **no** (scope violation) | 4/4 | 393571 | 1149383 | 0 | 6706 | 11165 | 0.8968 |

## Revealed result

- Candidate A: `deepseek-v4-flash` via OpenCode (`deepseek/deepseek-v4-flash`).
- Candidate B: `luna-max` via Codex (`gpt-5.6-luna`, max effort).
- Candidate C: `gemini-3.6-high` via OpenCode (`cliproxy/gemini-3.6-flash-high`).
- Verdict: **Luna max wins; DeepSeek close second at a quarter of the price; Gemini critical failure.**
- Rationale: all three implemented the algorithm correctly (8/8 each). B has the
  cleanest schema typing and test design. A ties on behavior with slightly looser
  typing, at $0.023 vs $0.084. C wrote the best wire contract but broke the scope
  discipline it had already been warned about — a rubric critical failure.
  Ironically, the two "weaker" optional-field schemas are what kept A and B inside
  the allowed paths.

## Interpretation

- Pure-algorithm work discriminates less than process work: accuracy 100% everywhere.
- The differentiators are contract strictness vs scope discipline — and Gemini
  optimized the first at the cost of the second.
- DeepSeek's reasoning tokens (25k) are 2.5x Luna's (10k) at a third of the price.
