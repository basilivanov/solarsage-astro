# ТЗ: Хорарные вопросы

## 1. Суть фичи

Пользователь задаёт конкретный астрологический вопрос — хорар — и получает ответ в формате «да / нет / возможно» с пояснением, сроками и практическим выводом.

Хорар — отдельный формат раздела «Разборы». Он не является частью `TodayPayload`: Today объясняет выбранный день, а хорар отвечает на конкретный вопрос пользователя, заданный в конкретный момент времени.

Ключевой принцип хорара: **момент вопроса и место вопроса важны**. Поэтому приложение фиксирует и показывает пользователю время и место вопроса перед отправкой.

---

## 2. Главная продуктовая модель квот

### 2.1. Активный доступ даёт weekly-free вопрос

Активный доступ даёт пользователю **1 бесплатный хорарный вопрос в неделю доступа**.

Активный доступ может быть получен через:

- trial;
- реферальное продление;
- подарочный доступ;
- платную подписку;
- ручную админскую корректировку.

Постоянного free-tier нет. Бесплатный weekly-вопрос существует только внутри активного доступа.

### 2.2. Бесплатный weekly-вопрос не копится

Бесплатный weekly-вопрос:

- выдаётся на конкретную неделю активного доступа;
- доступен только внутри этой недели;
- **не переносится** на следующую неделю;
- **сгорает** в конце недели доступа, если пользователь его не использовал;
- не превращается в paid-кредит;
- не суммируется с weekly-вопросами следующих недель.

Пример:

```text
Пользователь получил 14 дней trial.
Неделя 1: доступен 1 бесплатный хорарный вопрос.
Если он не использован до конца недели 1 — он сгорает.
Неделя 2: появляется новый 1 бесплатный хорарный вопрос.
Итого в неделю 2 у пользователя всё равно 1 бесплатный weekly-вопрос, а не 2.
```

### 2.3. Продление доступа

Если пользователь продлил доступ через рефералку, подарок или подписку, он **не получает все будущие weekly-вопросы сразу пачкой**.

Правило:

```text
Каждая фактически наступившая неделя активного доступа даёт максимум 1 бесплатный weekly-вопрос.
```

Пример:

```text
Trial: 14 дней.
Referral extension: ещё 14 дней.
Итого активный доступ: 28 дней.

Но пользователь не получает сразу 4 хорарных вопроса.
В каждую неделю доступа появляется только 1 weekly-free вопрос.
Неиспользованный weekly-free вопрос прошлой недели сгорает.
```

---

## 3. Типы хорарных кредитов

### 3.1. Источники кредитов

Используем явные `source` значения:

```text
subscription_weekly_free
referral_bonus
gift
paid
adjustment
```

Старое имя `weekly_bonus` **deprecated** и не должно использоваться в новой реализации.

Причина: `weekly_bonus` смешивает две разные сущности:

1. weekly-free вопрос, который даётся активным доступом и сгорает;
2. настоящие бонусные / подарочные кредиты, которые могут копиться.

### 3.2. `subscription_weekly_free`

Это бесплатный weekly-вопрос за активную неделю доступа.

Правила:

- `amount = 1`;
- привязан к конкретному `access_week_start` / `access_week_end`;
- `expires_at = access_week_end`;
- не копится;
- не переносится;
- первым участвует в списании;
- не продаётся отдельно.

### 3.3. `paid`

Купленные хорарные вопросы.

Правила:

- копятся;
- не сгорают по умолчанию;
- не уменьшаются при weekly-expiry;
- списываются после weekly-free и expiring bonus/gift/referral credits.

### 3.4. `referral_bonus`, `gift`, `adjustment`

Это не weekly-free вопросы.

Правила:

- могут копиться;
- могут иметь `expires_at`;
- если `expires_at = null`, не сгорают;
- если `expires_at` задан, списываются раньше paid-кредитов.

---

## 4. Порядок списания

При создании хорарного вопроса backend списывает кредит строго в порядке:

