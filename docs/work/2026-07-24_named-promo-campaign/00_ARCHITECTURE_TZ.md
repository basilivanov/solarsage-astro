# Архитектурное ТЗ: именованные promo campaigns через Telegram Mini App deep link

Дата: 2026-07-24

Статус: ready for implementation by small coder-loop slices

Роль постановщика: архитектор/ревьюер

Роль исполнителя: кодер в `tmux astro2`, по одному numbered slice за итерацию

## 1. Цель

Добавить в SolarSage Astro универсальные именованные promo campaigns. Кампания
не является специальной сущностью «для тестеров»: владелец при создании задаёт
произвольное безопасное `display_name`, например «Пакет тестера», «Для друзей»
или «Летний доступ». Confirmation sheet показывает это название и фактический
состав конкретной кампании.

Основной MVP-вход:

```text
https://t.me/AstroGrace_Bot/app?startapp=m7q4n9x2r5kd
```

Кампания активируется только после Telegram auth, проверки профиля и явного
нажатия «Активировать». Выдача доступа, кредитов, natal entitlement,
redemption-row и счётчика выполняется одной транзакцией.

## 2. Зафиксированные продуктовые решения

1. Кампания универсальная и имеет обязательное `display_name`; слово
   «тестер» не должно быть зашито в модели, API, UI или бизнес-логику.
2. Confirmation sheet:
   - eyebrow: `Промокод`;
   - title: server-owned `display_name`;
   - текст: `По промокоду вам доступно:`;
   - динамический список только реально включённых преимуществ;
   - primary CTA: `Активировать`;
   - secondary CTA: `Не сейчас`.
3. Значения по умолчанию при создании кампании:
   - activation window: 7 суток;
   - access: 30 календарных дней;
   - bonus credits: 50;
   - unlock natal: `true`.
4. Доступ не должен теряться при наличии старого access ledger. Promo-период
   начинается с `max(UTC today, latest AccessLedger.end_date + 1 day)`, то есть
   30 дней добавляются после уже выданного доступа. Это совпадает с текущим
   billing promise «no lost days».
5. Gift credits доступны сразу после redemption и истекают в начало суток UTC,
   следующих за `AccessLedger.end_date`. Таким образом последний inclusive day
   доступа остаётся полноценным днём использования кредитов.
6. Повторный запрос идемпотентен по эффектам: новых grants/counter increment не
   возникает; HTTP-ответ — `409 ALREADY_REDEEMED`.
7. После изменения birth profile существующий natal `Purchase` остаётся
   привязан к старому `context_hash`, как и оплаченный entitlement. Promo не
   выдаёт entitlement повторно для нового профиля.
8. Закрытие sheet через `Не сейчас` очищает pending token из текущего
   `sessionStorage`. Для повторного показа пользователь снова открывает deep
   link. Network/transient error token не очищает.
9. Для кампании с `unlock_natal=true` неизвестное время рождения не считается
   заполненным профилем. Promo-onboarding обязан открыть уже заполненный профиль
   в режиме `requiredFor=promoNatal`, объяснить необходимость точного времени и
   не предлагать вариант «Не знаю точное время». Обычный onboarding и его
   optional-time semantics глобально не ужесточаются.
   Для кампании с `unlock_natal=false` достаточно base birth profile:
   `birthday`, `birth_city`, valid `gender`; exact time не требуется.
10. `ALREADY_REDEEMED` остаётся стабильным HTTP 409, но frontend трактует его
    как восстановленный successful outcome: очищает pending token и обновляет
    access/quota. Это закрывает потерю первого HTTP 200 после server commit.
11. Gift credits доступны немедленно, даже если promo access отложен после
    старого ledger. Их expiry всё равно совпадает с концом promo access. Это
    осознанная benefit-семантика, а не ровно 30 суток жизни credit row.

## 3. Найденное исходное состояние

### 3.1. Auth и referral

