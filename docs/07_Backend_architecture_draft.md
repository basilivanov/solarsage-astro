---
id: doc-07-backend-arch
status: active
wave: W-1.1
last_review: 2026-06-08
---
# 07. Backend architecture draft

## Роль документа

Этот документ фиксирует текущую рабочую модель backend для MVP Telegram Mini App.

Backend в этом проекте — не просто CRUD. Он является **оркестратором расчёта, доступа, нормализации, LLM-интерпретации и кэширования**.

Главная задача backend:

```text
принять пользователя и дату
  → проверить профиль и доступ
  → посчитать или достать из кэша день
  → собрать TodayPayload
  → вернуть фронту стабильный контракт
```

---

# Рекомендуемый стек

- Python
- FastAPI
- PostgreSQL
- Redis
- Celery / RQ / Dramatiq / arq для фоновых задач
- SQLAlchemy / SQLModel
- Pydantic
- SolarSage как REST sidecar
- отдельный LLM service module

Для расчётного слоя, JSON-пайплайнов, SolarSage-интеграции и LLM-оркестрации Python удобнее, чем Node. Фронт остаётся React/Next.

---

# Общая схема backend

```text
Telegram Mini App
        ↓
Backend API
        ↓
Telegram auth / User / Profile
        ↓
Access service
        ↓
SolarSage client
        ↓
Calculation pipeline
        ↓
Normalization / AstroSignal
        ↓
Scoring / SemanticLayer
        ↓
LLM interpretation
        ↓
TodayPayload cache
        ↓
Frontend
```

---

# Предлагаемая структура проекта

```text
app/
  api/
    day.py
    calendar.py
    profile.py
    readings.py
    auth.py
    payments.py
    referrals.py
    horary.py

  core/
    config.py
    security.py
    logging.py

  db/
    models.py
    session.py
    migrations/

  services/
    telegram_auth.py
    access_service.py
    profile_service.py
    solarsage_client.py
    calculation_service.py
    normalization_service.py
    scoring_service.py
    semantic_service.py
    llm_service.py
    today_service.py
    calendar_service.py
    referral_service.py
    subscription_service.py
    horary_credit_service.py
    horary_service.py
    horary_engine.py

  schemas/
    today.py
    calendar.py
    profile.py
    readings.py
    access.py
    astro_signal.py
    horary.py

  workers/
    tasks.py
```

---

# Главные сущности базы

## users

```text
users
- id
- telegram_id
- username
- first_name
- avatar_url
- created_at
- updated_at
```

## user_profiles

Данные для расчётов.

```text
user_profiles
- user_id
- birth_date
- birth_time
- birth_place_name
- birth_lat
- birth_lon
- birth_timezone
- current_location_name
- current_lat
- current_lon
- current_timezone
- birthday_location_name
- birthday_lat
- birthday_lon
- birthday_timezone
- house_system
- created_at
- updated_at
```

Изменение этих данных инвалидирует расчётные кэши.

---

# Access model

## Важный принцип

Сначала расходуются подарочные / реферальные дни, затем подписка.

Постоянного free-tier нет.

## access_ledger

Лучше хранить доступ ledger-событиями, а не только одним `access_until`.

```text
access_ledger
- id
- user_id
- type: referral_bonus / gift / subscription / adjustment
- days_amount
- starts_at
- expires_at
- consumed_days
- created_at
```

Так проще корректно реализовать:

- реферальные 14 дней;
- подарочные дни;
- подписку, которая начинает расходоваться после бонусных дней;
- ручные корректировки;
- аудит.

## access_service.can_access_day(user, date)

Должен возвращать content access state:

```ts
{
  state: "full" | "preview" | "locked",
  reason?: "active_referral_days" | "active_subscription" | "expired_access" | "outside_access_window",
  referralDaysLeft?: number,
  subscriptionActive?: boolean,
  accessUntil?: string
}
```

---

# Referrals

```text
referrals
- id
- inviter_user_id
- invited_user_id
- referral_code
- status
- reward_granted_at
- created_at
```

Правило:

**когда новый валидный пользователь пришёл по ссылке — обоим начислить 14 дней.**

---

# Horary credits

Source of truth для продуктовой логики: `docs/16_Horary_questions_TZ.md`.

Даже если хорар реализуется позже, модель кредитов нужно заложить заранее, потому что она влияет на Profile, paywall и будущие payment flows.

## horary_credits

