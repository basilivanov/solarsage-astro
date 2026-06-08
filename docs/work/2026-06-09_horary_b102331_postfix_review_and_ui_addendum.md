# Horary post-fix review + UI/location addendum

Date: 2026-06-09
Reviewed commit: `b102331fc22b8dbdb2d3e7c04a6c81e517d685b2`
Previous review packet: `docs/work/2026-06-09_horary_30ea0d1_review_action_plan.md`
Source TZ: `docs/16_Horary_questions_TZ.md`

## 1. Status after `b102331`

`b102331` resolves the main backend blockers from the previous review packet:

- B1: duplicate idempotent submit no longer enqueues a second background task;
- B2: `request_hash` now hashes the full business payload, not only text/category;
- B3: stale/late generation is guarded before saving `HoraryAnswer`;
- M1: legacy `HoraryQuota` model/table was removed;
- tests were extended for the new rules.

Backend acceptance can move from **blocked** to **conditionally acceptable for MVP**, assuming local CI remains green and grep confirms no live usage of the removed old quota model.

Required verification before final product acceptance:

```bash
grep -R "HoraryQuota\|questions_used\|questions_limit\|left\|nextInDays" apps/api lib components packages/contracts \
  --exclude-dir=.venv --exclude-dir=__pycache__ --exclude-dir=node_modules
```

Allowed hits: none for live horary quota logic. Historical docs/work mentions are allowed.

---

## 2. New product/UX feedback to add to implementation

Screenshot/user feedback from the current horary screen:

1. Category chip selection appears broken: `Отношения` works, but after selecting it, clicking other categories does not visibly change selection.
2. The form shows the question time, but does not show the question place/location.
3. For horary, location matters: the chart is cast for the question moment and place. The UI must show the current question place and allow changing it.
4. The submit copy `Спросить звёзды` feels generic. Need a more premium/feminine phrase.
5. The processing state should be beautiful and product-like, not just a technical spinner.

This is a separate UX/product-polish packet. It should not be mixed with the credit-ledger backend acceptance unless needed by API fields.

---

# 3. Required UX additions

## 3.1. Category chip behavior

Current expected behavior:

- category chips are single-select;
- tapping a non-selected category must immediately switch selection;
- tapping the selected category may either keep it selected or clear it, but this must be explicit and tested;
- selected category must have clear visual state.

Recommended rule for MVP:

```text
Category is optional, but chips are single-select.
Tapping another chip always switches selectedCategory.
Tapping the already selected chip keeps it selected, not clears it.
```

Reason: accidental clearing is confusing on mobile.

Acceptance:

```text
Given selectedCategory = love
When user taps career
Then selectedCategory = career
And career chip becomes visually selected
And love chip becomes unselected
```

## 3.2. Question place/location block

Horary form must show both:

- question time;
- question place.

Current time block should become a combined context block or two stacked blocks:

```text
Время вопроса: 9 июня 2026 г. в 00:41 (Europe/Moscow)
Место вопроса: Москва, Россия
```

If exact place is unknown:

```text
Место вопроса: не определено
```

and CTA:

```text
Указать место
```

The place block must be editable.

Recommended UI copy:

```text
Момент вопроса
Время: 9 июня 2026 г. в 00:41
Место: Москва, Россия
```

Button/edit labels:

```text
Изменить время
Изменить место
```

## 3.3. Location source/fallback

Backend already accepts:

```text
questionLat
questionLon
```

The frontend should send them when known.

Resolution order:

```text
1. user-selected question location from the form
2. browser/geolocation result if user allowed it
3. profile current location
4. profile birth location
```

UI must display which location is being used, not silently fallback.

Do not show raw coordinates as the primary UI. Show human-readable place name:

```text
Москва, Россия
Сочи, Россия
Амстердам, Нидерланды
```

Store/send machine fields:

```ts
questionLat?: number
questionLon?: number
questionLocationName?: string // if backend contract is extended
```

