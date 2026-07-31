# Agent eval scorecard — sidecar-planet-house-v1

> Stage 1: candidate patches inspected and quality-scored before `identity.json` was opened.

Base: `ae8dba4f4f1aeeb55604eca005927df688e5f553` (`598ee39b17f2f12cb0b7dda7a673cebded285cd9`)

## Baseline verification

| Check | Pass | Seconds |
|---|---:|---:|
| sidecar-natal | yes | — |
| api-normalization | yes | — |
| grace-backend | yes | — |
| diff-check | yes | — |

## Harness incident (task-caused, fixed and re-verified)

The original `sidecar-natal` gate resolved `import solarsage` to the **main tree**
(the linked venv carries an editable install pointing at `/opt/solarsage-astro`),
so candidates' sidecar changes were invisible to their own tests. Both real
candidates failed the gate for harness reasons. Fix: `PYTHONPATH=apps/solarsage`
in the gate (committed to `task.toml` and `prompt.md`). Both candidates were
re-verified manually in fresh worktrees from the same base with their exact
patches: **all gates green for both**. The task had no scored run before the fix,
so the immutability rule was not violated.

## Candidate-blind quality review

| Candidate | Completion / 100 | Accuracy / 100 | Critical failure | Notes |
|---|---:|---:|---|---|
| A | 95 | 100 (8/8) | no | `NatalPlanet` subclass with range-validated `house` (ge=1, le=12), `_find_house` in the natal service, context-service boundary re-validation, deterministic monkeypatched boundary tests. Unnecessary scope stretch: added `house_system` to the sidecar request schema (B proved both systems testable without it). |
| B | 100 | 100 (8/8) | no | `find_house` + `assign_planet_houses` on the chart model, transit schema explicitly kept house-free, broadest coverage: real-ephemeris endpoint tests (Moscow + high-latitude Murmansk), wraparound units, normalization edge cases (empty houses, null, boundary 1/12, `normalize_day` path). Zero scope stretch. |
| C | 0 | 0 | no (no result) | **No result**: three consecutive runner-side empty patches (20s/15s/10s, rc=0, mid-exploration). Scored as n/a, not as model quality. |

Use `evals/tasks/sidecar-planet-house-v1/rubric.md`. Do not use cost to score quality.

## Objective evidence (open after quality scoring)

| Candidate | Agent outcome | Seconds | Patch bytes | Control valid | Verification | Input | Cached | Cache write | Output | Reasoning | Normalized cost |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| A | rc=0 | 888 | 28614 | yes | 4/4 (re-verified) | — | — | — | — | — | 0.1795 |
| B | rc=0 | 508 | 32303 | yes | 4/4 (re-verified) | — | — | — | — | — | 0.0409 |
| C | rc=0 ×3, empty | 45 (3 attempts) | 0 | n/a | 4/4 vacuous | 88683 | 130849 | 0 | 54 | 2581 | 0.2684 |

## Revealed result

- Candidate A: `luna-max` via Codex (`gpt-5.6-luna`, max effort).
- Candidate B: `deepseek-v4-flash` via OpenCode (`deepseek/deepseek-v4-flash`).
- Candidate C: `gemini-3.6-high` via OpenCode (`cliproxy/gemini-3.6-flash-high`).
- Verdict: **DeepSeek wins the cross-codebase task outright; Luna close second; Gemini no result.**
- Rationale: both real patches are correct on every accuracy case, including the
  backward-compatibility matrix. B is cleaner (no API-surface change, transit
  explicitly untouched) and far broader on tests, at a quarter of A's price and
  1.75x faster. A is more defensive at the context boundary but paid for it with
  an unnecessary request-schema change.

## Interpretation

- The hardest task flipped the ranking: DeepSeek's deliberate, test-heavy style
  wins on cross-codebase compatibility work.
- Gemini's runner produced 4 empty deaths out of 8 attempts across the suite
  (2 of them recovered on re-run). On this task it never produced a patch —
  treat its row as missing data, and the cliproxy/OpenCode path as a stability
  risk to investigate separately from model quality.
