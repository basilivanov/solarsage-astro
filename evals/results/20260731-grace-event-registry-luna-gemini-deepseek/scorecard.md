# Agent eval scorecard — grace-event-registry-v1

> Stage 1: candidate patches inspected and quality-scored before `identity.json` was opened
> (exception: candidate B's identity was learned during infra-failure diagnosis before its
> re-run patch was scored — see note below).

Base: `ae8dba4f4f1aeeb55604eca005927df688e5f553` (`598ee39b17f2f12cb0b7dda7a673cebded285cd9`)

## Baseline verification

| Check | Pass | Seconds |
|---|---:|---:|
| registry-drift | yes | 0.065 |
| frontend-checkin-statistics | yes | 0.616 |
| typescript | yes | 13.207 |
| grace-backend | yes | 0.517 |
| diff-check | yes | 0.115 |

## Candidate-blind quality review

| Candidate | Completion / 100 | Accuracy / 100 | Critical failure | Notes |
|---|---:|---:|---|---|
| A | 100 | 100 (6/6) | no | Full slice: canon XML with payload schema (wave-consistent owner), both registries, emission with exact slice/module/block, FUNCTION_CONTRACT + test annotations, matrix row, meaningful 3-case test file. |
| B | 50 | 50 (3/6) | no | Registry-only patch: event registered in all three stores, but no emission from the component, no tests, no matrix, no GRACE updates. Gates passed vacuously (see caveat). |
| C | 90 | 100 (6/6) | no | Same shape as A, slightly weaker discipline: canon `owner` set to a slice name instead of a wave, no FUNCTION_CONTRACT for the changed public component. Richer matrix row (S1–S5). |

Use `evals/tasks/grace-event-registry-v1/rubric.md`. Do not use cost to score quality.

### Process notes

- Candidate B's first attempt (`20260731t1726…` run) terminated after 21 s with an
  empty patch and rc=0 mid-exploration — runner/infra failure, not a model result.
  Re-run solo (`20260731t1740…`); the re-run patch and metrics are what is scored here.
  Diagnosing the failure required opening B's runner identity before quality scoring,
  so B's review was not fully blind. A and C were scored fully blind.
- Rubric item "payload TypedDict": the backend registry contains no payload TypedDicts
  for any existing event (Literal names only), so the item was scored as following the
  file's actual convention; no candidate was penalized or credited for TypedDicts.
- Gate-vacuity caveat: B's registry-only patch passes all five controller gates
  (the new-test gate uses `--passWithNoTests`, tsc has no consumer of the new event).
  For this task the human rubric is the discriminator; consider a
  "required evidence files exist" gate in a v2 task.

## Objective evidence (open after quality scoring)

| Candidate | Agent outcome | Seconds | Patch bytes | Control valid | Verification | Input | Cached | Cache write | Output | Reasoning | Normalized cost |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| A | rc=0 | 426.975 | 11848 | yes | 5/5 | 1873033 | 1747456 | 0 | 20376 | 8833 | 0.08451572 |
| B | rc=0 (re-run) | 76.792 | 1685 | yes | 5/5 | 296355 | 1477744 | 0 | 3236 | 6562 | 0.7396791 |
| C | rc=0 | 195.471 | 9722 | yes | 5/5 | 57492 | 2137088 | 0 | 8313 | 6448 | 0.01636037 |

## Revealed result

- Candidate A: `luna-max` via Codex (`gpt-5.6-luna`, max effort).
- Candidate B: `gemini-3.6-high` via OpenCode (`cliproxy/gemini-3.6-flash-high`).
- Candidate C: `deepseek-v4-flash` via OpenCode (`deepseek/deepseek-v4-flash`).
- Verdict: **Luna max wins on completeness; DeepSeek is the value pick.**
- Rationale: all three registered the event correctly, but only A and C shipped the
  whole slice (emission + tests + matrix). A is the most disciplined patch
  (wave-consistent canon owner, FUNCTION_CONTRACT). C matches A's behavior
  (6/6 accuracy) at 5.2x lower cost and 2.2x faster, losing 10 completion points
  on GRACE formalities. Per the rubric rule, a >5pp quality gap beats cost.
  B stopped after the registry step — half the task at the highest price.

## Interpretation

- Completion: A 100, B 50, C 90. Accuracy: A 6/6, B 3/6, C 6/6.
- Speed: B 77s (2.5x faster than C, 5.6x than A) — but for half the deliverable.
- Cost: C $0.0164 « A $0.0845 « B $0.7397. DeepSeek is ~45x cheaper than Gemini
  for a strictly better patch.
- One task, one slice: this ranks the models for SolarSage GRACE-process work,
  not universally.
