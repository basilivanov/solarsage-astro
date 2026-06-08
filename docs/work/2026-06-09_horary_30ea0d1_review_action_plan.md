# Review / action plan: Horary credit ledger after commits 30ea0d1 and b102331

Date: 2026-06-09
Original reviewed commit: `30ea0d1416da92ae857a48d7c4e25f2c27ebefb9`
Follow-up fix commit: `b102331fc22b8dbdb2d3e7c04a6c81e517d685b2`
Source TZ: `docs/16_Horary_questions_TZ.md`
Related UX addendum: `docs/work/2026-06-09_horary_b102331_postfix_review_and_ui_addendum.md`

## Current verdict

Status: **backend blockers from the 30ea0d1 review are resolved on paper by b102331**.

The previous review marked the feature as not accepted because of three backend blockers and one major legacy-model issue:

```text
B1 duplicate idempotent submit could enqueue duplicate generation
B2 request_hash ignored time/location/timezone
B3 late/stale generation could overwrite failed/refunded question
M1 legacy HoraryQuota model/table still existed
```

Commit `b102331` claims and appears from the commit diff to resolve these:

- `HoraryService.create_question()` now returns `(question, created)`;
- router starts generation only when `created == true`;
- `request_hash` now uses canonical JSON over full business payload excluding `idempotencyKey`;
- generator uses `with_for_update` and status checks before generation/save;
- legacy `HoraryQuota` model/table was removed;
- tests were expanded.

Backend acceptance is now **conditional** on local CI/grep verification staying green.

---

# What must still be verified

Run these checks before final acceptance:

```bash
# no old live quota model
grep -R "HoraryQuota\|questions_used\|questions_limit\|left\|nextInDays" apps/api lib components packages/contracts \
  --exclude-dir=.venv --exclude-dir=__pycache__ --exclude-dir=node_modules

# new credit model present
grep -R "subscription_weekly_free\|HoraryCredit\|HoraryCreditSpend" apps/api

# tests
cd /opt/solarsage-astro
pytest apps/api/tests -q
pnpm test
pnpm build
```

Allowed old-model hits:

- historical docs/work review files only.

No live app code should rely on:

```text
HoraryQuota
questions_used
questions_limit
left / nextInDays as primary horary balance
```

---

# Resolved backend blockers

## B1. Duplicate idempotent submit enqueueing duplicate generation

Previous issue:

```text
Same idempotencyKey + same payload returned existing processing question,
but router still launched a new background generation task.
```

Expected fixed behavior after `b102331`:

```text
same idempotencyKey + same payload => return existing question, created=false
router enqueues generation only when created=true
```

Required regression test:

```text
POST same payload twice with same idempotencyKey
=> same question id
=> one credit spend
=> create_task called once
```

## B2. Incomplete request_hash

Previous issue:

```text
request_hash = hash(text + category)
```

This was wrong because horary depends on time/place/timezone.

Expected fixed behavior after `b102331`:

```text
request_hash = canonical JSON hash of:
- text
- category
- clientTimezone/client_timezone
- clientLocalTime/client_local_time
- questionLat/question_lat
- questionLon/question_lon
```

`idempotencyKey` must not be included in the hash.

Required regression tests:

```text
same idempotencyKey + different clientLocalTime => 409
same idempotencyKey + different questionLat/questionLon => 409
same idempotencyKey + different clientTimezone => 409
```

## B3. Late/stale generation overwrite after refund

Previous issue:

```text
TTL could mark question failed and refund credit,
then late generator could still save answer and mark question answered.
```

Expected fixed behavior after `b102331`:

```text
Before generation/save, reload/lock question.
If status != processing, skip save and do not change status.
```

Required regression test:

```text
question failed/refunded by TTL
late generation attempts to save answer
=> no answer created
=> question remains failed
=> credit remains refunded
```

## M1. Legacy HoraryQuota removed

Previous issue:

```text
HoraryQuota.questions_used / questions_limit / reset_at still existed.
```

