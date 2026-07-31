# Agent eval scorecard — ui-contract-disclosure-v1

> Stage 1: candidate patches inspected and quality-scored before `identity.json` was opened.

Base: `ae8dba4f4f1aeeb55604eca005927df688e5f553` (`598ee39b17f2f12cb0b7dda7a673cebded285cd9`)

## Baseline verification

| Check | Pass | Seconds |
|---|---:|---:|
| frontend-checkin-statistics | yes | — |
| typescript | yes | — |
| grace-frontend | yes | — |
| diff-check | yes | — |

## Candidate-blind quality review

| Candidate | Completion / 100 | Accuracy / 100 | Critical failure | Notes |
|---|---:|---:|---|---|
| A | 85 | 100 (7/7) | **yes** | Correct contract implementation, but its own new test file fails `tsc` (fixture field `lastCheckinDate` not in `CheckinMetrics`, TS2353); empty-state test is vacuous (asserts the loading state); verification matrix not updated. |
| B | 100 | 100 (7/7) | no | Complete contract: all states, `hidden`-based disclosure with `aria-labelledby`, FUNCTION_CONTRACT + invariants, matrix row, and the only real empty-state test (waits for the testid to disappear). |
| C | 95 | 100 (7/7) | no | Same behavior as B, slightly less thorough: no FUNCTION_CONTRACT, no empty-state case, no aria-controls→element resolution check. |

Use `evals/tasks/ui-contract-disclosure-v1/rubric.md`. Do not use cost to score quality.

## Objective evidence (open after quality scoring)

| Candidate | Agent outcome | Seconds | Patch bytes | Control valid | Verification | Input | Cached | Cache write | Output | Reasoning | Normalized cost |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| A | rc=0 | 46 | 9294 | yes | 3/4 | 72244 | 326630 | 0 | 4522 | 1844 | 0.2051 |
| B | rc=0 | 329 | 13181 | yes | 4/4 | 752974 | 671744 | 0 | 15972 | 8135 | 0.0488 |
| C | rc=0 | 166 | 11243 | yes | 4/4 | 37793 | 1058176 | 0 | 7974 | 7509 | 0.0105 |

## Revealed result

- Candidate A: `gemini-3.6-high` via OpenCode (`cliproxy/gemini-3.6-flash-high`).
- Candidate B: `luna-max` via Codex (`gpt-5.6-luna`, max effort).
- Candidate C: `deepseek-v4-flash` via OpenCode (`deepseek/deepseek-v4-flash`).
- Verdict: **Luna max wins; DeepSeek again the value pick; Gemini critical failure.**
- Rationale: B is the only patch with complete GRACE hygiene and a real empty-state
  test. C matches the behavior contract for a fifth of B's price and half the time,
  losing 5 points on thoroughness. A implemented the contract correctly but shipped
  a test file that does not typecheck — the same failure class as in the
  checkin-mood-trend pilot (fixture type drift) — a rubric critical failure.

## Interpretation

- Completion: A 85, B 100, C 95. Accuracy: 7/7 for all three (behavior is correct
  everywhere; differences are hygiene and test quality).
- Gemini's 46s / $0.21 looks efficient until you count the cost of a red `tsc`.
- DeepSeek: 4/4 gates, $0.0105 — the cheapest shippable patch of the batch.
