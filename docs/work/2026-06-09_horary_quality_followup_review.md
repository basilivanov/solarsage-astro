# Review: W-HORARY-ANSWER-QUALITY-V1 follow-up

Date: 2026-06-09
Reviewed commit: 3d78579b16025167e8e3e39fdecb4cf8a9855f80
Base commit: e493b9539a758ed6aaac94114a902192262196db
Verdict: ACCEPTED

## Scope reviewed

Changed files:

- apps/api/alembic/versions/0013_add_horary_refund_status.py
- apps/api/app/api/horary.py
- apps/api/app/db/models.py
- apps/api/app/services/horary_service.py
- apps/api/tests/test_horary_endpoints.py
- apps/api/tests/test_horary_service.py
- package.json
- scripts/check_horary_quality.sh
- scripts/guardrails.sh

## Findings

### B1 — horary quality grep guard

Status: ACCEPTED

The script root calculation is now correct for a script located under `scripts/`:

- ROOT resolves to `<repo>/scripts/..`.
- The guard checks the production horary prompt/code path for hardcoded default timing.
- The guard checks old generic horary fallback phrases.
- The guard checks horary UI/contracts for probability wording.
- `package.json` exposes `guardrails:horary-quality`.
- `scripts/guardrails.sh` runs the guard inside `run_frontend`, therefore it is included in frontend, vercel, full, and strict guardrail paths.

No blocker found.

### B2 — explicit refund outcome

Status: ACCEPTED

The previous API behavior could report `creditRefunded=true` based only on failed question + spent credit ID. That could mislead the UI for non-refundable credits.

The follow-up adds explicit persisted refund state:

- `HoraryQuestion.refund_status` with values `none|refunded|not_refundable`.
- Alembic migration `0013_add_horary_refund_status`.
- `_refund_credit_for_failed_question` writes the real outcome.
- `_to_question_read` now maps `creditRefunded` from `refund_status == "refunded"`.
- Tests cover paid refund and expired weekly-free non-refund at service and endpoint levels.

No blocker found.

## Verification evidence

Coder-reported evidence:

- 255 backend tests pass.
- 484 frontend tests pass.
- `guardrails:horary-quality` passes.
- Negative guard test with injected hardcoded timing exits with 1, then restored.

Connector-visible CI evidence:

- No GitHub Actions workflow runs were visible for the reviewed commit through the connector.
- No combined GitHub status checks were visible through the connector.

## Residual notes

1. CI/status could not be independently verified through GitHub connector. Acceptance relies on the coder-provided local evidence plus diff review.
2. A future hardening improvement could add DB-level CHECK constraint for `refund_status`, but this is not required for this follow-up.
3. A future hardening improvement could make refund status updates explicitly idempotent for impossible inconsistent states such as spend row present with `used_amount=0`, but normal ledger invariants make this non-blocking.

## Final decision

ACCEPTED.

The two reported blockers are addressed. The implementation aligns with the failure-handling canon and the W-HORARY-ANSWER-QUALITY requirements for honest error/refund reporting and guardrail coverage.