```text
1. Активный subscription_weekly_free текущей недели доступа.
2. referral_bonus / gift / adjustment с ближайшим expires_at.
3. paid credits, oldest first.
```

Инварианты:

- paid-кредит нельзя списывать, если доступен активный `subscription_weekly_free`;
- истёкшие кредиты нельзя списывать;
- списание атомарное;
- один вопрос списывает максимум один кредит;
- повторный submit с тем же `idempotency_key` не должен списывать второй кредит;
- технический сбой генерации не должен терять paid-кредит без retry/refund политики.

---

## 5. Access-week окно

### 5.1. Неделя доступа

Для MVP неделя доступа считается **от начала активного access-периода**, а не от календарного понедельника.

Пример:

```text
Trial starts: 2026-06-01 12:00
Week 1: 2026-06-01 12:00 → 2026-06-08 12:00
Week 2: 2026-06-08 12:00 → 2026-06-15 12:00
```

Так пользователь не теряет weekly-вопрос из-за того, что стартовал trial в середине календарной недели.

### 5.2. Непрерывное продление

Если доступ продлён до окончания текущего окна, следующие недели строятся непрерывно.

```text
Trial:    2026-06-01 12:00 → 2026-06-15 12:00
Referral: продление до 2026-06-29 12:00

Week 1: 2026-06-01 12:00 → 2026-06-08 12:00
Week 2: 2026-06-08 12:00 → 2026-06-15 12:00
Week 3: 2026-06-15 12:00 → 2026-06-22 12:00
Week 4: 2026-06-22 12:00 → 2026-06-29 12:00
```

В каждой неделе максимум один `subscription_weekly_free`.

---

## 6. Пользовательский флоу

### 6.1. Список вопросов `/readings/horary`

1. Header: стрелка «← Разборы», заголовок «Хорарные вопросы».
2. `HoraryQuotaBar` показывает:
   - доступен ли weekly-free вопрос;
   - когда он сгорит;
   - количество paid-кредитов;
   - количество gift/referral/adjustment-кредитов.
3. Список прошлых вопросов.
4. Если есть доступный кредит — форма нового вопроса.
5. Если кредитов нет — плашка «Вопросы закончились» + кнопка «Докупить».

### 6.2. Форма вопроса

- Категория: `love | career | money | health | travel | other`.
- Категория optional, но chips single-select: клик по другой категории всегда переключает selected category.
- Textarea: min 5, max 500 символов.
- Подтверждение времени вопроса:
  - timezone: `Intl.DateTimeFormat().resolvedOptions().timeZone`;
  - local time: текущее локальное время;
  - возможность изменить время вручную.
- Подтверждение места вопроса:
  - показать человекочитаемое место: город + страна, например `Москва, Россия`;
  - возможность изменить место;
  - если место не определено, показать `Место вопроса: не определено` и CTA `Указать место`;
  - не показывать raw coordinates как основной UX.
- Кнопка disabled, если:
  - текст короче 5 символов;
  - нет доступных кредитов;
  - место вопроса требуется, но не определено.

Рекомендуемый текст кнопки:

```text
Получить ответ карты
```

Допустимый вариант:

```text
Открыть ответ карты
```

Не использовать generic/kitsch copy как основной CTA:

```text
Спросить звёзды
Спросить Вселенную
Магический ответ
```

### 6.3. Генерация

После submit:

1. backend списывает кредит;
2. создаёт `HoraryQuestion`;
3. ставит `status = processing`;
4. запускает генерацию;
5. frontend показывает premium progress screen и polling.

Polling:

```text
GET /api/horary/questions/{id}
interval: 2 sec
```

Processing screen должен быть продуктовым, не техническим spinner-only.

Рекомендуемая копия:

```text
Строим карту вопроса
Фиксируем момент, место и главные сигнификаторы. Обычно это занимает несколько секунд.
```

Визуальная идея:

- мягкая карточка на тёплом фоне;
- тонкое анимированное кольцо/орбита;
- маленькая moon/star-dot animation;
- 3 шага: `Фиксируем момент` → `Строим карту` → `Формулируем ответ`.

