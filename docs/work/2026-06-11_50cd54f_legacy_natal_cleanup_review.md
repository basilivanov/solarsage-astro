# Review: 50cd54f — Legacy Natal Cleanup

Date: 2026-06-11
Status: ACCEPTED
Reviewed commit: `50cd54ffa0b9d617e5bebf6ff2f5b6a0d720a318`
Branch: `feat/natal-full-report`
Related prior review: `docs/work/2026-06-10_e309ef3_wave_1_2_acceptance_review.md`

## 1. Scope reviewed

Commit `50cd54f` performs the cleanup that was left as a non-blocking note after Wave 1–2 acceptance:

- removes legacy `GET /api/natal/overview`;
- removes legacy `GET /api/natal/section/{section_id}`;
- removes hardcoded `NatalService.get_natal_reading()`;
- removes the legacy `apps/api/tests/test_natal.py` file;
- updates preview/full-report tests to mock the new `natal_context_service.get_solarsage_client` path;
- adds test evidence in `docs/work/2026-06-11_wave_1_2_test_evidence.md`;
- updates module contracts to match the new production path.

Commit message reports: `68 tests passed, 0 failed`.

## 2. Verdict

ACCEPTED.

The cleanup matches the requested architecture: production natal data now goes through `NatalContextService`, and the old hardcoded MVP reading path is removed from API and service code.

## 3. Checks

### CHECK 1 — Legacy API endpoints removed

Status: OK.

The diff removes:

```python
@router.get("/api/natal/overview")
@router.get("/api/natal/section/{section_id}")
```

This closes the previous risk that fake/hardcoded natal content could still be reachable through legacy routes.

### CHECK 2 — Hardcoded `get_natal_reading()` removed

Status: OK.

`NatalService.get_natal_reading()` and its hardcoded Sun/Moon/Ascendant blocks were removed.

This is important because the method contained fake chart facts such as:

- Sun in Aries;
- Moon in Cancer;
- Ascendant in Leo;
- Moscow 1990 birth metadata.

Those facts must not exist in production paths.

### CHECK 3 — NatalService contract now matches actual role

Status: OK.

The module contract now describes `NatalService` as a preview builder over cached `NatalContext`, not a hardcoded full reading generator.

This matches the intended Wave 1–2 architecture.

### CHECK 4 — Tests moved to correct mock boundary

Status: OK by commit diff/summary.

Mocks were moved from the old `natal_service.get_solarsage_client` location to the new `natal_context_service.get_solarsage_client` location, which is now the actual sidecar boundary.

This is the correct test seam after introducing `NatalContextService`.

### CHECK 5 — Legacy tests removed

Status: OK.

`tests/test_natal.py` only tested legacy overview/section endpoints, so removing it is appropriate after removing those routes.

Important: this is acceptable because current preview/full-report tests were updated instead of leaving the area untested.

### CHECK 6 — Evidence artifact added

Status: OK, with note.

The commit adds a test evidence artifact and reports `68 tests passed, 0 failed`.

I did not see GitHub CI statuses attached through the connector during review, so final merge should still rely on local/CI evidence from the implementation packet.

## 4. Remaining notes

### NOTE 1 — Frontend route audit

Before final production merge, do a quick frontend grep for:

- `/api/natal/overview`
- `/api/natal/section/`

This review saw the backend cleanup in the commit diff, but frontend references should be explicitly checked by coder/evidence verifier.

### NOTE 2 — Docs/history references are allowed

Old docs/packets/review files may still mention legacy endpoints historically. That is acceptable as long as runtime code and current tests do not depend on them.

## 5. Acceptance decision

Accepted.

This commit completes the Wave 1–2 cleanup note from the previous acceptance review: legacy fake natal endpoints and hardcoded service content are removed.
