# Review: Horary UX/location after commit a23feb6

Date: 2026-06-09
Reviewed commit: `a23feb69c84cab3711a08c044c65b8d292b6145f`
Source TZ: `docs/16_Horary_questions_TZ.md`
Related packet: `W-HORARY-UX-LOCATION: question place, category fix, premium processing`

## Verdict

Status: **ACCEPTED WITH MINOR FOLLOW-UP**.

The original UX issue was that the horary form did not show the place of the question at all. Commit `a23feb6` fixes that: the form now has a `Момент вопроса` block with both time and place, allows editing both, sends `questionLat/questionLon/questionLocationName`, persists `question_location_name`, and displays it on the answer card.

Important product decision confirmed after review:

```text
For MVP, it is acceptable to take the default question place from the user's profile current location.
Browser/device geolocation is NOT required for this packet.
```

So this review does not require device geolocation. The remaining follow-up is small: make sure the user cannot submit a horary question without a usable question place/coordinates, and polish a couple of copy/details.

---

# What is accepted

## A1. Place of question is now visible

The horary form now shows a context block:

```text
Момент вопроса — важно для расчёта карты
Время: ...
Место: ...
```

This closes the original gap: previously the form showed time but not place.

## A2. Place can be changed manually

The `Место` row has `Изменить место` / `Указать место`, and the inline editor uses `CityPicker`.

This satisfies the product requirement:

```text
Show question place and allow changing it.
```

## A3. Profile current location as default is acceptable

The current fallback is:

```text
1. profile current location
2. profile birth location
3. unknown
```

This is acceptable for MVP, because the user confirmed that taking current place from profile is normal.

No browser/device geolocation is required in this packet.

## A4. Location is sent to backend

The frontend submits:

```ts
questionLat
questionLon
questionLocationName
```

The backend schema/model now includes:

```text
question_location_name
```

and the generated contracts include `questionLocationName` in both create/read shapes.

## A5. Category chip behavior was fixed

Category chips are now single-select. Clicking another category switches selection; clicking the same category keeps it selected.

This fixes the feedback that after choosing `Отношения`, other category clicks did not visibly change the selection.

## A6. CTA copy was improved

Submit CTA is now:

```text
Получить ответ карты
```

This matches the approved direction and removes the generic `Спросить звёзды` button.

## A7. Premium processing state was added

The processing state now uses:

- orbit/ring visual;
- title `Строим карту вопроса`;
- copy about time/place/topic;
- steps:
  1. `Фиксируем момент`
  2. `Строим карту`
  3. `Формулируем ответ`

This satisfies the direction for a more beautiful, female-audience-friendly loading state.

---

# Minor follow-ups

## F1. Disable submit when place coordinates are missing

### Current concern

`HoraryForm.isValid` currently checks:

```ts
text.trim().length >= 5
text.length <= 500
hasSpendableCredit
```

It does not explicitly require `questionLat/questionLon`.

If profile current location has a city name but no coordinates, or if the user clears/manual-types a city without selecting a result, the form may submit without a usable place.

### Required fix

For MVP, require coordinates before submit:

```ts
const hasQuestionPlace =
  typeof questionLat === "number" && typeof questionLon === "number"

const isValid =
  text.trim().length >= 5 &&
  text.length <= 500 &&
  hasSpendableCredit &&
  hasQuestionPlace
```

If place is missing, show helper text:

```text
Укажи место вопроса — оно нужно для построения карты.
```

### Acceptance

```text
Given no questionLat/questionLon
Then submit button is disabled
And helper text asks user to set question place
```

```text
Given selected city has lat/lon
Then submit button can become enabled
And payload includes questionLat/questionLon/questionLocationName
```

## F2. When user selects another city, keep timezone consistent

### Current concern

The form initializes timezone from browser:

```ts
Intl.DateTimeFormat().resolvedOptions().timeZone
```

When user changes place through `CityPicker`, selected city can contain `timezone`, but `HoraryTimeConfirm` does not update its `timezone` state from `selectedCity.timezone`.

### Product decision

For MVP, either behavior is acceptable if it is explicit:

- Option A: time is local to selected question place;
- Option B: time is the user's browser/device local time, while place only changes chart location.

Recommended simple fix: update timezone to `city.timezone` when available, because the block visually presents time + place as one combined moment.

### Acceptance

```text
Given browser timezone Europe/Moscow
When user selects Amsterdam with timezone Europe/Amsterdam
Then displayed/submitted clientTimezone becomes Europe/Amsterdam
```

If this is intentionally not done, document in UI/TZ that the question time remains browser-local even when place changes.

## F3. Align long-running toast copy

`HoraryProgress` long-running copy says:

```text
Ответ формируется дольше обычного. Мы сохраним вопрос и покажем ответ, когда карта будет готова.
```

`HoraryScreen.pollStatus()` toast still says:

```text
Ответ формируется дольше обычного. Мы покажем его, когда он будет готов.
```

Recommended to align toast copy with the stronger product copy:

```text
Ответ формируется дольше обычного. Мы сохраним вопрос и покажем ответ, когда карта будет готова.
```

## F4. Polish remaining generic “звёздам” copy

The main header paragraph still says:

```text
Задай конкретный вопрос звёздам...
```

CTA is already fixed, so this is not a blocker. But for consistency, replace with:

```text
Задай конкретный вопрос и получи ответ карты на момент вопроса — с пояснением, сроками и практическим выводом.
```

---

# Required next small packet

Packet title:

```text
W-HORARY-UX-LOCATION-FOLLOWUP: require usable place and polish copy
```

Scope:

```text
components/readings/horary/horary-form.tsx
components/readings/horary/horary-time-confirm.tsx
components/readings/horary/horary-screen.tsx
```

Optional tests:

```text
components/readings/horary/*.test.tsx
```

Required changes:

1. Add `hasQuestionPlace` validation based on `questionLat/questionLon`.
2. Show helper text when place is missing.
3. Update timezone when selected city has timezone, or document why not.
4. Align long-running toast copy.
5. Replace remaining header `звёздам` copy with card/question wording.

---

# Final acceptance checklist

```text
[ ] Place is visible on form.
[ ] Place can be changed manually.
[ ] Default place can come from profile current location.
[ ] Browser/device geolocation is not required for MVP.
[ ] Submit is disabled if there is no usable question place/coordinates.
[ ] Payload includes questionLat/questionLon/questionLocationName when known.
[ ] Answer card displays questionLocationName when available.
[ ] Category chips switch reliably.
[ ] CTA is `Получить ответ карты`.
[ ] Processing state is premium/branded.
[ ] Long-running copy is aligned.
```

## Final note

The main UX request is implemented. The follow-up is not a rewrite; it is a small validation/copy pass to prevent submitting a paid/limited horary question without a usable chart location.