Timeout UI: если через 30 секунд ответ ещё `processing`, показать текст:

```text
Ответ формируется дольше обычного. Мы сохраним вопрос и покажем ответ, когда карта будет готова.
```

### 6.4. Экран ответа `/readings/horary/[id]`

Показывает:

- текст вопроса;
- категорию;
- дату/время вопроса;
- место вопроса / место построения карты;
- verdict card: `yes | no | maybe`, confidence;
- блоки ответа;
- timing-блок;
- задействованные планеты / дома;
- дату генерации.

---

## 7. Блоковая система ответа

Хорарный ответ использует ту же блоковую систему, что и натальная карта.

Переиспользуем стандартные блоки:

```text
paragraph
lead
heading
list
callout
pros_cons
divider
quote
```

Добавляем только 2 хорарных блока:

```text
verdict_card
timing
```

`verdict_card`:

```ts
{
  type: "verdict_card"
  verdict: "yes" | "no" | "maybe"
  confidence: number // 0..1
  label?: string
}
```

`timing`:

```ts
{
  type: "timing"
  timeRange: string
  text?: string
}
```

---

## 8. Data model

### 8.1. `horary_credits`

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

Rules:

- `subscription_weekly_free` has `amount = 1`;
- `subscription_weekly_free.expires_at = access_week_end`;
- paid rows usually have `expires_at = null`;
- `metadata_json` can hold payment_id, referral_id, campaign_id, admin_note.

