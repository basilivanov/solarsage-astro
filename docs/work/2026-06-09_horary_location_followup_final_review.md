# Final review: Horary location follow-up

Date: 2026-06-09
Reviewed scope: follow-up tasks from `docs/work/2026-06-09_horary_a23feb6_review_action_plan.md`
Status: **ACCEPTED**

## Verdict

The follow-up packet is accepted.

The previously requested fixes F1–F4 are implemented:

```text
F1: disable submit without usable question coordinates — done
F2: sync timezone from selected city — done
F3: align long-running copy — done
F4: remove remaining generic “звёздам” copy — done
```

The horary UX/location feature is now acceptable for MVP.

---

## F1. Location validation

Accepted.

`HoraryForm` now calculates:

```ts
const hasQuestionPlace = typeof questionLat === "number" && typeof questionLon === "number"
const isValid = text.trim().length >= 5 && text.length <= 500 && hasSpendableCredit && hasQuestionPlace
```

This means the submit button is disabled unless a usable question place exists.

When coordinates are missing, the form shows:

```text
Укажи место вопроса — оно нужно для построения карты.
```

This closes the risk of spending a horary credit without a chart location.

---

## F2. Timezone synchronization

Accepted.

`HoraryTimeConfirm` now accepts profile timezones:

```ts
profileCurrentTz
profileBirthTz
```

and stores them on the resolved city fallback.

It also syncs timezone when the selected city changes:

```ts
if (selectedCity?.timezone) {
  setTimezone(selectedCity.timezone)
}
```

This resolves the previous mismatch where changing the question place could leave the old browser timezone in the payload.

MVP product decision remains:

```text
Default question place may come from profile current location.
Browser/device geolocation is not required for MVP.
```

---

## F3. Long-running copy alignment

Accepted.

The 30-second polling toast now matches the stronger progress-screen copy:

```text
Ответ формируется дольше обычного. Мы сохраним вопрос и покажем ответ, когда карта будет готова.
```

This is consistent with the behavior that the question is already saved and can finish later.

---

## F4. Copy polish

Accepted.

Remaining generic “звёздам” copy was removed from the horary screen/form.

The section intro now says:

```text
Задай конкретный вопрос и получи ответ карты на момент вопроса — с пояснением, сроками и практическим выводом.
```

The textarea label is now:

```text
Твой вопрос
```

Submit CTA remains:

```text
Получить ответ карты
```

A repository search for the previously unwanted wording returned no hits for the horary UI copy.

---

## Accepted current behavior

The MVP behavior is:

```text
1. The form shows question time and question place.
2. Default place is taken from profile current location.
3. If profile current location is unavailable, profile birth location may be used.
4. User can change the question place manually through CityPicker.
5. Submit is disabled if no coordinates are available.
6. Payload includes questionLat/questionLon/questionLocationName when known.
7. Timezone is synced from selected city when available.
8. Processing state is premium/branded.
```

This matches the agreed product direction.

---

## Remaining optional polish, not blocking

These are optional and should not block MVP acceptance:

1. Add component tests for `HoraryForm` / `HoraryTimeConfirm`:
   - no coordinates => submit disabled;
   - selected city with coordinates => submit enabled;
   - selecting a city updates timezone;
   - warning text appears when no place is available.
2. Add a tiny source label if desired:
   - `из профиля`;
   - `выбрано вручную`.
3. Improve empty-country formatting if any profile city comes without country.

---

## Final acceptance checklist

```text
[x] Place is visible on the form.
[x] Place can be changed manually.
[x] Default place can come from profile current location.
[x] Browser/device geolocation is not required for MVP.
[x] Submit is disabled if there is no usable question place/coordinates.
[x] Payload includes questionLat/questionLon/questionLocationName when known.
[x] Answer card displays questionLocationName when available.
[x] Category chips switch reliably.
[x] CTA is “Получить ответ карты”.
[x] Processing state is premium/branded.
[x] Long-running copy is aligned.
[x] Generic “звёздам” copy removed from the reviewed horary UI.
```

## Final note

The horary question flow is now acceptable for MVP from the UX/location perspective. Any next work should move to broader product polish or real user QA rather than another implementation rewrite of this packet.