If backend contract is not extended, `questionLocationName` can remain frontend-only for MVP, but the answer screen should still display the place used.

## 3.4. Should this be called significator?

No. The place is not a significator.

Correct terms:

- question place / место вопроса;
- horary chart location / место построения хорарной карты;
- event location context.

`Significator` means the planet/house representing the querent or the asked topic. Example:

- querent significator: ASC ruler;
- relationship significator: 7th house ruler / Venus depending on method;
- career significator: 10th house ruler / Saturn depending on method.

UI should not call location a significator.

Recommended user-facing wording:

```text
Место вопроса
По нему строится хорарная карта
```

or shorter:

```text
Место вопроса — важно для расчёта карты
```

---

# 4. Premium/feminine action copy

Avoid generic:

```text
Спросить звёзды
```

Better options:

```text
Получить ответ карты
Задать хорарный вопрос
Открыть ответ карты
Построить хорар
Узнать ответ
```

Best MVP recommendation:

```text
Получить ответ карты
```

Why: softer and more premium than “Спросить звёзды”, but still concrete.

Secondary option for a more mystical/feminine tone:

```text
Открыть ответ карты
```

Avoid too kitschy copy:

```text
Спросить Вселенную
Спросить звёзды
Магический ответ
```

---

# 5. Beautiful processing state

Current spinner/progress must become a branded horary ritual state.

Recommended title/copy:

```text
Строим карту вопроса
Фиксируем момент, место и главные сигнификаторы. Обычно это занимает несколько секунд.
```

Alternative:

```text
Карта вопроса собирается
Мы учитываем время, место и тему вопроса, чтобы дать точный хорарный ответ.
```

Visual idea:

- soft card on warm background;
- animated thin circular orbit/ring;
- tiny moon/star dot moving around the ring;
- 3 short steps appearing below:
  1. Фиксируем момент
  2. Строим карту
  3. Формулируем ответ

Do not use a plain technical spinner as the main visual.

Acceptance:

```text
When question is submitted
Then user sees a premium processing screen
And the copy mentions moment + place + chart/question
And polling still happens every 2 seconds
And after 30 seconds the screen switches to long-running state text
```

Long-running state copy:

```text
Ответ формируется дольше обычного. Мы сохраним вопрос и покажем ответ, когда карта будет готова.
```

---

# 6. Required implementation packet

Packet title:

```text
W-HORARY-UX-LOCATION: question place, category fix, premium processing
```

Allowed files likely include:

```text
components/readings/horary/horary-screen.tsx
components/readings/horary/horary-form.tsx
components/readings/horary/horary-quota-bar.tsx
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

Backend contract extension is optional for MVP if only lat/lon are needed. But if we want to display the place later in history/answer, add:

```text
question_location_name nullable
```

to `horary_questions` and expose it in `HoraryQuestionRead`.

---

# 7. Acceptance checklist for this UX packet

```text
[ ] Category chips switch reliably from love to career/money/etc.
[ ] Selected category visual state updates immediately.
[ ] Form shows question time and question place.
[ ] User can change question place.
[ ] questionLat/questionLon are sent when known.
[ ] UI displays human-readable place, not only raw coordinates.
[ ] Location is called “Место вопроса”, not “сигнификатор”.
[ ] Submit button copy changed from “Спросить звёзды” to “Получить ответ карты” or approved equivalent.
[ ] Processing state is premium/branded, not a plain spinner.
[ ] Long-running generation copy says the question is saved and answer will appear later.
```

---

# 8. Post-b102331 review note

After `b102331`, the backend blocker packet is considered addressed on paper:

```text
B1 duplicate generation: fixed by created flag.
B2 incomplete request_hash: fixed by canonical JSON full payload hash.
B3 stale generation overwrite: fixed by status lock/check before save.
M1 legacy HoraryQuota: removed.
```

Remaining work is now primarily product UX/location polish plus final verification of tests/grep gates.
