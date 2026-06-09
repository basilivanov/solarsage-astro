# TZ: W-NATAL-REDESIGN + W-HORARY-SUBMIT-FIX

Date: 2026-06-09
Status: ready for coder
Priority: high
Scope: `/readings/natal` preview landing redesign + horary submit/debug flow

## 1. Why this packet exists

There are two visible product problems.

### A. Natal preview / mini-landing looks weak and messy

Based on the supplied screenshots:

- the screen does not feel premium or sellable;
- there are leftover English labels and zodiac names: `NATAL PREVIEW`, `Cancer`, `Scorpio`, `Leo`, `Libra`, `Sagittarius`;
- text like `для него` and repeated generic sentences look unpolished;
- the page feels like a raw data/debug dump, not a landing;
- too many similar cards create visual noise;
- `50 факторов карты` looks weak and probably undersells the real calculation;
- planet cards and locked report cards are too repetitive;
- CTA exists but the page before it does not sell strongly enough.

### B. Horary submit still feels broken

User reports:

- tapping the horary calculation button gives no visible result;
- user cannot calculate a horary question;
- from UX perspective the primary flow feels dead.

This must be treated as a broken conversion-critical path.

---

# PART I — Natal landing redesign

## 2. Product goal

Turn `/readings/natal` into a short, clean, premium mini-landing that:

1. quickly shows “this is about me”;
2. looks polished and feminine/premium;
3. removes raw/debug feeling;
4. explains the value of the full report;
5. drives desire to unlock the full natal report for 999 ₽.

This screen must not look like a data table.

## 3. Current problems to fix

### Visual / UX

- too many similar cards;
- weak hierarchy;
- too much text before the page has sold the value;
- planets section is bulky;
- locked chapters are a long repetitive wall;
- CTA comes after visual fatigue.

### Content

- remove all English user-facing labels/signs;
- replace awkward generated phrases;
- avoid technical scores like `+4.96` unless they clearly help;
- do not show `50 факторов карты` as the main selling proof if it weakens perceived value.

### Product structure

The page should not show everything at equal weight. It should guide the user:

1. emotional hook;
2. proof that the chart is personal;
3. concise value preview;
4. full-report promise;
5. CTA.

## 4. New target page structure

### 4.1 Hero card

Required:

- title: `Твоя натальная карта`
- subtitle example:
  - `Твой характер, отношения, сильные стороны и внутренние сценарии — по точным данным рождения.`
- compact badge row:
  - `ASC в Раке`
  - `Солнце в Скорпионе`
  - `Луна во Льве`
- birth city only if useful.

Forbidden:

- `NATAL PREVIEW`
- English zodiac signs;
- weird hero copy like `для него`.

### 4.2 Short personal insight card

A compact, beautiful summary, 2–4 sentences max.

Example tone:

```text
Ты считываешь мир глубоко и тонко. В карте заметно сочетание чувствительности, внутренней силы и выраженной личной воли. Сильнее всего у тебя читаются темы тела, ресурса и личного проявления.
```

### 4.3 “Что уже видно по карте”

Replace huge ASC/Sun/Moon cards with compact chips or mini-cards:

- Асцендент — как ты входишь в контакт;
- Солнце — твой базовый вектор;
- Луна — эмоциональный отклик.

Keep explanations short.

### 4.4 “Глубина расчёта”

Do not force `50 факторов карты` as a headline if it undersells the product.

Choose one of two honest paths:

#### Path A — stronger truthful numeric stat

If backend can honestly compute a stronger total, show a bucket label:

- `200+ факторов карты`
- `300+ факторов карты`
- `350+ факторов карты`

#### Path B — if only ~50 factors are currently provable

Do not make the number the main hero proof. Instead show structured depth:

```text
В разборе учитываются:
• планеты и дома
• аспекты и акценты карты
• приоритетные жизненные сферы
• сильные и напряжённые зоны
```

Rules:

- no fake `300+`;
- no weak headline if it hurts conversion;
- presentation must be truthful and sellable.

### 4.5 “Сильнее всего у тебя проявлены”

Show top 3 spheres by default, not 7 full cards.

Each item:

- sphere title;
- score only if it helps;
- 1–2 lines of human explanation.

Optional: `Показать все сферы` expander.

### 4.6 Planets block

Current planets grid is too verbose.

New rule:

- show top 3 key planets by default;
- each with planet name, sign + house, one human explanation;
- hide technical score pills unless clearly useful.

Optional: `Показать все планеты`.

### 4.7 Full report preview

Replace long heavy wall of locked cards with a lighter compact section:

Title: `Что войдёт в полный отчёт`

Topics:

- Отношения и близость;
- Предназначение и реализация;
- Деньги и стратегия роста;
- Карьера и публичная позиция;
- Здоровье и энергия тела;
- Семья и род;
- Творчество и самовыражение;
- Духовный путь и трансформация.

Cards/list must be visually lighter than current implementation.