- `hooks/use-telegram-auth.ts` сейчас считает referral любое непустое
  `start_param`, сохраняет его в `localStorage`, отправляет в
  `/api/referral/claim` и даже пишет raw value в legacy log.
- Этот же hook пишет fragment `initData` через `authKey.slice(...)`; это также
  нужно убрать как ненужную утечку auth material.
- `apps/api/app/api/referral.py` фактически принимает только числовой Telegram
  `tg_user_id` через `int(referrer_code)`. Следовательно канонический referral
  contract уже числовой, а frontend tests с `ref123`/`ref789` неверны.
- Telegram auth backend логирует только boolean `has_start_param`, raw param не
  нужен и не должен появиться в новых событиях.
- Production Nginx сейчас логирует request URI и same-origin Referer. Telegram
  реально добавляет `tgWebAppStartParam` в URL, поэтому opaque token утечёт ещё
  до выполнения JavaScript. Privacy fix Nginx и browser URL является
  обязательным compatibility floor, а не опциональной частью rate limiter.

### 3.2. Profile/onboarding

- `UserProfile.is_onboarded` выставляется уже при наличии `birthday`,
  `birth_city`, `gender`.
- Канонический natal context требует более строгий набор из
  `NatalContextService.REQUIRED_PROFILE_FIELDS`:
  `birthday`, `birth_time`, `birth_lat`, `birth_lon`, `birth_tz`, `gender`.
- Поэтому promo preview/redeem не может доверять только сохранённому boolean
  `is_onboarded`; сервер вычисляет base readiness из реальных полей. Если
  `unlock_natal=true`, поверх base contract используется natal-ready проверка,
  которая защищает построение `context_hash`.
- Текущий onboarding разрешает `birth_time=unknown` и всё равно завершается.
  Простой redirect в тот же flow создаст бесконечный цикл. Нужен отдельный
  promo-natal mode с prefilled existing profile и обязательным exact time.
- `app/(grace)/layout.tsx` уже является общей post-auth точкой, а onboarding
  после completion делает `router.replace('/day/...')`. Promo gate можно
  смонтировать в authenticated branch и повторно resolve-ить pending offer при
  смене pathname после onboarding.

### 3.3. Access, credits и natal

- `AccessService.grant_subscription(..., commit=False)` уже умеет stage/flush
  grant без отдельного commit, но сейчас не возвращает созданный
  `AccessLedger`; promo redemption нужен его ID.
- `BillingService` уже откладывает новый paid access после latest ledger end.
  Promo использует ту же семантику, но не создаёт `Subscription`.
- `HoraryCredit.source='gift'` уже разрешён. Все non-paid/non-weekly credits
  входят в bonus balance и сортируются по ближайшему `expires_at`.
- Election уже использует `HoraryCreditService.select_spendable_credit`, значит
  promo gift автоматически входит в общий pool. Однако election вызывает
  выбор без `FOR UPDATE`; это отдельный маленький hardening slice.
- `Purchase` допускает `payment_id=NULL`, а partial unique index
  `uq_purchases_natal_entitlement` запрещает два fulfilled
  `natal_full_report` для одного `(user_id, context_hash)`.
- `BillingService.has_natal_entitlement` проверяет статусы `succeeded` и
  `delivered`. Promo создаёт `delivered` или переиспользует существующую row.

### 3.4. Runtime и rate limiting

- В проекте нет Redis/SlowAPI/general application rate limiter.
- Canonical production имеет один Nginx entrypoint и один Uvicorn worker.
- Sole limiter по `$binary_remote_addr` неприемлем: разные Telegram users могут
  находиться за одним mobile carrier NAT.
- Для MVP primary limiter — bounded in-process bucket по authenticated internal
  `user_id` в единственном Uvicorn worker. Nginx остаётся только loose
  volumetric IP ceiling. До запуска нескольких workers primary limiter нужно
  перенести в shared store/DB bucket.