Expected fixed behavior after `b102331`:

```text
HoraryQuota model removed.
horary_quotas migration/table removed.
No service/API/frontend uses old quota model.
```

---

# Remaining product/UX work

The next work packet is not the backend credit ledger. It is UX/product polish from the current horary screen feedback.

Packet title:

```text
W-HORARY-UX-LOCATION: question place, category fix, premium processing
```

This packet is now also reflected in `docs/16_Horary_questions_TZ.md` and detailed in `docs/work/2026-06-09_horary_b102331_postfix_review_and_ui_addendum.md`.

## UX issue U1. Category chips switching

Observed feedback:

```text
Отношения works, but after selecting it, clicking another category does not visibly change selection.
```

Required behavior:

```text
Category chips are single-select.
Clicking another chip always switches selectedCategory.
The selected chip visual state updates immediately.
```

Acceptance:

```text
Given selectedCategory = love
When user taps career
Then selectedCategory = career
And career chip is selected
And love chip is unselected
```

## UX issue U2. Question place is missing

Horary form currently shows question time, but must also show question place.

Required UI:

```text
Момент вопроса
Время: 9 июня 2026 г. в 00:41
Место: Москва, Россия
```

If location is unknown:

```text
Место вопроса: не определено
[Указать место]
```

Location must be editable.

## UX issue U3. Location terminology

Do not call place/location a significator.

Correct terms:

```text
Место вопроса
Место построения хорарной карты
Question place
Horary chart location
```

`Significator` is a planet/house representing the querent or the topic.

## UX issue U4. CTA copy

Replace generic:

```text
Спросить звёзды
```

Recommended CTA:

```text
Получить ответ карты
```

Alternative:

```text
Открыть ответ карты
```

## UX issue U5. Premium processing state

Replace plain spinner-like state with branded horary processing.

Recommended copy:

```text
Строим карту вопроса
Фиксируем момент, место и главные сигнификаторы. Обычно это занимает несколько секунд.
```

Visual direction:

- warm/premium card;
- animated orbit/ring;
- tiny moon/star dot;
- steps:
  1. Фиксируем момент
  2. Строим карту
  3. Формулируем ответ

Long-running state:

```text
Ответ формируется дольше обычного. Мы сохраним вопрос и покажем ответ, когда карта будет готова.
```

---

# Required UX implementation scope

Likely files:

```text
components/readings/horary/horary-screen.tsx
components/readings/horary/horary-form.tsx
components/readings/horary/horary-time-confirm.tsx
components/readings/horary/horary-progress.tsx
components/readings/horary/horary-answer-view.tsx
lib/contracts/horary.ts
lib/api/horary.ts
apps/api/app/schemas/horary.py
apps/api/app/db/models.py
apps/api/alembic/versions/0011_add_horary.py
apps/api/app/api/horary.py
apps/api/tests/test_horary_endpoints.py
```

Backend extension is optional unless we want to persist/display place later. Recommended addition:

```text
question_location_name nullable
```

Use it for history/answer display. `questionLat/questionLon` are still the calculation fields.

---

# Final checklist

Backend ledger acceptance:

```text
[ ] B1 regression test passes.
[ ] B2 regression tests pass.
[ ] B3 regression test passes.
[ ] No live old quota model usage.
[ ] API uses weeklyFreeAvailable/bonusCredits/paidCredits.
[ ] Frontend gating does not use left/nextInDays.
```

UX/location acceptance:

```text
[ ] Category chips switch reliably.
[ ] User sees question time and question place.
[ ] User can edit question place.
[ ] questionLat/questionLon are sent when known.
[ ] Human-readable place is shown.
[ ] Place is called “Место вопроса”, not “сигнификатор”.
[ ] CTA is “Получить ответ карты” or approved equivalent.
[ ] Processing state is premium/branded and not plain spinner-only.
```

## Final note

`b102331` closes the backend review action plan. The next useful coder packet should focus on UI/location polish, not another rewrite of the credit ledger.
