# Review: W-HORARY-ANSWER-QUALITY-V1

Date: 2026-06-09
Reviewed implementation commit: `c85497faf4f211893de67e01b682e92b8a94792c`
Previous stale review commit: `efbafd4b2d62b75025a7ed35ed1292165f294e0a`
Source TZ: `docs/work/2026-06-09_horary_answer_quality_TZ.md`
Canon dependency: `docs/FAILURE_HANDLING_CANON.md`

## Verdict

Status: **REWORK REQUIRED — 2 BLOCKERS**

The main implementation direction is correct and most of the original horary quality issues are fixed:

- structured `HoraryAnalysis` exists;
- confidence is exposed as `low|medium|high` + explanation;
- LLM receives structured computed evidence;
- generic horary fallback answer was removed;
- invalid LLM output raises `HoraryGenerationError` and the service marks the question failed;
- frontend renders failed/error state instead of a normal-looking answer;
- frontend verdict card renders a confidence label instead of percent/probability.

However, the packet is not accepted yet because two user-facing / gate issues remain.

## Accepted parts

### A1. Engine now returns structured analysis

`HoraryEngine.analyze()` now returns `HoraryAnalysis` with:

- verdict;
- confidence score;
- confidence label;
- confidence explanation;
- testimonies for;
- testimonies against;
- neutral factors;
- timing;
- calculation warnings.

The old `compute_verdict()` remains only as a backward-compatible helper and delegates to `analyze()`.

### A2. Structured evidence model exists

`apps/api/app/schemas/horary_analysis.py` defines explicit models for evidence, timing and analysis.

Important invariant is present: every evidence item is `source="computed"`, and confidence label is restricted to `low|medium|high`.

### A3. LLM generation no longer has generic fallback

`LLMService.generate_horary_answer()` now accepts `HoraryAnalysis`, builds the prompt from structured evidence, validates block structure, and raises `HoraryGenerationError` after failed attempts.

This removes the previous generic two-line fallback answer.

### A4. Service failure path does not save `HoraryAnswer`

`HoraryService._generate_answer_task()` catches `HoraryGenerationError`, marks the question as `failed`, refunds through `_refund_credit_for_failed_question()`, commits, and returns before answer creation.

This is the correct direction for the no-synthetic-fallback canon.

### A5. Frontend no longer renders probability wording in verdict card

`HoraryBlockRenderer` renders `Уверенность разбора: Низкая/Средняя/Высокая` and does not display percent probability in the verdict card.

### A6. Failed/error state exists on answer page

The horary answer page now renders a visible failed/expired state and says it will not show generic text instead of a real reading.

## Blockers

### B1. Grep guard is broken and not wired into guardrails

`W-HORARY-ANSWER-QUALITY-V1` requires a grep guard for hardcoded timing, generic fallback text and probability wording.

A guard script was added at `scripts/check_horary_quality.sh`, but it has two problems:

1. `ROOT` is computed as `$(dirname scripts/check_horary_quality.sh)/../..`, which resolves to the parent of the repository, not the repository root. Since the script lives in `scripts/`, it should use `/..`, not `/../..`.
2. The script is not called from `package.json` scripts or from `scripts/guardrails.sh`, so normal `guardrails`, `guardrails:full`, `guardrails:strict`, frontend, backend or prod guard runs will not execute it.

Impact: the advertised regression guard can report OK or never run at all, so the packet does not actually satisfy the acceptance gate.

Required fix:

- change `ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"`;
- add a package script, e.g. `guardrails:horary-quality`;
- call it from `scripts/guardrails.sh` in `run_frontend` or `run_full`;
- add evidence that the script fails when a forbidden string is intentionally present, or at least show a real successful run from repo root.

### B2. `creditRefunded` can be incorrect/misleading

`_to_question_read()` currently sets:

`credit_refunded = q.status == "failed" and q.spent_credit_id is not None`

But `_refund_credit_for_failed_question()` can decide not to refund expired weekly-free credits while still deleting the spend row. The question also keeps `spent_credit_id`.

Impact: UI can show `Списание возвращено` even when no refund happened. This violates the failure-handling canon because the error state may mislead the user about credit recovery.

Required fix:

- persist refund outcome explicitly, e.g. `HoraryQuestion.refund_status = refunded | not_refundable | none`, or equivalent;
- return `creditRefunded=true` only when `used_amount` was actually decremented/refund was actually applied;
- add tests for both paths:
  - paid credit failed => `creditRefunded=true`;
  - expired weekly-free failed => `creditRefunded=false` / `not_refundable`.

## Important non-blocking risks

### R1. LLM can still alter evidence contents inside `testimonies`

The prompt instructs the LLM to use only provided evidence, and schema validation checks block shape. But validation does not verify that LLM-provided testimony titles/explanations/weights correspond exactly to computed evidence.

This is acceptable for this iteration if the product owner accepts LLM paraphrasing, but the stronger version would render testimonies directly from backend-computed evidence and let LLM write only explanatory paragraphs.

### R2. Category timing hints use internal English ranges

`_CATEGORY_TIMING_HINTS` stores values like `weeks`, `months`, `weeks-months`. If these ever leak into `timeRange`, they will be user-visible English/internal labels. The prompt currently asks LLM to avoid `timeRange` for unclear timing, but the risk remains.

Preferred fix: store Russian display labels or split internal bucket from user-facing label.

### R3. CI/workflow status was not visible through connector

`fetch_commit_workflow_runs` returned no workflow runs for implementation commit `c85497faf4f211893de67e01b682e92b8a94792c`.

Commit message claims backend/frontend tests and grep guard, but I could not independently verify CI from GitHub.

## Acceptance checklist

```text
[x] Generic horary fallback answer removed.
[x] Invalid LLM JSON raises HoraryGenerationError.
[x] Invalid/unavailable generation marks question failed/error.
[x] Invalid/unavailable generation does not save HoraryAnswer.
[!] Credit refund works for paid-credit happy failure path, but user-visible creditRefunded can be false-positive.
[x] Hardcoded `2–3 недели` removed from main horary prompt/template.
[x] Timing supports known / unclear / not_enough_evidence states.
[x] Engine returns structured evidence via HoraryAnalysis.
[x] LLM receives structured computed evidence.
[x] Public UI shows low/medium/high confidence, not probability percent.
[x] Backend tests added for engine and LLM failure behavior.
[x] Frontend tests added for verdict/timing/error state.
[ ] Grep guard is correctly rooted and wired into guardrails.
[ ] Failed-question refund flag is accurate for refundable vs non-refundable credits.
```

## Required rework packet

### W-HORARY-ANSWER-QUALITY-FOLLOWUP-1

Scope:

- `scripts/check_horary_quality.sh`
- `scripts/guardrails.sh`
- `package.json`
- `apps/api/app/api/horary.py`
- `apps/api/app/services/horary_service.py`
- `apps/api/app/db/models.py` and migration only if explicit refund status is persisted
- backend tests for refund flag correctness

Tasks:

1. Fix guard script root path.
2. Wire horary quality guard into normal guardrails.
3. Make `creditRefunded` reflect actual refund result, not `spent_credit_id != null`.
4. Add paid-credit and expired-weekly-free failure tests.
5. Re-run backend tests, frontend tests, contracts if schema changes, and guardrails/horary-quality guard.

## Final conclusion

Do not accept yet.

The core feature implementation is mostly done, but the packet still fails two important acceptance conditions: a broken/unwired regression guard and a potentially misleading refund flag in the failed-answer UX.