### 8.2. `horary_questions`

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
- question_location_name nullable
- spent_credit_id nullable
- idempotency_key
- request_hash
- created_at
- updated_at
```

`question_location_name` is optional but recommended for displaying the place used later in history/answer screens. If not implemented in the first UI polish pass, frontend must still show the place currently used before submit.

### 8.3. `horary_answers`

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

### 8.4. `horary_credit_spends`

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

Invariants:

- `UNIQUE(idempotency_key)`;
- `UNIQUE(question_id)` if one question consumes one credit;
- `amount = 1` for MVP.

---

## 9. API contracts

### 9.1. Quota / balance

```http
GET /api/horary/quota
```

Response:

```ts
export type HoraryQuotaRead = {
  weeklyFreeAvailable: boolean
  weeklyFreeExpiresAt?: string
  nextWeeklyFreeAt?: string
  bonusCredits: number
  paidCredits: number
  canPurchase: boolean
}
```

Важно: `bonusCredits` не включает текущий `subscription_weekly_free`.

### 9.2. Create question

```http
POST /api/horary/questions
```

Request:

```ts
export type HoraryQuestionCreate = {
  text: string
  category?: "love" | "career" | "money" | "health" | "travel" | "other"
  clientTimezone: string
  clientLocalTime?: string
  questionLat?: number
  questionLon?: number
  questionLocationName?: string
  idempotencyKey: string
}
```

Response:

```ts
export type HoraryQuestionRead = {
  id: string
  text: string
  category?: string | null
  status: "pending" | "processing" | "answered" | "failed" | "refunded" | "expired"
  spentCreditSource?: "subscription_weekly_free" | "referral_bonus" | "gift" | "paid" | "adjustment"
  clientTimezone: string
  clientLocalTime?: string | null
  questionLocationName?: string | null
  createdAt: string
  answer?: HoraryAnswerRead | null
}
```

Errors:

```text
401 UNAUTHORIZED
402 NO_HORARY_CREDITS
403 ACCESS_REQUIRED
409 IDEMPOTENCY_CONFLICT
422 INVALID_QUESTION
500 HORARY_GENERATION_FAILED
```

---

## 10. Horary engine

Хорарный движок не зависит от LLM.

Алгоритм:

1. взять момент вопроса: `clientLocalTime + clientTimezone`, fallback на серверное now;
2. взять место вопроса: `questionLat/questionLon`, fallback на current location, затем birth location;
3. построить хорарную карту;
4. определить ASC, управителя ASC, Луну, сигнификатор вопроса;
5. посчитать verdict и confidence;
6. передать LLM только готовый контекст, а не сырые внутренние структуры.

Место вопроса не является сигнификатором. Корректные термины:

```text
question place
место вопроса
место построения хорарной карты
```

Сигнификатор — это планета/дом, представляющие кверента или тему вопроса.

Категории:

| category | significator | houses |
|---|---|---|
| love | Венера | 5, 7 |
| career | Сатурн | 2, 6, 10 |
| money | Юпитер | 2, 8 |
| health | Марс | 1, 6, 12 |
| travel | Меркурий | 3, 9 |
| other | Луна | зависит от вопроса |

---

## 11. LLM narration

LLM не рассчитывает хорар. LLM только объясняет результат, который уже посчитал backend engine.

LLM получает:

- текст вопроса;
- категорию;
- момент вопроса;
- место вопроса / место построения карты;
- verdict;
- confidence;
- сигнификатор;
- управителя ASC;
- Луну;
- ключевые аспекты;
- задействованные дома;
- timing hints.

LLM возвращает только JSON с блоками:

```json
{
  "blocks": [
    { "type": "verdict_card", "verdict": "yes", "confidence": 0.78, "label": "Скорее да" },
    { "type": "lead", "text": "Главный вывод..." },
    { "type": "paragraph", "text": "Что говорит карта..." },
    { "type": "pros_cons", "pros": ["..."], "cons": ["..."] },
    { "type": "timing", "timeRange": "2–3 недели", "text": "..." },
    { "type": "callout", "tone": "insight", "title": "Обрати внимание", "text": "..." }
  ]
}
```

Fallback: если LLM не вернул валидный JSON за 2 попытки, backend возвращает минимальный ответ из детерминистических данных: `verdict_card + lead`.

---

## 12. Tests / acceptance criteria

### 12.1. Weekly-free expires

```text
Given user has active access week 1
And unused subscription_weekly_free exists for week 1
When week 1 ends
Then this credit is expired
And it is not available in week 2
```

### 12.2. New week grants exactly one new free question

```text
Given user has continuous active access for 14 days
When week 2 starts
Then user has exactly 1 subscription_weekly_free for week 2
And unused week 1 credit is not added to week 2
```

### 12.3. Paid credits persist

```text
Given user bought 3 paid horary credits
When weekly free credits expire
Then paid credits remain 3
```

### 12.4. Spend order

```text
Given user has 1 active subscription_weekly_free and 2 paid credits
When user submits a horary question
Then subscription_weekly_free is spent
And paidCredits remains 2
```

### 12.5. No double spend

```text
Given user submits the same question twice with the same idempotencyKey
Then only one credit is spent
```

### 12.6. No old quota model

```text
Implementation must not use the old model:
- default 3 free questions
- questions_used / questions_limit as the primary balance
- +1 accumulating question every 7 days
- weekly_bonus as an accumulating source
```

### 12.7. Category switching

```text
Given selectedCategory = love
When user taps career
Then selectedCategory = career
And career chip is visually selected
And love chip is visually unselected
```

### 12.8. Question place is visible and editable

```text
Given the horary form is open
Then user sees question time and question place
And user can edit question place
And submitted payload includes questionLat/questionLon when known
```

### 12.9. Premium processing state

```text
Given user submits a horary question
Then progress screen is shown
And it mentions moment + place + card/chart calculation
And it is not a plain technical spinner-only state
```

---

## 13. Implementation order

1. Pydantic schemas: `apps/api/app/schemas/horary.py`.
2. DB models: `horary_credits`, `horary_credit_spends`, `horary_questions`, `horary_answers`.
3. Alembic migration.
4. `HoraryCreditService`: weekly-free resolution, paid/bonus balance, spend order.
5. `HoraryService`: create/list/get questions, generation lifecycle.
6. API router: `/api/horary/*`.
7. `scripts/contracts/export_openapi.py`: add horary top-level schemas.
8. `pnpm contracts:generate`.
9. Frontend contracts and API facade.
10. `/readings/horary` and `/readings/horary/[id]`.
11. Profile `HoraryCard`: show weekly-free separately from paid/bonus.
12. Question place selector / resolver.
13. Premium horary progress state.
14. Tests.

---

## 14. Invariants

1. Backend-first contracts: Pydantic → OpenAPI → generated TS.
2. Weekly-free is `subscription_weekly_free`, not `weekly_bonus`.
3. Weekly-free does not accumulate and expires weekly.
4. Paid credits accumulate and do not expire by default.
5. Bonus/gift/referral/adjustment credits follow their own `expires_at`.
6. Spending order is deterministic: weekly-free → expiring bonus/gift/referral/adjustment → paid.
7. LLM does not calculate verdict; backend engine does.
8. Frontend does not invent quotas locally; it renders API state.
9. User cannot read another user's question.
10. Duplicate submit cannot double-spend credits.
11. Horary form must show both question time and question place.
12. Location must be called `Место вопроса`, not `сигнификатор`.
13. Category chips must be reliable single-select controls.
14. Processing state must be product/premium UX, not a plain spinner-only state.

---

## 15. Non-goals

- Real payment integration in the first horary wave.
- Streaming/SSE generation.
- Editing or deleting questions.
- Likes/dislikes for answers.
- Push notification when answer is ready.
- Full advanced horary engine beyond MVP deterministic verdict.
- Refactoring the whole natal block renderer before the first horary MVP.

---

## 16. No-guessing implementation rules

Этот раздел обязателен для coder agents. Не придумывать альтернативную модель квот и не возвращаться к старой модели `HoraryQuota.questions_used / questions_limit`.

### 16.1. Weekly-free credit creation

Не создавать все будущие weekly-free credits заранее.

`subscription_weekly_free` должен резолвиться лениво:

- на `GET /api/horary/quota`;
- на `POST /api/horary/questions`.

Backend может создать `subscription_weekly_free` row только для текущей активной access-week.

Будущие access-weeks не создают credits до фактического наступления этой недели.

### 16.2. Access-week interval

Access-week intervals are half-open:

```text
active if now >= access_week_start AND now < access_week_end
expired if now >= access_week_end
```

Все timestamps в DB должны храниться как timezone-aware UTC timestamps.

Frontend может показывать локальное время, но backend comparisons всегда идут в UTC.

### 16.3. Horary access rule

Активный product access нужен только для получения `subscription_weekly_free`.

Paid, gift, referral и adjustment horary credits можно тратить даже если Today access expired, если сам credit не expired.

```text
No active access + no horary credits → NO_HORARY_CREDITS
No active access + paid horary credits → question may be submitted
Active access + current weekly-free → weekly-free is spent first
```

### 16.4. Required DB constraints

`horary_credits`:

```text
CHECK amount > 0
CHECK used_amount >= 0
CHECK used_amount <= amount
CHECK source IN (
  'subscription_weekly_free',
  'referral_bonus',
  'gift',
  'paid',
  'adjustment'
)
```

Unique current-week free credit:

```text
UNIQUE(user_id, source, access_week_start, access_week_end)
WHERE source = 'subscription_weekly_free'
```

`horary_questions`:

```text
UNIQUE(user_id, idempotency_key)
```

`horary_credit_spends`:

```text
UNIQUE(question_id)
UNIQUE(idempotency_key)
```

### 16.5. Atomic spend algorithm

`POST /api/horary/questions` должен использовать одну DB transaction:

```text
1. Begin transaction.
2. Resolve current access-week.
3. Create current subscription_weekly_free if active access exists and row does not exist.
4. Select spendable credits FOR UPDATE.
5. Sort by spend order:
   a. active subscription_weekly_free
   b. referral_bonus / gift / adjustment by nearest expires_at
   c. paid by oldest created_at
6. If no spendable credit exists, return NO_HORARY_CREDITS.
7. Create horary_questions row with status='processing'.
8. Create horary_credit_spends row.
9. Increment horary_credits.used_amount by 1.
10. Commit.
11. Start async generation only after commit.
```

Нельзя запускать генерацию до commit списания кредита.

### 16.6. Idempotency behavior

Если тот же user отправляет тот же `idempotencyKey` повторно:

- same payload hash → вернуть существующий question;
- different payload hash → вернуть `409 IDEMPOTENCY_CONFLICT`;
- второй credit не списывается.

Хранить `request_hash` на `horary_questions`.

`request_hash` должен включать все business-input поля хорара, кроме `idempotencyKey`:

```text
text
category
clientTimezone / client_timezone
clientLocalTime / client_local_time
questionLat / question_lat
questionLon / question_lon
questionLocationName / question_location_name, если поле добавлено
```

### 16.7. Failure / refund policy

Если генерация ответа упала до создания `HoraryAnswer`:

- поставить question status = `failed`;
- для paid / gift / referral / adjustment credits создать compensating refund или уменьшить `used_amount`;
- для `subscription_weekly_free` восстановить кредит только если текущее время всё ещё внутри той же access-week;
- если weekly-free уже expired к моменту failure — не восстанавливать его.

Если ответ успешно создан:

- поставить question status = `answered`;
- automatic refund не делать.

Late/stale generation guard:

```text
Before saving HoraryAnswer, reload/lock question and require status='processing'.
If question is already failed/refunded/answered, skip answer save and do not change status.
```

### 16.8. Deprecated model forbidden

Implementation must not create or rely on:

```text
HoraryQuota.questions_used
HoraryQuota.questions_limit
left / nextInDays as primary quota model
default 3 free questions
+1 accumulating question every 7 days
weekly_bonus as a source
```

Frontend must render quota from:

```text
weeklyFreeAvailable
weeklyFreeExpiresAt
nextWeeklyFreeAt
bonusCredits
paidCredits
canPurchase
```

### 16.9. Required tests

Добавить тесты:

1. weekly-free создаётся только для текущей access-week;
2. future access weeks do not pre-create credits;
3. unused weekly-free expires at `access_week_end`;
4. boundary: ровно в `access_week_end` старый weekly-free уже unavailable;
5. next week has exactly one new weekly-free, not accumulated;
6. paid credits can be spent without active Today access;
7. paid credit is not spent while weekly-free is available;
8. expired gift/referral credits are ignored;
9. nearest `expires_at` bonus credit is spent before paid;
10. duplicate idempotency key does not double-spend;
11. same idempotency key with different request hash returns 409;
12. generation failure refunds paid credit;
13. generation failure restores weekly-free only if access-week is still active;
14. frontend does not use `left` / `nextInDays` as primary balance;
15. category chips switch reliably;
16. question place is visible, editable, and submitted as lat/lon when known;
17. progress screen uses premium horary UX copy and not only a spinner.

---

## 17. Final product rule

```text
Активный доступ даёт 1 бесплатный хорарный вопрос в неделю доступа.
Этот weekly-free вопрос не копится и сгорает в конце недели доступа.
Платные хорарные вопросы копятся и не сгорают по умолчанию.
Подарочные / реферальные / ручные кредиты живут по expires_at своей акции.
Сначала списывается weekly-free, потом expiring bonus/gift/referral/adjustment, потом paid.
```

---

## 18. UI/location addendum

This section captures the post-implementation UX feedback from the current horary screen.

Required polish packet:

```text
W-HORARY-UX-LOCATION: question place, category fix, premium processing
```

Scope:

- fix category chip switching;
- show/edit question place;
- send `questionLat/questionLon` when known;
- optionally persist/display `questionLocationName`;
- change CTA from generic `Спросить звёзды` to `Получить ответ карты` or approved equivalent;
- replace plain spinner with branded/premium horary processing state.

Acceptance:

```text
[ ] Category chips switch visually and logically.
[ ] User sees both time and place before submit.
[ ] User can edit question place.
[ ] Location is called “Место вопроса”.
[ ] Location is not called “сигнификатор”.
[ ] Submit CTA is premium and concrete.
[ ] Processing screen is beautiful and mentions moment/place/card construction.
```