```text
horary_credits
- id
- user_id
- source: subscription_weekly_free / referral_bonus / gift / paid / adjustment
- amount
- used_amount
- access_week_start nullable
- access_week_end nullable
- created_at
- expires_at nullable
- metadata_json nullable
```

Deprecated:

```text
weekly_bonus
```

`weekly_bonus` больше не используется, потому что смешивает два разных понятия: weekly-free вопрос активного доступа и настоящие бонусные / подарочные кредиты.

## Правило продукта

- активный доступ даёт **1 бесплатный хорарный вопрос в неделю доступа**;
- weekly-free вопрос называется `subscription_weekly_free`;
- `subscription_weekly_free` не копится;
- `subscription_weekly_free` сгорает в конце своей недели доступа, если пользователь его не использовал;
- продление trial/referral/gift/subscription создаёт будущие недели доступа, но не выдаёт все будущие weekly-вопросы сразу;
- paid-хорары копятся и не сгорают по умолчанию;
- gift/referral/adjustment-хорары живут по своему `expires_at`.

## Порядок списания

```text
1. Активный subscription_weekly_free текущей access-week.
2. referral_bonus / gift / adjustment с ближайшим expires_at.
3. paid credits, oldest first.
```

Инварианты:

- нельзя списать paid-кредит, если доступен активный weekly-free;
- истёкшие кредиты не списываются;
- списание атомарное;
- один вопрос списывает максимум один кредит;
- повторный submit с тем же idempotency_key не списывает второй кредит.

## horary_questions

```text
horary_questions
- id
- user_id
- text
- category nullable
- status: pending / processing / answered / failed / refunded / expired
- client_timezone
- client_local_time nullable
- question_lat nullable
- question_lon nullable
- spent_credit_id nullable
- idempotency_key
- created_at
- updated_at
```

## horary_answers

```text
horary_answers
- id
- question_id
- verdict: yes / no / maybe
- confidence
- blocks_json
- planets_json
- generated_at
```

## horary_credit_spends

```text
horary_credit_spends
- id
- user_id
- credit_id
- question_id
- amount
- idempotency_key
- created_at
```

---

# Расчётные кэши

## natal_snapshots

```text
natal_snapshots
- id
- user_id
- input_hash
- calculation_version
- payload_json
- created_at
```

Считается при:

- первом онбординге;
- изменении даты рождения;
- изменении времени рождения;
- изменении места рождения.

## period_snapshots

```text
period_snapshots
- id
- user_id
- period_key
- input_hash
- calculation_version
- payload_json
- created_at
```

Примеры `period_key`:

- `2026_solar_year`
- `2026-04`
- `annual_profection_2026`

Инвалидируется при:

- смене birthday location;
- смене calculation version;
- изменении профиля.

## daily_snapshots

```text
daily_snapshots
- id
- user_id
- date
- input_hash
- calculation_version
- payload_json
- created_at
```

## semantic_layers

```text
semantic_layers
- id
- user_id
- date
- normalization_version
- scoring_version
- payload_json
- created_at
```

Содержит:

- AstroSignal[];
- mainTheme;
- topFlags;
- amplifiers;
- softeners;
- dayQuality;
- dayStatus.

## today_payloads

```text
today_payloads
- id
- user_id
- date
- contract_version
- interpretation_version
- prompt_version
- payload_json
- created_at
```

Это готовый ответ для фронта.

---

# Главный endpoint

## GET /api/day/:date

Центральный endpoint продукта.

Логика:

```text
1. Проверить Telegram user
2. Найти user profile
3. Проверить access к date
4. Если нет доступа:
   - вернуть preview TodayPayload + soft lock
5. Если доступ есть:
   - проверить TodayPayload cache
6. Если cache есть:
   - вернуть payload
7. Если cache нет:
   - получить / создать NatalDeepSnapshot
   - получить / создать PeriodSnapshot
   - получить / создать DailySnapshot
   - нормализовать в AstroSignal[]
   - посчитать scoring
   - собрать SemanticLayer
   - отправить curated context в LLM
   - сохранить TodayPayload
   - вернуть TodayPayload
```

---

# Horary endpoints

## GET /api/horary/quota

Возвращает баланс:

```ts
{
  weeklyFreeAvailable: boolean,
  weeklyFreeExpiresAt?: string,
  nextWeeklyFreeAt?: string,
  bonusCredits: number,
  paidCredits: number,
  canPurchase: boolean
}
```