- Pydantic/FastAPI default 422 включает raw invalid input. Promo token request
  требует route-scoped redaction: malformed body никогда не возвращает token в
  validation response.

## 4. Целевой flow

```text
Telegram start_param
        |
        v
pure classifier
  | digits only        | valid opaque token       | other
  v                    v                          v
referral claim     sessionStorage pending       ignore
                         |
                  Telegram auth complete
                         |
                  POST /api/promo/preview
                    | invalid/closed -> clear/ignore
                    | profile incomplete -> /onboarding
                    | profile complete
                    v
               confirmation sheet
                    | Не сейчас -> clear, no grant
                    | Активировать
                    v
                  POST /api/promo/redeem
                         |
          locked campaign transaction + grants
                         |
             success/ALREADY -> clear + reload data
```

`preview` необходим: opaque token намеренно не содержит display name или
benefit config, а sheet должен показывать server-owned актуальные значения до
redemption. Использовать GET/query parameter нельзя: token попадёт в URL и
access logs.

## 5. Start parameter contract

### 5.1. Opaque token

Allowed alphabet:

```text
letters: abcdefghjkmnpqrstuvwxyz
digits:  23456789
```

Canonical regex:

```regex
^(?=.{12,16}$)(?=.*[a-hj-km-np-z])[a-hj-km-np-z2-9]+$
```

Инварианты:

- только lowercase ASCII letters и digits;
- длина 12–16, CLI default 12;
- исключены `0/o`, `1/l/i`;
- есть хотя бы одна буква, поэтому token не пересекается с referral;
- никаких `promo`, `beta`, дат, имени проекта или campaign name;
- token генерируется только `secrets`, пользовательский `--token` CLI запрещён;
- SHA-256 считается над exact ASCII token без trim/lowercase normalization.

### 5.2. Closed routing

```text
/^\d+$/                                               -> referral
/^(?=.{12,16}$)(?=.*[a-hj-km-np-z])[a-hj-km-np-z2-9]+$/ -> promo
anything else                                         -> ignored
```

Порядок важен: сначала digits-only referral, затем opaque promo. Promo regex и
так требует букву, но explicit order делает контракт читаемым и тестируемым.

Referral может сохранять только уже классифицированный numeric code в текущем
`localStorage` key. Promo token разрешён только в
`sessionStorage['__astro_pending_promo_token']`. Старый persisted non-numeric
referral value после обновления удаляется и не отправляется ни в один endpoint.

## 6. Data model

### 6.1. `PromoCampaign`

| Field | Type | Contract |
|---|---|---|
| `id` | UUID PK | operator/API-internal identity |
| `display_name` | varchar(120) | required, trimmed, 1–120 chars; returned to sheet, never logged |
| `code_hash` | varchar(64) | lowercase SHA-256 hex, UNIQUE; raw token absent |
| `active` | bool | kill switch, default true at CLI create |
| `activation_starts_at` | timestamptz | inclusive |
| `activation_ends_at` | timestamptz | exclusive |
| `max_redemptions` | int | required, `> 0` |
| `redemptions_used` | int | default 0, `0 <= used <= max` |
| `access_days` | int | default 30, `>= 0` |
| `bonus_credits` | int | default 50, `>= 0` |
| `unlock_natal` | bool | default true |
| `created_at`, `updated_at` | timestamptz | operational audit |

DB checks:

```text
activation_ends_at > activation_starts_at
max_redemptions > 0
0 <= redemptions_used <= max_redemptions
access_days >= 0
bonus_credits >= 0
bonus_credits = 0 OR access_days > 0
access_days > 0 OR bonus_credits > 0 OR unlock_natal = true
```

Последние два checks позволяют generic natal-only/access-only campaigns, но не
позволяют бессмысленную кампанию и credits без даты истечения.

### 6.2. `PromoRedemption`

