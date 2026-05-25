---
id: doc-05-api-contracts
status: superseded
wave: W-1.1B
supersedes: doc-05-api-contracts-pre-w11b
source_of_truth: apps/api/app/schemas
last_review: 2026-05-25
---
# 05. API contracts и TodayPayload

> **STATUS: SUPERSEDED (W-1.1B, 2026-05-25).**
>
> The authoritative source of truth for all API payload shapes
> (`TodayPayload`, `CalendarPayload`, `NatalPayload`, `AccessSummary`,
> `ReadingBody`, `ContentAccessState`, errors) is now the Pydantic models
> under **`apps/api/app/schemas/*`**. The TS types in
> `packages/contracts/_generated.ts` are produced from those schemas via
> `pnpm contracts:generate` and re-exported by `packages/contracts/index.ts`.
> Drift between Pydantic and `_generated.ts` fails the W-1.1B drift gate.
>
> Differences vs the text below that you should ignore in favour of the
> Pydantic schemas:
>
> - `contractVersion` is **`number`** (Pydantic `int`), not `string`.
> - `whyThisHappens` is **required** in `TodayPayload`, not optional.
> - `meta.cached` and other client-side bookkeeping fields are **not** part
>   of the contract; they belong to the client adapter.
> - Field naming follows Pydantic JSON aliasing (`why_this_happens` →
>   `whyThisHappens` on the wire); see schemas for the exact mapping.
> - Block discriminator on `WhyBlock` is `kind` (`"paragraph" | "bullets"`),
>   on `NatalBlock` it is `type`. Do not unify them.
>
> This document is retained for **product-history context only**: it
> explains why each field exists and the rationale for the
> backend↔frontend boundary. Do not edit it to reflect schema changes —
> change the Pydantic source instead and regenerate.
>
> **W-1.2 addendum (2026-05-25).** Auth + profile surface added under
> the same Option B SoT. The new wire types live in
> `apps/api/app/schemas/auth.py` and `apps/api/app/schemas/profile.py`
> and ship through the same `_generated.ts` → `packages/contracts/*`
> pipeline as the payloads above. Authoritative endpoints:
>
> - `POST /api/auth/telegram` — body `TelegramAuthRequest`, response
>   `AuthSession`, sets `Set-Cookie: <SESSION_COOKIE_NAME>=<opaque>;
>   HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=<SESSION_TTL>`.
>   Errors: `AuthError` with codes
>   `INVALID_HMAC` / `MISSING_FIELDS` / `MALFORMED_INITDATA` (HTTP 400)
>   and `INITDATA_EXPIRED` / `UNAUTHORIZED` (HTTP 401).
> - `POST /api/auth/logout` — 204; revokes the session row and clears
>   the cookie. Idempotent.
> - `GET /api/profile` — auth required; lazily creates an empty
>   `user_profiles` row, returns `ProfileRead` (`{user_id, first_name,
>   birth: BirthData}`). Privacy: never returns `tg_user_id`,
>   `token_hash`, `init_data`, or the session token.
> - `PUT /api/profile` — auth required; body `ProfileWrite`, response
>   `ProfileRead`. Validators: `birth_lat` ∈ [-90, 90],
>   `birth_lon` ∈ [-180, 180], `birth_lat`/`birth_lon` go together
>   or both stay null, `birth_tz` ∈ `zoneinfo.available_timezones()`,
>   `birthday >= 1900-01-01`.
>
> Session mechanism is fixed by `M-AUTH-TG = Option A` (opaque cookie
> + server-side `sessions` table; see `grace/packets/W-1.2.md`).
> Field-level details and validators are normative in the Pydantic
> source — do not duplicate them here.

## Роль документа

Фиксирует стабильные API-контракты между backend и frontend для MVP.

Главная задача — сделать так, чтобы расчётную модель можно было менять без переписывания фронта.

## Главный принцип

Фронт не должен знать расчётную кухню.

Фронт не получает raw SolarSage, все транзиты, аспекты, dignity/lots/midpoints, внутренний scoring, internal ranking или LLM prompt context.

Фронт получает стабильный продуктовый payload.

## Versioning

```ts
export type PayloadMeta = {
  contractVersion: string
  calculationVersion?: string
  normalizationVersion?: string
  scoringVersion?: string
  interpretationVersion?: string
  promptVersion?: string
  generatedAt: string
  cached: boolean
}
```

`contractVersion` меняется редко, расчётные и prompt-версии могут меняться чаще.

## 1. TodayPayload

Endpoint:

```http
GET /api/day/:date
```

```ts
export type TodayPayload = {
  meta: PayloadMeta
  date: string
  title: string
  subtitle?: string
  headline: string
  access: AccessState
  dayStatus: DayStatus
  dayQuality?: DayQuality
  topFlags: TopFlag[]
  reading: DayReading
  whyThisHappens?: WhyThisHappens
  weekStrip: WeekStripDay[]
  actions?: TodayAction[]
}
```

## 2. AccessState

```ts
export type AccessState = {
  state: "full" | "preview" | "locked"
  reason?:
    | "active_referral_days"
    | "active_subscription"
    | "expired_access"
    | "outside_access_window"
    | "not_onboarded"
  accessUntil?: string
  referralDaysLeft?: number
  subscriptionActive?: boolean
  lock?: SoftLock
}
```

`full` — полный день. `preview` — дата, headline, часть флагов, teaser, soft lock. `locked` — если даже preview не доступен; для MVP чаще достаточно `preview`.

## 3. SoftLock

```ts
export type SoftLock = {
  title: string
  text: string
  primaryCta: { label: string; action: "subscribe" | "open_paywall" }
  secondaryCta?: { label: string; action: "invite_friend" | "open_referral" }
}
```