`bonusCredits` не включает текущий `subscription_weekly_free`.

## POST /api/horary/questions

Создаёт вопрос, атомарно списывает кредит и запускает генерацию.

Request:

```ts
{
  text: string,
  category?: "love" | "career" | "money" | "health" | "travel" | "other",
  clientTimezone: string,
  clientLocalTime?: string,
  questionLat?: number,
  questionLon?: number,
  idempotencyKey: string
}
```

## GET /api/horary/questions

Список вопросов пользователя.

## GET /api/horary/questions/{id}

Один вопрос + ответ. Обязательная ownership-проверка по `user_id`.

---

# Sync vs async generation

## MVP v1

Today можно считать синхронно, если укладываемся в 10–20 секунд.

Horary генерация может быть асинхронной:

```text
POST /api/horary/questions
  → списать кредит
  → создать question(status=processing)
  → запустить generate_answer
  → frontend polling GET /api/horary/questions/{id}
```

Если генерация упала:

- paid-кредит не должен пропадать без retry/refund политики;
- вопрос переводится в `failed` или `refunded`;
- ошибка логируется.

---

# Calendar endpoint

## GET /api/calendar?month=YYYY-MM

Возвращает сетку месяца:

- date;
- dayNumber;
- isToday;
- isCurrentMonth;
- dayStatus;
- access.

Для календаря не нужно генерировать полный текст дня.

Для MVP:

- календарь показывает дни;
- dayStatus можно отдавать, если день уже посчитан;
- если не посчитан — можно показывать нейтрально;
- при открытии дня считаем полностью.

Для 7-дневной ленты лучше считать статусы сразу.

---

# LLM service

LLM получает не raw SolarSage, а curated context.

Для Today:

```json
{
  "date": "...",
  "mainTheme": "...",
  "dayQuality": "...",
  "topFlags": [],
  "dailyTriggers": [],
  "personalActivations": [],
  "periodBackground": [],
  "amplifiers": [],
  "softeners": [],
  "manifestationZones": [],
  "practicalDirection": []
}
```

Для Horary LLM получает уже посчитанный backend-движком verdict/confidence и только narrates результат. LLM не рассчитывает хорар самостоятельно.

LLM возвращает строгий JSON и не должна придумывать расчёты.

---

# Обязательные технические принципы

## Versioning

Везде храним:

```text
calculation_version
normalization_version
scoring_version
prompt_version
contract_version
```

## Input hash

Для расчётных кэшей нужен `input_hash`.

Он должен учитывать:

- birth data;
- current location;
- birthday location;
- date;
- house system;
- calculation version.

Если hash изменился — кэш невалиден.

## Debug endpoint

Полезен internal endpoint:

```http
GET /api/debug/day/:date
```

Он возвращает:

- AstroSignal[];
- scoring;
- top ranked signals;
- LLM context;
- final payload.

Пользователю это не отдаём.

## Не хранить только LLM-текст

Нужно хранить:

- raw;
- normalized;
- semantic;
- final text.

Иначе будет невозможно понять, почему LLM написала конкретный день.

---

# Фазы backend MVP

## Фаза 1. Пользователь и профиль

- Telegram auth
- onboarding save
- profile edit
- birth/current/birthday locations

## Фаза 2. Access

- referral code
- +14 дней обоим
- access state
- paywall state

## Фаза 3. Today mocked pipeline

- endpoint `/api/day/:date`
- отдаёт payload из mock/fixture
- фронт подключается к реальному API

## Фаза 4. SolarSage integration

- natal snapshot
- daily snapshot
- period snapshot хотя бы частично

## Фаза 5. Normalization + scoring

- AstroSignal
- SemanticLayer
- dayStatus

## Фаза 6. LLM generation

- curated context
- strict JSON output
- cache TodayPayload

## Фаза 7. Payments

- Telegram payments / provider
- subscription state
- порядок списания доступа

## Фаза 8. Horary

- `subscription_weekly_free` weekly-credit
- paid / gift / referral horary credits
- horary question lifecycle
- deterministic verdict engine
- LLM narration

---

# Главное решение

Backend должен строиться вокруг главного endpoint:

```http
GET /api/day/:date
```

И вокруг стабильного пути:

```text
Profile + Access + SolarSage + SemanticLayer + LLM + Cache → TodayPayload
```

Хорар строится как отдельный product flow:

```text
Profile + Access + HoraryCredits + HoraryEngine + LLM narration + HoraryAnswer
```