| Field | Type | Contract |
|---|---|---|
| `id` | UUID PK | audit identity |
| `campaign_id` | UUID FK | campaign |
| `user_id` | UUID FK | internal user, не Telegram ID |
| `redeemed_at` | timestamptz | UTC grant time |
| `access_ledger_id` | UUID FK nullable | null only when `access_days=0` |
| `credit_id` | UUID FK nullable | null only when `bonus_credits=0` |
| `natal_purchase_id` | UUID FK nullable | existing or newly created entitlement; null if disabled |

Обязательные ограничения и индексы:

```text
UNIQUE(campaign_id, user_id)
INDEX(campaign_id, redeemed_at)
INDEX(user_id)
```

Grant FKs используют `ON DELETE SET NULL`; redemption остаётся audit record.
Campaign не удаляется CLI-командой, только disabled. User FK следует текущей
repo policy (`CASCADE`) и не является механизмом возврата campaign capacity.

Migration: `0024_named_promo_campaign`, down revision `0023_election`.

## 7. Server profile readiness

Добавить два public pure readiness contract:

```py
missing_onboarding_fields(profile) -> list[str]
NatalContextService.missing_profile_fields(profile) -> list[str]
NatalContextService.is_profile_complete(profile) -> bool
```

Base helper владеет `birthday`, `birth_city`, valid `gender`; существующий
`ProfileService.update_profile` использует его при выставлении `is_onboarded`.
Natal private validation делегирует strict helper (`birthday`, exact
`birth_time`, coordinates, timezone, gender), чтобы promo, natal
preview/generation и context hash не получили разные определения полноты.

Campaign readiness:

```text
unlock_natal=false -> base readiness
unlock_natal=true  -> natal readiness
```

Promo preview возвращает `profileComplete: false`; redemption при stale/race
состоянии возвращает `409 PROFILE_INCOMPLETE`. Ни один из этих путей не создаёт
redemption/grants и не меняет counter.

`profileComplete=false` не означает redirect в обычный пустой onboarding.
Frontend передаёт safe mode `requiredFor=promoNatal` либо
`requiredFor=promoBase` (без token в URL), загружает текущий профиль, просит
дозаполнить соответствующие fields и после успешного PUT возвращается на day
route. Pending token остаётся только в sessionStorage. Если пользователь не
знает точное время, невозможна только активация кампании с
`unlock_natal=true`; campaign не расходуется.

## 8. HTTP contract

Оба endpoint session-authenticated и принимают JSON body с одним `SecretStr`
token. Public OpenAPI schema отмечает поле `writeOnly/password`, но не ставит
Pydantic `min_length/max_length/pattern`: default validation error эхоирует raw
`input`. Length/alphabet проверяет domain service, а malformed JSON/type
перехватывает route-local safe parser/handler и возвращает `400 INVALID_CODE`
без raw input. Responses имеют `Cache-Control: no-store` и никогда не echo
token, hash или campaign ID.

### 8.1. `POST /api/promo/preview`

Request:

```json
{"token":"m7q4n9x2r5kd"}
```

Success `200`:

```json
{
  "offer": {
    "displayName": "Пакет тестера",
    "accessDays": 30,
    "bonusCredits": 50,
    "unlockNatal": true
  },
  "profileComplete": true
}
```

Preview проверяет format/hash, active, start/end, capacity и already redeemed,
но ничего не блокирует надолго и не резервирует slot. Redeem всегда повторяет
все проверки под lock.

### 8.2. `POST /api/promo/redeem`

Request shape тот же. Success `200`:

```json
{
  "status": "redeemed",
  "offer": {
    "displayName": "Пакет тестера",
    "accessDays": 30,
    "bonusCredits": 50,
    "unlockNatal": true
  },
  "grants": {
    "accessStartsAt": "2026-07-25",
    "accessUntil": "2026-08-23",
    "bonusCredits": 50,
    "bonusCreditsExpiresAt": "2026-08-24T00:00:00Z",
    "natalUnlocked": true,
    "natalAlreadyOwned": false
  }
}
```

