# TZ: W-NATAL-PREVIEW-MVP

Date: 2026-06-09
Status: ready for coder
Supersedes for next implementation slice: `docs/17_Natal_landing_and_generation_TZ.md`
Related: `docs/work/2026-06-09_profile_gender_onboarding_TZ.md`, `docs/FAILURE_HANDLING_CANON.md`

## 1. Review of existing natal TZ

The existing `docs/17_Natal_landing_and_generation_TZ.md` has a good product direction:

- free instant natal preview from real calculated data;
- paid full report later;
- 8 report chapters;
- block renderer reuse;
- sectioned LLM generation later.

But it is too broad and has outdated/unsafe parts for the next coder packet:

1. It mixes preview, payment, DB report model, LLM generation, section polling, and paid full report into one wave.
2. It says `price: int = 999` while commenting that price is in kopecks. If price is stored in kopecks, 999 ₽ must be `99900`.
3. It allows skipped/placeholder generated sections on LLM failure. That violates the failure-handling canon: do not show generic successful-looking content when real generation failed.
4. It does not include the new onboarding gender requirement for Russian masculine/feminine wording.
5. It lists advanced inputs such as fixed stars, midpoints, configurations, special points. Coder must use only data actually returned by the current backend/sidecar; no invented preview facts.
6. It has “fallback model” wording. Provider retry is allowed as an internal retry mechanism, but user-facing fallback/placeholder content is not allowed.

Therefore this packet implements the first safe slice: a real natal preview/landing screen, without paid report generation.

## 2. Goal

Create the first usable `/readings/natal` screen:

- based on real user birth data;
- deterministic and instant;
- no LLM required;
- no fake/demo natal payload in production;
- no paid full report yet;
- correct masculine/feminine Russian wording based on onboarding `gender`.

User value:

> “Вот моя карта: Солнце/Луна/ASC, главные акценты, сильные сферы, планеты, и почему это похоже на меня.”

This is trust/personalization layer, not the main monetization loop.

## 3. Product scope for this wave

### In scope

1. Backend endpoint:
   - `GET /api/natal/preview`

2. Frontend route:
   - `/readings/natal`

3. Preview content:
   - hero with name, birth date/place, house system, ASC;
   - highlights strip;
   - top 5–7 life spheres;
   - key planets list;
   - 8 locked full-report chapters;
   - deterministic personal hook from real chart facts;
   - CTA for future full report, not a working payment flow.

4. Gendered wording:
   - `male` → masculine forms;
   - `female` → feminine forms.

5. Tests and guardrails.

### Out of scope

- Real payment.
- Telegram Stars / YooKassa.
- Creating paid `NatalReport` records.
- LLM full natal generation.
- Section polling.
- `/api/natal/generate`.
- `/api/natal/report`.
- `/readings/natal/[section]` full generated section content.
- Regeneration/update purchase.
- Neutral gender option.

## 4. Dependencies

This wave depends on the profile gender field from:

`docs/work/2026-06-09_profile_gender_onboarding_TZ.md`

Coder options:

1. If gender is already merged, use it.
2. If not merged, stop and return dependency blocker instead of silently using a default.

No male/female default may be guessed for old users.

## 5. Backend contract

### 5.1 Endpoint

Add:

`GET /api/natal/preview`

Authentication:

- requires session auth;
- returns only the current user's data.

Profile completeness required:

- birth date;
- birth time if current system requires time for ASC/houses;
- birth latitude;
- birth longitude;
- birth timezone;
- gender: `male|female`.

If profile incomplete:

- return `409 Conflict`;
- payload includes missing fields;
- frontend shows completion CTA;
- do not return demo/mock preview.

Suggested error payload:

```json
{
  "error": "profile_incomplete",
  "missingFields": ["gender", "birthLat", "birthLon"],
  "message": "Нужно дозаполнить профиль, чтобы построить натальную карту."
}
```

### 5.2 NatalPreview response

Add/extend `apps/api/app/schemas/natal.py`:

```python
class NatalPreviewMeta(CamelModel):
    name: str | None
    birth_date: str
    birth_time: str | None
    birth_city: str | None
    house_system: str | None
    asc_sign: str | None
    asc_degree: float | None
    gender: Literal["male", "female"]

class NatalHighlight(CamelModel):
    id: str
    title: str
    value: str
    description: str | None = None

class NatalSpherePreview(CamelModel):
    id: str
    title: str
    score: float
    rank: int
    description: str

class NatalPlanetPreview(CamelModel):
    id: str
    name: str
    sign: str | None
    house: int | None
    score: float | None = None
    description: str

class NatalChapterPreview(CamelModel):
    id: str
    eyebrow: str
    title: str
    locked: bool = True
    description: str

class NatalPreviewRead(CamelModel):
    meta: NatalPreviewMeta
    highlights: list[NatalHighlight]
    spheres: list[NatalSpherePreview]
    planets: list[NatalPlanetPreview]
    chapters: list[NatalChapterPreview]
    personal_hook: str
    full_report_available: bool = False
    full_report_price_kopecks: int = 99900
```

Field names on wire must be camelCase through `CamelModel`.

### 5.3 Backend service

Add or extend `NatalService`:

```python
async def get_preview(user_id: UUID) -> NatalPreviewRead:
    ...
```

Rules:

1. Uses real user profile only.
2. Calls existing SolarSage sidecar/client for natal chart.
3. Reuses existing normalization/scoring where available.
4. Does not call LLM.
5. Does not create paid report rows.
6. Does not use fixture/demo payload in production.
7. If calculation fails, returns a real error, not placeholder data.

### 5.4 Deterministic builders

Add small pure helpers where practical:

```python
def build_natal_highlights(chart, signals, scores, gender) -> list[NatalHighlight]:
    ...

def build_natal_spheres(scores, gender) -> list[NatalSpherePreview]:
    ...

def build_natal_planets(chart, scores, gender) -> list[NatalPlanetPreview]:
    ...

def build_natal_chapters(gender) -> list[NatalChapterPreview]:
    ...

def build_natal_personal_hook(preview, gender) -> str:
    ...
```

These helpers must be deterministic and testable without external calls.

## 6. Gendered Russian wording

Use gender only for grammar, not astrology.

Examples:

For `female`:

- `Из чего ты собрана`
- `Ты можешь быть особенно чувствительна к...`
- `В этой карте ты сильнее всего проявлена через...`

For `male`:

- `Из чего ты собран`
- `Ты можешь быть особенно чувствителен к...`
- `В этой карте ты сильнее всего проявлен через...`

Do not use gender to invent interpretations like “женская энергия” or “мужская энергия”.

## 7. Frontend

### 7.1 Route

Update or create:

`app/(grace)/readings/natal/page.tsx`

States:

1. `loading` — skeleton.
2. `profile_incomplete` — clear CTA to finish profile/onboarding.
3. `error` — calculation/API error, no demo fallback.
4. `preview` — real natal preview.

### 7.2 Components

Allowed/expected files:

```text
components/readings/natal/landing/natal-landing.tsx
components/readings/natal/landing/natal-hero.tsx
components/readings/natal/landing/natal-highlights.tsx
components/readings/natal/landing/natal-spheres-preview.tsx
components/readings/natal/landing/natal-planets-preview.tsx
components/readings/natal/landing/natal-chapters-preview.tsx
components/readings/natal/landing/natal-personal-hook.tsx
components/readings/natal/landing/natal-cta.tsx
lib/api/natal.ts
lib/contracts/natal.ts
```

If the project currently uses `components/grace/readings/...`, follow the existing active path convention and do not create duplicate parallel component trees.

### 7.3 UI composition

Page order:

1. Hero:
   - title: `Натальная карта`;
   - user name if present;
   - birth date/city;
   - ASC sign/degree if available;
   - house system.

2. Highlights:
   - ASC;
   - Moon sign;
   - Sun sign;
   - dominant sphere;
   - strongest visible planet if score is available.

3. Personal hook:
   - 2–4 sentences from deterministic templates;
   - based only on data in preview;
   - gender-correct.

4. Spheres preview:
   - top 5–7 spheres;
   - score/rank;
   - simple life-language descriptions.

5. Planets preview:
   - key planets;
   - sign/house;
   - simple description.

6. Locked chapters:
   - 8 chapters;
   - locked labels;
   - no fake content behind locks.

7. CTA:
   - text: `Полный разбор натальной карты`;
   - price shown: `999 ₽`;
   - button disabled or “скоро”, unless payment is already implemented;
   - no broken payment route.

## 8. Failure handling

Must follow `docs/FAILURE_HANDLING_CANON.md`.

Forbidden:

- if profile missing, returning demo natal data;
- if sidecar fails, showing fake card values;
- if a value is absent, inventing it in text;
- generic placeholder that looks like a successful natal interpretation;
- silently defaulting gender.

Allowed:

- explicit profile incomplete state;
- explicit calculation error state;
- partial preview only if every visible item is marked as computed/available and missing values are not presented as facts.

Recommended user-facing error text:

`Не удалось построить натальную карту. Мы не будем показывать общий текст вместо реального разбора. Попробуй позже или проверь данные профиля.`

## 9. Tests

### Backend

1. `GET /api/natal/preview` requires auth.
2. Incomplete profile returns `409 profile_incomplete` with missing fields.
3. Missing gender returns `409 profile_incomplete`; no default.
4. Complete profile returns preview.
5. Preview endpoint does not call LLM.
6. Sidecar/client failure returns error state/status, no fixture payload.
7. `fullReportPriceKopecks == 99900`.
8. Male profile returns masculine chapter title `Из чего ты собран`.
9. Female profile returns feminine chapter title `Из чего ты собрана`.
10. Pure builders use only provided chart/scoring data.

### Frontend

1. `/readings/natal` renders loading state.
2. `profile_incomplete` renders completion CTA.
3. API error renders honest error state, not demo data.
4. Successful preview renders hero, highlights, spheres, planets, locked chapters, CTA.
5. Male fixture renders masculine title/forms.
6. Female fixture renders feminine title/forms.
7. CTA does not navigate to broken payment route while payment is out of scope.

### Guardrails / grep

Add a small guard if practical:

- no hardcoded natal demo payload in production path;
- no `999` kopeck price for natal full report; expected `99900`;
- no generic natal fallback text like `Эта секция будет обновлена позже` in production preview path.

## 10. Acceptance criteria

- `/readings/natal` is a real working screen, not an in-dev placeholder.
- It uses real calculated user data.
- It works without LLM.
- It does not require payment.
- It does not create paid report rows.
- It handles incomplete profile honestly.
- It handles calculation failure honestly.
- It respects `gender` for masculine/feminine wording.
- It shows `999 ₽` as future full-report price but does not start a broken payment flow.
- Tests pass.
- Existing horary tests and guardrails remain green.

## 11. Expected evidence from coder

Coder must provide:

1. Diff summary.
2. Backend tests count and command output.
3. Frontend tests count and command output.
4. Guardrails output.
5. Screenshot or DOM evidence for female preview.
6. Screenshot or DOM evidence for male preview.
7. Evidence that incomplete profile does not show fake natal data.
8. Evidence that sidecar/API failure does not show fake natal data.