Пример:

```json
{
  "title": "Этот день уже рассчитан для тебя",
  "text": "Полный разбор и объяснение доступны по подписке или приглашению друга.",
  "primaryCta": { "label": "Оформить подписку", "action": "subscribe" },
  "secondaryCta": { "label": "Пригласить друга", "action": "invite_friend" }
}
```

## 4. DayStatus и DayQuality

```ts
export type DayStatus = "supportive" | "steady" | "tense"
```

UI labels:

- supportive → поддерживающий
- steady → ровный
- tense → напряжённый

```ts
export type DayQuality =
  | "supportive"
  | "steady"
  | "quiet"
  | "tense"
  | "high_contrast"
  | "intense"
  | "peak"
  | "releasing"
```

## 5. TopFlag

```ts
export type TopFlag = {
  id: string
  type:
    | "moon_voc"
    | "moon_phase"
    | "moon_sign_change"
    | "retrograde"
    | "station"
    | "eclipse"
    | "ingress"
    | "personal_transit"
    | "active_house"
    | "period_focus"
    | "custom"
  title: string
  summary: string
  severity?: "info" | "notice" | "important"
  timeWindow?: { startsAt?: string; endsAt?: string; label?: string }
  hint: TopFlagHint
}

export type TopFlagHint = {
  meaning: string
  whyToday: string
  howItFeels: string
}
```

## 6. DayReading

```ts
export type DayReading = {
  paragraphs: string[]
  teaser?: string
}
```

## 7. WhyThisHappens

```ts
export type WhyThisHappens = {
  initiallyOpen?: boolean
  sections: WhySection[]
}

export type WhySection = {
  id: string
  title: string
  paragraphs: string[]
  bullets?: string[]
}
```

Рекомендуемые section ids:

```ts
export type WhySectionId =
  | "main_theme"
  | "daily_layer"
  | "personal_activation"
  | "period_background"
  | "amplifiers"
  | "softeners"
  | "manifestation_zones"
  | "astrological_meaning"
  | "practical_meaning"
```

## 8. WeekStripDay

```ts
export type WeekStripDay = {
  date: string
  weekdayLabel: string
  dayNumber: string
  status: DayStatus
  isActive: boolean
  access: "full" | "preview" | "locked"
}
```

## 9. TodayAction

```ts
export type TodayAction = {
  id: string
  label: string
  type: "primary" | "secondary"
  action:
    | "open_why"
    | "subscribe"
    | "invite_friend"
    | "open_calendar"
    | "open_profile"
}
```

## 10. CalendarPayload

Endpoint:

```http
GET /api/calendar?month=2026-04
```

```ts
export type CalendarPayload = {
  meta: PayloadMeta
  month: string
  title: string
  allowedRange: { from: string; to: string }
  days: CalendarDay[]
}

export type CalendarDay = {
  date: string
  dayNumber: string
  isCurrentMonth: boolean
  isToday: boolean
  isSelected?: boolean
  status?: DayStatus
  access: "full" | "preview" | "locked" | "disabled"
}
```

Правила: календарь показывает прошлый/текущий/следующий месяц, disabled дни не кликабельны, tap по доступному или locked дню открывает `/day/:date`.

## 11. ProfilePayload

```ts
export type ProfilePayload = {
  meta: PayloadMeta
  telegramUser: { id: string; name: string; username?: string; avatarUrl?: string }
  access: ProfileAccess
  referral: ReferralInfo
  horary: HoraryInfo
  birthData: BirthData
}

export type ProfileAccess = {
  state: "active" | "expired" | "none"
  activeUntil?: string
  referralDaysLeft: number
  subscriptionActive: boolean
  subscriptionStartsAfterReferralDays?: boolean
  label: string
  description: string
}

export type ReferralInfo = {
  inviteUrl: string
  invitedCount: number
  daysEarned: number
  title: string
  description: string
}

export type HoraryInfo = {
  bonusCredits: number
  paidCredits: number
  nextBonusAt?: string
  description: string
}

export type BirthData = {
  birthDate: string
  birthTime?: string
  birthPlace: LocationValue
  currentLocation: LocationValue
  birthdayLocation?: LocationValue
}

export type LocationValue = {
  name: string
  country?: string
  latitude?: number
  longitude?: number
  timezone?: string
}
```

## 12. ReadingsPayload

```ts
export type ReadingsPayload = {
  meta: PayloadMeta
  sections: ReadingSection[]
}

export type ReadingSection = {
  title: string
  items: ReadingCard[]
}

export type ReadingCard = {
  id: string
  title: string
  description: string
  status: "available" | "locked" | "in_development"
  ctaLabel?: string
  route?: string
}
```

MVP cards: natal chart, horary. In development: month, year, synastry, thematic readings, history/archive.

## 13. Error contract

```ts
export type ApiError = {
  error: {
    code: string
    message: string
    details?: unknown
  }
}
```

Common codes:

- `NOT_ONBOARDED`
- `INVALID_DATE`
- `ACCESS_DENIED`
- `CALCULATION_FAILED`
- `LLM_GENERATION_FAILED`
- `PROFILE_INCOMPLETE`
- `UNAUTHORIZED`

## 14. Frontend rules

Фронт рендерит payload, не интерпретирует астрологию, не выбирает top flags, не считает day status, не пересобирает why sections.

## 15. Backend rules

Backend валидирует пользователя, проверяет доступ, считает/достаёт кэш, собирает TodayPayload, не отдаёт raw SolarSage на фронт.

## Главное решение

Стабилизируем не расчётн��ю формулу, а форму выдачи. Расчёт, скоринг, prompt и LLM можно менять, если `TodayPayload` остаётся совместимым.