Dates are illustrative; server UTC clock is authoritative.

### 8.3. Stable errors

Shape:

```json
{"detail":{"code":"CAMPAIGN_FULL","message":"Все активации уже использованы."}}
```

| HTTP | Code | Meaning |
|---|---|---|
| 400 | `INVALID_CODE` | malformed, unknown, inactive or not-yet-started |
| 410 | `CAMPAIGN_EXPIRED` | `now >= activation_ends_at` |
| 409 | `CAMPAIGN_FULL` | counter reached max |
| 409 | `ALREADY_REDEEMED` | natural idempotency key already exists |
| 409 | `PROFILE_INCOMPLETE` | natal-ready fields absent at redeem |
| 429 | `RATE_LIMITED` | technical additive code required by rate limit |

`active=false` maps to `INVALID_CODE`, чтобы public API не раскрывал наличие
disabled campaign. `now < starts_at` тоже `INVALID_CODE`; отдельный oracle для
будущих кампаний не нужен.

## 9. Atomic redemption algorithm

Одна `AsyncSession`, один final commit:

```text
1. validate opaque format; SHA-256 in memory
2. SELECT PromoCampaign WHERE code_hash=:hash FOR UPDATE
3. check existing PromoRedemption(campaign,user) -> ALREADY even if campaign
   was disabled/expired after the original successful commit
4. validate active/window for users without redemption
5. SELECT User WHERE id=:user_id FOR UPDATE (campaign-before-user lock order)
6. validate server profile completeness
7. check redemptions_used < max_redemptions
8. compute access start after latest AccessLedger end
9. stage AccessLedger(entry_type=subscription), flush -> id
10. stage HoraryCredit(source=gift, used_amount=0, expires_at=access end + 1d)
11. resolve current natal context_hash
12. reuse fulfilled Purchase or insert delivered Purchase(payment_id=NULL)
13. insert PromoRedemption with grant ids
14. redemptions_used += 1
15. flush constraints
16. COMMIT exactly once
```

На любой exception — full rollback. Grant helpers, natal helper и route не
имеют скрытых commits.

Campaign row lock сериализует capacity и duplicate attempts для одной
campaign. `UNIQUE(campaign_id,user_id)` остаётся final DB guard. Возможную гонку
с параллельной YooKassa выдачей того же natal entitlement закрывает partial
unique index: natal insert выполняется в savepoint; при conflict используется
уже committed entitlement, не дублируется весь grant. Если dialect/savepoint
реализация не позволяет безопасно продолжить, допустим полный rollback и один
bounded service retry; частичный commit запрещён.

User row lock сериализует additive access calculation между разными promo
campaigns одного пользователя. Без него две campaign rows не конфликтуют и
обе транзакции могут выбрать один и тот же latest AccessLedger end.

`promo.redemption_succeeded` пишется только после успешного final commit.
Unexpected exception сначала rollback-ится, затем пишет
`promo.redemption_failed` с safe error kind/campaign ID и re-raise-ится. Нельзя
использовать `NatalContextService.get_or_build_natal_context`: он имеет commits
и sidecar effects; разрешён только pure `compute_profile_hash` после проверки
профиля.

Kill switch ordering: если redeem уже держит campaign row lock, он может
завершиться раньше ожидающей disable-команды. После commit `active=false` ни
один новый lock-holder не получит grants. Уже выданные grants не отзываются.
Повтор уже redeemed user возвращает ALREADY и после disable/expiry; это только
recovery signal, новых grants/counter не создаёт.

## 10. Grants

### 10.1. Access

- Existing `AccessLedger`, `entry_type='subscription'`.
- Не создавать `Subscription`, `Payment`, YooKassa idempotency или enrollment.
- `start_date` — первый UTC day после latest existing ledger end, минимум today.
- `end_date = start_date + access_days - 1` inclusive.
- Каждый campaign redemption имеет собственную ledger row; global dedupe по
  другим кампаниям не выполняется.