### 4.8 Value bullets

Max 3 bullets.

Example:

```text
✦ Поймёшь, где в карте ты уже проявлен сильнее всего.
✦ Увидишь приоритетные сферы, а не разрозненные факты.
✦ Получишь связный разбор карты, домов, планет и жизненных тем.
```

Use gender-aware wording.

### 4.9 CTA

Button:

```text
Полный отчёт за 999 ₽
```

If payment is not connected:

- keep it visually premium;
- but disabled/safe;
- no broken payment route.

## 5. Natal content rules

### Remove English completely

Must not remain:

- `NATAL PREVIEW`
- `Cancer`
- `Scorpio`
- `Leo`
- `Libra`
- `Sagittarius`
- other English signs in visible UI.

Use Russian signs:

- Рак;
- Скорпион;
- Лев;
- Весы;
- Стрелец.

### Rewrite weak/repetitive phrases

Remove/replace phrases like:

- `через эту планету особенно проявлен личный паттерн карты`;
- `для него`;
- repeated card copy that differs only by planet/sphere name.

Need natural Russian product text.

### Gender wording

Keep correct gender-aware Russian:

- male: `ты собран`, `проявлен`;
- female: `ты собрана`, `проявлена`.

No awkward inserted phrases in hero.

## 6. Natal acceptance criteria

Done when:

- page no longer looks like raw/debug output;
- no English remains in visible natal UI;
- top section is short, emotional, and clean;
- placement info is compact;
- only top spheres/planets are shown by default;
- full report section is compact and elegant;
- CTA clearly sells the 999 ₽ report;
- screenshots show a materially better premium mini-landing.

---

# PART II — Horary submit / calculation fix

## 7. Product problem

User says pressing the horary calculation button still feels like nothing happens. This is a primary paid/conversion flow and must be fixed before further polish.

## 8. Root causes to investigate

Coder must verify, not guess:

### RC1 — submit handler is not firing

Possible causes:

- button disabled unexpectedly;
- form validation blocks silently;
- `onSubmit` not reached.

### RC2 — request fires but UI does not update

Possible causes:

- create request succeeds;
- question created;
- no processing card appears;
- question not inserted into list;
- user sees no feedback.

### RC3 — request fails

Possible causes:

- backend validation;
- no credits;
- missing location;
- auth/session problem;
- idempotency conflict.

### RC4 — question created but generation does not start

Possible causes:

- background task not enqueued;
- generator failed;
- polling not attached;
- response insufficient for UI.

## 9. Required debugging evidence

Coder must provide evidence for:

1. click reaches submit handler;
2. exact payload sent to `createHoraryQuestion()`;
3. exact backend response;
4. whether new question row is created;
5. whether new question is inserted into UI immediately;
6. whether polling starts;
7. whether generation task starts;
8. if failure occurs, exact stage and error code.

## 10. Required horary UX behavior

### On click

Immediately:

- button loading state appears;
- label changes to something like `Считаем карту...`;
- user sees that action was accepted or is blocked with a reason.

### On successful create

- new question appears at the top immediately;
- processing state is visible;
- polling starts.

### If blocked

No silent no-op. Show clear reason:

- `Напиши вопрос`;
- `Укажи место вопроса`;
- `Нужен доступный хорарный вопрос`;
- etc.

### If create fails

Show honest user-facing error.

## 11. Horary implementation tasks

Frontend:

1. ensure click triggers submit;
2. ensure disabled/loading state works;
3. surface blocked reasons visibly;
4. surface create API errors visibly;
5. insert created question into history immediately;
6. show processing card reliably;
7. start polling reliably.

Backend:

1. verify create endpoint accepts current payload;
2. verify status transitions;
3. verify background generation starts;
4. record exact failure stage if generation fails;
5. ensure create response contains enough data for immediate UI rendering.

## 12. Horary acceptance criteria

Done when:

- tapping the horary calculation button always gives visible feedback;
- valid submit creates/starts visible processing;
- invalid submit shows reason;
- create failure shows real error;
- processing/failure states are honest;
- “ничего не происходит” is no longer reproducible.

## 13. Tests required

Natal:

- no English visible in natal UI;
- hero renders Russian signs;
- compact top sections render;
- full report section renders 8 topics;
- CTA present and safe.

Horary:

- button click triggers submit;
- loading state appears;
- invalid form shows reason;
- create API error shows real message;
- successful create inserts question into history;
- successful create starts polling;
- processing card appears.

## 14. Deliverables expected

Coder must provide:

1. diff summary;
2. screenshots of new natal landing:
   - hero/top;
   - spheres;
   - full report section;
   - CTA;
3. proof that English labels/signs are removed;
4. explanation of calculation-depth presentation;
5. horary debug report:
   - where flow was broken;
   - what was fixed;
   - evidence click → create → processing;
6. frontend test results;
7. backend test results.

## 15. Priority order

1. Fix horary submit / “nothing happens”.
2. Redesign natal landing.
