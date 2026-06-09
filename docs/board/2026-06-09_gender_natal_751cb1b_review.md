# Review: Gender + Natal Preview MVP

Date: 2026-06-09
Reviewed commit: 751cb1b92fb9482a54dba8229748f6190ac97081
Base commit: 51f27131f0474cc402f8991fcc3923f8906e0755
Verdict: REJECTED

## Scope reviewed

The commit claims:

- `feat: natal preview MVP + gender field`
- profile gender field and migration;
- `/api/natal/preview`;
- `/readings/natal` mini landing;
- calculation stats;
- gendered Russian wording;
- profile incomplete / error states.

Changed areas:

- Profile schema/model/service/API;
- Natal API/service/schema;
- Natal frontend route and components;
- frontend natal API/client contracts;
- generated contracts;
- migration `0015_add_profile_gender.py`.

## Positive findings

1. The old locked natal placeholder was replaced by a real `/readings/natal` frontend page that calls `fetchNatalPreview()` and renders loading, profile-incomplete, error, and ready states.
2. Backend added `GET /api/natal/preview` returning `NatalPreviewRead`.
3. `user_profiles.gender` was added as a nullable DB column, and `ProfileRead/ProfileWrite` expose `gender` as `male|female|null`.
4. The preview service requires core birth data and `gender` before generating the natal preview.
5. The CTA price is represented as `99900` kopecks, which is correct for 999 ₽.
6. The frontend CTA is disabled, so it does not currently route into a broken payment flow.

Direction is good, but the packet is not yet acceptable.

## Blockers

### B1 — Gender onboarding is not implemented

Status: BLOCKER

The gender field exists in the backend model/schema, but the active onboarding flow does not ask `Мужчина / Женщина`, does not store `gender`, and does not pass it in `updateProfile()`.

Current active onboarding steps are still only:

- welcome;
- birth;
- place;
- birthday;
- done.

The finish payload sends birth/current/birthday locations, but no `gender`.

Also, backend `update_profile()` still marks the profile as onboarded when only `birthday` and `birth_city` exist. It does not require gender, birth time, or birth coordinates before setting `is_onboarded=true`.

Why this is a blocker:

- New users can complete onboarding without gender.
- Natal preview then returns `409 profile_incomplete` instead of working after onboarding.
- This violates `W-PROFILE-GENDER-ONBOARDING`: new onboarding must require `male|female`, and existing users without gender must be explicitly completed.

Required fix:

1. Add onboarding step/field: `Ты мужчина или женщина?` with `Мужчина` / `Женщина`.
2. Add gender to onboarding reducer/state/local profile if needed.
3. Send `gender` in `updateProfile()` from onboarding.
4. Do not mark profile onboarded unless required MVP fields are present, including gender and required birth data.
5. Add frontend and backend tests for missing gender blocking onboarding/profile completion.

### B2 — Profile incomplete API shape is incompatible with the frontend parser

Status: BLOCKER

Backend raises FastAPI `HTTPException` with `detail={"message": ..., "missingFields": ...}`.

FastAPI serializes this as:

```json
{"detail": {"message": "...", "missingFields": [...]}}
```

But `lib/api/natal.ts` parses the response as if `message` and `missingFields` were top-level fields:

```ts
const body: ErrorBody = await res.json()
body.message
body.missingFields
```

Result:

- `missingFields` is lost;
- frontend profile-incomplete screen receives `[]`;
- completion CTA cannot tell what is missing;
- user sees less useful/error-prone state.

Required fix:

- Parse both top-level and FastAPI nested `detail` shape.
- Prefer a typed backend error contract, for example:

```json
{
  "detail": {
    "code": "PROFILE_INCOMPLETE",
    "message": "Нужно дозаполнить профиль...",
    "missingFields": ["gender"]
  }
}
```

- Add test for `409 profile_incomplete` preserving missing fields.

### B3 — Natal preview does not meet the requested product scope: only 3 spheres and 3 chapters

Status: BLOCKER

The approved TZ asks for:

- top 5–7 life spheres;
- 8 locked full-report chapters;
- sales layer that makes the future 999 ₽ report feel valuable.

Current implementation:

- `_build_spheres()` returns only `ranked[:3]`.
- `_build_chapters()` returns only 3 chapters: relationships, purpose, money.

Why this is a blocker:

- The screen is materially smaller than the requested mini landing.
- It weakens the “full report” sales promise.
- It does not satisfy the explicit acceptance criteria.

Required fix:

1. Return 5–7 spheres if scoring data has them.
2. Return 8 locked chapters.
3. Add tests/snapshot or DOM checks for 8 chapter cards and at least 5 sphere cards when data exists.

### B4 — Calculation stats do not follow the TZ counting/display rules

Status: BLOCKER

The addendum requires backend-computed `calculationStats` and bucketed display labels:

- `>=350` → `350+ факторов карты`
- `>=300` → `300+ факторов карты`
- `>=200` → `200+ факторов карты`
- otherwise exact count

Current implementation returns:

```python
display_label=f"{planets_count} планет • {aspects_count} аспектов • {spheres_count} сфер"
```

Also `total_factors_count` omits `spheres_count` and `dignity_factors_count` from the sum, despite returning both fields.

Why this is a blocker:

- The mini landing cannot truthfully display the requested “300+/350+ факторов карты” value.
- The total count is inconsistent with the response fields.
- The product promise from the addendum is not implemented.

Required fix:

1. Compute `total_factors_count` from all real counted groups.
2. Implement the display bucket rule.
3. Do not claim groups that are absent.
4. Add tests for exact/200+/300+/350+ buckets.

### B5 — Backend exposes raw internal errors from natal preview

Status: BLOCKER

`/api/natal/preview` catches any exception and returns:

```python
detail=f"Failed to build natal preview: {exc}"
```

The service also exposes raw sidecar exception text as detail:

```python
detail=f"SolarSage sidecar request failed: {exc}"
```

Why this is a blocker:

- User-facing/API-visible responses may leak internal implementation details.
- This violates the failure-handling canon: show honest user-safe error, not raw internals and not fake fallback.

Required fix:

- Log the raw exception internally.
- Return safe public error code/message, for example:

```json
{
  "detail": {
    "code": "NATAL_PREVIEW_FAILED",
    "message": "Не удалось построить натальную карту. Попробуй позже или проверь данные профиля."
  }
}
```

- Add test that raw sidecar/provider exception text is not exposed.

### B6 — No tests changed for a large backend/frontend feature

Status: BLOCKER

The commit changes DB schema, profile schema, profile writing, natal API, natal service, frontend route, UI components, and contracts. But no test files are changed.

Required tests were explicitly requested in the TZ:

Backend:

- missing gender returns profile incomplete;
- complete profile returns preview;
- sidecar failure returns safe error;
- price is 99900;
- male/female wording;
- calculation stats bucket rules;
- 8 chapters.

Frontend:

- loading / profile incomplete / error / successful preview;
- mini landing first screen;
- CTA disabled and priced at 999 ₽;
- male/female fixtures;
- calculation stats from backend.

Required fix:

- Add backend unit/API tests.
- Add frontend component/page tests.
- Provide command output/counts.

## Major risks / notes

### R1 — `get_preview()` uses transits for the birth date/time

The natal preview calls `get_transits()` using the birth date and birth time, then normalizes natal + transits and scores those signals.

This may be technically convenient, but product-wise it is unclear: natal preview should be based on the natal chart, not a transit snapshot at birth unless explicitly intended and documented.

Required clarification:

- If scoring requires transit-shaped input, document why this is safe.
- Otherwise use natal-only scoring or a dedicated natal signal builder.

### R2 — Old `get_natal_reading()` still returns hardcoded generic natal content

The new preview avoids LLM and uses real chart data, which is good. But the old overview/section endpoints still return generic hardcoded content. This is out of scope for this packet, but keep it away from the new preview UI and do not link users into it as paid/full content.

## Verification evidence

Connector-visible CI evidence:

- No GitHub Actions workflow runs were visible for commit `751cb1b92fb9482a54dba8229748f6190ac97081`.
- No combined GitHub status checks were visible for the commit.

Coder/local evidence was not included in the user message.

## Final decision

REJECTED.

The implementation direction is correct: real natal preview endpoint, real mini landing route, profile gender field, disabled 999 ₽ CTA. But it cannot be accepted until the blockers are fixed:

1. implement gender in onboarding;
2. fix profile-incomplete error parsing/contract;
3. render 5–7 spheres and 8 locked chapters;
4. implement calculation stats bucket rules correctly;
5. return safe public errors;
6. add tests.