### 10.2. Bonus credits

- Existing `HoraryCredit`.
- `source='gift'`, `amount=campaign.bonus_credits`, `used_amount=0`.
- `access_week_start/access_week_end=NULL`.
- `expires_at = UTC midnight(end_date + 1 day)`.
- `metadata_json` содержит только safe internal provenance, например
  `{"grant_type":"promo","campaign_id":"<uuid>"}`; token/name отсутствуют.
- Existing horary and election selection consume the same row; no separate
  election balance is introduced.

### 10.3. Natal

- Canonical `NatalContextService.compute_profile_hash(profile)` after strict
  completeness check.
- Existing fulfilled entitlement for `(user, context_hash)` is reused and its
  ID записывается в redemption.
- Otherwise create:

```text
product_slug = natal_full_report
status = delivered
payment_id = NULL
context_hash = current profile hash
horary_quota_added = NULL
```

- Product catalog row `natal_full_report` must exist; absence is internal
  invariant failure and rolls back the entire redemption.

## 11. Frontend ownership

### 11.1. Pure classifier

Создать pure start-param module. `useTelegramAuth` после successful auth:

- numeric -> existing referral flow;
- opaque -> write session pending token, never call referral;
- ignored -> no storage/network;
- no raw value in logger;
- no initData fragment in logger;
- old invalid referral value in localStorage is removed.

### 11.2. Promo API client

`lib/api/promo.ts` uses `instrumentedFetch` with safe operations and templates:

```text
promo.preview   POST /api/promo/preview
promo.redeem    POST /api/promo/redeem
```

Request body is never logged by the wrapper. Generated OpenAPI/Zod schemas are
the only wire source of truth. `PromoApiError` exposes only status, typed code
and safe message; request/token is not attached to Error.

### 11.3. Gate and onboarding

`PromoCampaignGate` mounts once in authenticated Grace layout, including while
the onboarding route renders. Token is read from sessionStorage just-in-time
for preview/redeem and is never stored in React state, props or DOM. React state
contains only safe `PromoOffer` and phase.

Rules:

- while pathname is onboarding: do not show sheet;
- preview `profileComplete=false`: retain session token and route to
  `/onboarding?requiredFor=promoNatal` when `offer.unlockNatal=true`, otherwise
  `/onboarding?requiredFor=promoBase`;
- when pathname leaves onboarding: preview again, then show sheet;
- redeem `PROFILE_INCOMPLETE`: retain token and route to the same mode derived
  from safe offer config;
- success: clear token, show success/close, then hard reload once so access,
  day and quota clients refetch from the authenticated backend;
- `ALREADY_REDEEMED`: тот же completed path, что success — clear + ровно один
  reload/refetch, а не terminal error;
- `Не сейчас`: clear token, close, no request;
- terminal invalid/expired/full: clear token;
- transient fetch/5xx: retain token and provide Retry.

Storage failure is fail-closed for promo intent but must not break auth.

### 11.4. Semantic UI/test contract

Root:

```tsx
<section
  role="dialog"
  aria-modal="true"
  data-testid="promo-confirmation-sheet"
  data-state="ready|redeeming|error|success"
>
```

Required stable elements:

```text
promo-offer-name
promo-benefits
promo-benefit-access       only if accessDays > 0
promo-benefit-credits      only if bonusCredits > 0
promo-benefit-natal        only if unlockNatal
promo-activate             real button, disabled/aria-busy while redeeming
promo-dismiss              real button
promo-error                role=alert
```

Exact content pattern:

```text
Промокод
{displayName}
По промокоду вам доступно:
{N} дней полного доступа
{N} бонусных вопросов
Полный натальный разбор
[Активировать]
[Не сейчас]
```

