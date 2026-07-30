# Agent eval scorecard — checkin-mood-trend-v1

> Stage 1: inspect candidate patches and fill quality scores before opening `identity.json`.

Base: `ec2331614b48866a03c670cf0ca9c6d730f4b916` (`bac1ac37828af2cc934234a74114146dc8a3d678`)

## Baseline verification

| Check | Pass | Seconds |
|---|---:|---:|
| backend-checkin | yes | 5.385 |
| frontend-checkin | yes | 1.377 |
| typescript | yes | 14.18 |
| grace-backend | yes | 0.567 |
| diff-check | yes | 0.215 |

## Candidate-blind quality review

| Candidate | Completion / 100 | Accuracy / 100 | Critical failure | Notes |
|---|---:|---:|---|---|
| A | 85 | 100 | yes | Strict wire contract and correct logic, but controller `tsc` fails on an existing typed fixture; final agent report incorrectly claimed all checks passed. |
| B | 90 | 87.5 | no | Fully runnable 5/5 patch; client contract is backward-compatible but weaker because both new fields are optional. |

Use `evals/tasks/checkin-mood-trend-v1/rubric.md`. Do not use cost to score quality.

## Objective evidence (open after quality scoring)

| Candidate | Agent outcome | Seconds | Patch bytes | Control valid | Verification | Input | Cached | Cache write | Output | Reasoning | Normalized cost |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| A | rc=0 | 220.508 | 17610 | yes | 4/5 | 348947 | 2529826 | 0 | 29960 | 3761 | 1.1558019 |
| B | rc=0 | 484.804 | 17842 | yes | 5/5 | 2561400 | 2447872 | 0 | 19690 | 8123 | 0.09529104 |

## Revealed result

- Candidate A: `gemini-3.6-high` via OpenCode (`cliproxy/gemini-3.6-flash-high`).
- Candidate B: `luna-high` via Codex (`gpt-5.6-luna`, high effort).
- Verdict: **Luna wins this pilot on shipability and cost.**
- Rationale: blind patch review preferred A (95/100 vs 85/100) because its API
  fields were strictly required. After objective evidence was revealed, A had a
  task-caused TypeScript failure and therefore a rubric critical failure. B
  passed all five controller gates with no scope/head mutation. B's tradeoff is
  an optional client contract, so this is a pilot result rather than a universal
  model ranking.

## Interpretation

- Quality-only blind review: A 95/100, B 85/100.
- Final acceptance-adjusted completion: A 85/100, B 90/100.
- Business-rule cases: A 8/8; B 7/8 because the published client contract
  permits the two new fields to be absent.
- A is 2.20x faster (220.5s vs 484.8s).
- B is about 12.13x cheaper at the committed official price snapshots
  ($0.0953 vs $1.1558). Luna's number is a base-rate estimate because its JSONL
  exposes aggregate rather than per-request context sizes; the manifest keeps
  the official >272K warning.