Pluralization must be normal Russian UI pluralization, not string snapshots in
business tests. Dynamic name is escaped by React and never used as selector.

## 12. Admin CLI

Canonical invocation inside API image/container:

```bash
python -m app.cli.promo_campaign create \
  --name "Пакет тестера" \
  --max-redemptions 100

python -m app.cli.promo_campaign status --campaign-id <uuid>
python -m app.cli.promo_campaign list-redemptions --campaign-id <uuid> --limit 100
python -m app.cli.promo_campaign disable --campaign-id <uuid>
```

Optional create flags:

```text
--starts-at <ISO UTC>
--activation-days 7
--access-days 30
--bonus-credits 50
--no-unlock-natal
--token-length 12  # 12..16 only
```

`--starts-at` принимает только timezone-aware RFC3339 (`Z` или explicit
offset). Naive datetime отклоняется с non-zero exit; внутри всё приводится к
UTC. CLI create дополнительно показывает worst-case totals:
`max_redemptions * bonus_credits`, maximum access grants и natal unlock count.

CLI create генерирует token, сохраняет только hash и выводит JSON с
`campaignId`, `token`, `deepLink`, window и benefits ровно один раз. Потерянный
token нельзя восстановить; нужно создать новую campaign. Никакая другая
команда token не принимает и не выводит. Status/list/disable работают только
по campaign UUID. `list-redemptions` не показывает Telegram ID/profile data —
только internal user UUID, timestamp и grant IDs.

`disable` идемпотентен; второй вызов возвращает already disabled с exit 0.
Не добавлять admin UI.

## 13. Rate limit и transport privacy

### 13.1. Application limiter

- authenticated key: internal `user_id`, не IP/session token;
- общий bucket для preview+redeem: 10 attempts / 10 minutes;
- bounded TTL/LRU storage, максимум 10 000 keys, expired keys pruning;
- один valid flow использует два attempts;
- overflow -> `429 RATE_LIMITED`, safe `Retry-After`, token отсутствует;
- limiter выполняется до campaign hash lookup, но после session auth;
- restart сбрасывает bucket — допустимо при высокой token entropy и single
  worker MVP, явно не является distributed guarantee.

### 13.2. Nginx volumetric ceiling

В `infra/nginx/astro.vasiliy-ivanov.ru.conf`:

- `limit_req_zone` в http context, key `$binary_remote_addr`;
- отдельный exact/anchored location только для
  `/api/promo/preview` и `/api/promo/redeem`;
- loose ceiling `120 requests/minute`, burst 60, `nodelay`; он защищает ingress,
  но не реализует per-user product limit;
- HTTP 429 JSON с `detail.code=RATE_LIMITED`;
- generic `/api/` proxy semantics/headers/cookies сохраняются;
- token не попадает в URI, error log или custom access fields.

### 13.3. Start-param privacy

До распространения первого deep link:

- site access log format использует method + `$uri` без args, `$request_uri`
  и raw `$request`;
- Referer либо исключён из log format, либо response policy изменена на
  `strict-origin`, чтобы same-origin static/API requests не повторяли query;
- frontend после классификации удаляет только `tgWebAppStartParam` из visible
  URL через `history.replaceState`, сохраняя остальные safe query params;
- synthetic canary token отсутствует в Nginx access/error, frontend shipper и
  API logs;
- privacy config после запуска ссылок не откатывается.

Repo config не попадает в OCI app deploy автоматически. Rollout имеет отдельный
installed-config gate: remote hash, `nginx -t`, reload и `nginx -T` proof.

## 14. Logging и privacy

Добавить в closed registry во всех трёх sources:

```text
promo.offer_viewed
promo.redemption_succeeded
promo.redemption_rejected
promo.redemption_failed
promo.campaign_created
promo.campaign_disabled
```

Allowed safe payload fields:

```text
campaign_id, error_code, access_days, bonus_credits, unlock_natal,
natal_already_owned, redemptions_used, max_redemptions, error_kind
```

Never log:

```text
raw token, start_param, code_hash, display_name, initData,
request body, response body, user profile/birth data, Telegram ID
```

Unknown-code rejection may log only `error_code=INVALID_CODE`. User identity is
represented only by existing bound `user_id_hash` context.

## 15. Test strategy

Required coverage by the numbered slices:

1. Pure classifier matrix and auth hook storage/network/log privacy.
2. Model constraints, unique campaign/user and Alembic round trip.
3. Access grant returns row and defers after latest access.
4. Promo completeness equals natal completeness.
5. Closed event registry parity.
6. Service happy path and every rejection code.
7. Atomic rollback on failure; no partial grants/counter.
8. Duplicate retry, capacity boundary and existing natal entitlement reuse.
9. API auth, no-store, safe errors and no token echo.
10. Generated OpenAPI/Zod drift gate and frontend validation.
11. Sheet semantic DOM contract and dynamic benefits/name.
12. sessionStorage-only onboarding roundtrip and terminal/transient cleanup.
13. CLI generation/one-time output/status/list/disable.
14. Per-user limiter, loose Nginx ceiling, query/referrer-free transport logs.
15. Gift credit consumed by both horary/election; election uses row lock.
16. Promo access не отображается как оплаченная recurring subscription.
17. Lost-200 recovery через `ALREADY_REDEEMED`.
18. Promo-specific onboarding exact-time path без redirect loop.

SQLite unit tests prove business behavior and unique constraints. A final
PostgreSQL acceptance must additionally prove two concurrent redeems against a
one-slot campaign produce exactly one redemption, one grant set and counter=1;
SQLite silently ignores `FOR UPDATE` and не является достаточным concurrency
proof.

## 16. Rollout and rollback

Rollout order:

1. Deploy и закрепить compatibility floor: safe start-param classifier без
   promo UI; opaque token никогда не referral/localStorage/log.
2. Установить Nginx query/referrer-free logging; remote hash + `nginx -t`.
3. migration + backend model/service/API + per-user limiter;
4. API contract generation;
5. CLI;
6. frontend client/sheet/gate/promo-onboarding/access copy;
7. loose Nginx volumetric limiter;
8. PostgreSQL concurrency acceptance и production smoke;
9. создать canary campaign `max_redemptions <= 5`;
10. только после наблюдения распространять основной deep link.

Frontend can deploy after backend. Backend can deploy before frontend without
effect because no campaign token is auto-redeemed. Migration rollback is
allowed only before production redemptions. После real grants сначала disable
campaign, затем откатывать UI/API, но таблицы и grants оставлять; down-migration
запрещена. Frontend нельзя откатывать ниже compatibility floor, иначе старый
hook снова отправит opaque token в referral/localStorage/log. Disabling campaign
never deletes/revokes ledger, credits or Purchase.

Production smoke:

```text
invalid opaque token -> safe INVALID_CODE, no raw token in logs
valid token + incomplete profile -> onboarding, redemptions_used unchanged
valid token + complete profile -> sheet shows configured name/benefits
activate -> one AccessLedger + one gift credit + one entitlement/redemption
lost first 200 + repeat -> ALREADY_REDEEMED, no duplicates, UI refreshes access
disable -> new user INVALID_CODE, old grants intact
unknown birth time -> explicit required-time UI, no redirect loop/counter use
synthetic token -> absent from all transport/application logs
```

## 17. Coder-loop execution rule

Кодеру никогда не передаётся этот master целиком как одна задача. Архитектор
выдаёт только очередной numbered slice из этой директории. На одну coder
итерацию — один локальный goal, узкий file scope, собственные acceptance criteria
и одна targeted verification command. Следующий slice начинается только после
review и фиксации предыдущего.

Кодер не коммитит и не пушит. Commit/push/deploy остаются у
архитектора/ревьюера после общей acceptance.
