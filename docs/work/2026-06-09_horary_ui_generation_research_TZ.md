# Research + TZ: W-HORARY-UX-GENERATION-REPAIR

Date: 2026-06-09
Status: ready for coder
Source: user screenshot + code review
Scope: horary question submit UX, generation progress, history cards, failed question handling, answer depth
Related: `docs/FAILURE_HANDLING_CANON.md`, `docs/work/2026-06-09_horary_answer_quality_TZ.md`, `docs/work/2026-06-09_horary_quality_followup_review.md`

## 1. User-visible problem

From the current app screen:

1. The latest horary question in history shows `Ответ: Ошибка`.
2. The submit CTA behavior is unclear: user taps the button and does not understand whether anything started.
3. A newly submitted question does not reliably appear in history immediately as “processing”.
4. The existing progress experience is either not visible in the current screen context or replaces the whole screen too abruptly.
5. The successful answer screen feels too thin/short (“куцо”) for a paid/monetizable horary feature.
6. The product needs a beautiful soft progress state, not a silent wait or plain error.

## 2. Code facts found

### 2.1 Existing progress component exists, but is not integrated as inline history feedback

`components/readings/horary/horary-progress.tsx` already exists and has a nice orbit-style animation, three steps, synthetic progress, and long-running state.

Current steps:

- `Фиксируем момент`
- `Строим карту`
- `Формулируем ответ`

It is rendered as a large full-screen/full-section state, not as an inline card in the question history.

### 2.2 Main horary screen only shows progress via global `submitting`

`components/readings/horary/horary-screen.tsx`:

- `handleSubmit` sets `submitting=true`;
- sends `createHoraryQuestion`;
- starts `pollStatus(q.id)`;
- while `submitting` is true, the whole screen returns `<HoraryProgress />`;
- it does not immediately insert the returned processing question into `questions` history;
- it does not show an inline processing card at the top of history.

Implication:

- If creation is slow, fails, or the UI context changes, the user gets weak feedback.
- If the user expects the history list to update, it looks like “nothing happened”.

### 2.3 Polling is only attached to a freshly submitted question

`pollStatus(id)` runs only after `handleSubmit` succeeds.

Problems:

- Existing `processing` questions from a previous visit are not continuously polled on the main history screen.
- The detail page fetches once and then shows `<HoraryProgress />` for unanswered questions, but does not poll until the answer is ready.
- Statuses `expired` and `refunded` are not handled in the main polling branch.
- Polling errors are only logged and do not surface a user-visible stable state.

### 2.4 API client hides important error reasons

`lib/api/horary.ts` currently maps only HTTP 403 to `Horary quota exceeded`.

Backend returns:

- `402` with detail `NO_HORARY_CREDITS`;
- `409` with detail `IDEMPOTENCY_CONFLICT`;
- other errors may include useful `detail`.

The frontend should parse backend `detail` and show a clear Russian message.

### 2.5 Failed questions are honest, but too uninformative

History card maps `failed`/`expired` to `Ответ: Ошибка`.

Detail page correctly says:

> Не удалось построить ответ. Мы не будем показывать общий текст вместо реального разбора.

This is correct by failure-handling canon, but the list card is too terse. It should show whether the spend was returned and suggest retrying.

### 2.6 Answer depth is not enforced enough

`LLMService.generate_horary_answer` asks for a structured multi-block answer, and `_validate_horary_blocks` checks required block types.

But validator mostly checks presence of block types, not minimum depth/length. A technically valid answer can still be too short.

Need stricter “quality gate” for generated horary blocks:

- enough paragraphs;
- non-empty lead;
- explanation length minimum;
- testimonies must contain meaningful explanations;
- advice and summary should not be one-liners.

If generated content is too short, retry. If still too short, fail/refund rather than saving a thin answer as successful.

## 3. Likely root causes to verify in production

### RC1 — actual generation failures

The latest history card shows `failed`. Backend can fail because of:

- LLM provider/key/config missing;
- LLM invalid JSON;
- block schema validation failure;
- SolarSage sidecar error;
- profile/location missing;
- background task exception.

Coder must inspect production/server logs around the failed question time and identify the exact error stage.

Search log markers:

- `[Horary Generator] LLM generation failed`
- `[Horary Generator] Error generating answer`
- `[Horary Refund]`
- SolarSage client errors
- HTTP 4xx/5xx for `/api/horary/questions`

### RC2 — user sees no progress because processing is not represented inline

Even if generation works, the current UX makes the flow feel broken:

- submit does not create an immediate visible card in the history list;
- full-screen progress may not be obvious in the Telegram mini app/bottom sheet context;
- history is refreshed only after timeout/failure, not immediately after creation.

### RC3 — detail route can get stuck on progress

If the user opens a processing question directly, detail page fetches once and does not poll. It can show progress forever until manual refresh.

## 4. Required product behavior

### 4.1 On submit

After tapping `Получить ответ карты`:

1. Disable button and show button-local loading immediately.
2. On successful create, immediately add the returned question to the top of history as a processing card.
3. Show a beautiful inline progress card/card overlay.
4. Poll status until answered/failed/expired/timeout.
5. If answered, either:
   - route to detail automatically; or
   - keep on list and show “Ответ готов” card with a subtle animation.

Preferred MVP behavior:

- stay on the horary list screen;
- insert processing card at top;
- when ready, transform it into answered card;
- user taps `Подробнее`.

This makes the history feel alive and avoids “nothing happened”.

### 4.2 Inline processing card

Create component:

`components/readings/horary/horary-processing-card.tsx`

Visual style:

- soft card;
- light gradient/surface;
- orbit/sparkle animation;
- progress bar 0→95%;
- steps:
  1. `Фиксируем момент вопроса`
  2. `Строим карту`
  3. `Сверяем сигнификаторы`
  4. `Собираем ответ`
- copy should be calm/feminine-friendly.

Example copy:

```text
Карта вопроса строится
Мы фиксируем момент, место и тему вопроса. Обычно это занимает несколько секунд.
```

Long-running copy after 30 seconds:

```text
Ответ готовится дольше обычного
Мы сохранили вопрос. Можно закрыть экран — ответ появится в истории, когда расчёт завершится.
```

### 4.3 Failed card in history

Current `Ответ: Ошибка` is too terse.

Improve failed history card:

- keep red/rose visual state;
- show `Не удалось построить ответ`;
- if `creditRefunded=true`, show small line `Списание возвращено`;
- if `creditRefunded=false`, show `Списание не возвращалось` only if this is correct and not confusing; otherwise omit;
- CTA: `Попробовать ещё раз` or `Подробнее`.

Do not show generic answer content.

### 4.4 Answer screen depth

Successful horary result must feel like a real paid-grade answer.

Minimum structure:

1. Verdict card.
2. Short direct answer.
3. “Почему так” explanation.
4. Significators: who/what represents user and topic.
5. Evidence for.
6. Evidence against / doubts.
7. Timing block.
8. What can change the outcome.
9. Practical advice.
10. Final summary.

UI should show clear sections/cards, not a sparse list of tiny paragraphs.

## 5. Backend requirements

### 5.1 Store failure reason

Add fields to `HoraryQuestion` if not already present:

```python
failure_stage: str | None
failure_code: str | None
failure_message: str | None  # internal/dev-safe, do not expose raw secrets
```

Suggested stages:

- `profile`
- `sidecar`
- `engine`
- `llm_provider`
- `llm_contract`
- `timeout`
- `unknown`

API may expose safe public code/message:

```python
public_error_code: str | None
public_error_message: str | None
```

Do not expose raw provider error text to users.

### 5.2 Improve status handling

Question status remains:

- `processing`
- `answered`
- `failed`
- `expired`

Do not introduce fake `refunded` status as a question status. Refund is already represented by `refund_status` / `creditRefunded`.

### 5.3 Quality gate for generated answer

Strengthen `_validate_horary_blocks` or add `_validate_horary_quality`:

Rules:

- Required block types: `verdict_card`, `lead`, `testimonies`, `timing`, `callout`.
- Minimum total blocks: 7.
- Lead text length: at least 60 chars.
- At least 2 paragraph blocks, unless a structured equivalent is present.
- Confidence explanation length: at least 60 chars.
- Timing text length: at least 60 chars.
- Callout advice length: at least 80 chars.
- Testimony item explanations must not be empty.
- Reject generic/filler phrases.

If quality gate fails:

- retry LLM;
- if still fails, mark question failed and refund where refundable;
- do not save thin answer as successful.

### 5.4 Diagnose production failure

Coder must identify why the actual failed card happened.

Expected evidence:

- log excerpt or local reproduction showing exact failure stage;
- if env/provider issue, fix env/config or document deployment setting;
- if schema/validation issue, add test and fix prompt/validator;
- if sidecar issue, add clear public error and retry policy.

## 6. Frontend requirements

### 6.1 `lib/api/horary.ts`

Parse backend errors properly.

Map:

- `402 / NO_HORARY_CREDITS` → `Недостаточно хорарных вопросов`
- `409 / IDEMPOTENCY_CONFLICT` → `Этот запрос уже был отправлен с другими данными. Попробуй ещё раз.`
- network error → `Не удалось связаться с сервером. Попробуй ещё раз.`
- fallback generic → `Не удалось отправить вопрос.`

### 6.2 `HoraryScreen`

Change submit flow:

- Keep list screen visible after submit.
- Set `activeQuestionId` and `activeQuestionStartedAt`.
- Immediately insert returned question into `questions` list if not present.
- Render processing card for processing question at top.
- Poll all visible `processing` questions, not only the fresh one.
- On answered, update that card in-place and optionally show toast `Ответ готов`.
- On failed/expired, update card in-place and show honest failure state.

### 6.3 `HoraryAnswerPage`

If loaded question is `processing`, start polling on detail page too.

Rules:

- Poll every 2 seconds for up to 30 seconds.
- After 30 seconds, keep beautiful long-running state and offer back to history.
- If answered, render answer without manual refresh.
- If failed/expired, render error state.

### 6.4 `HoraryQuestionCard`

Improve states:

- `processing`: show animated mini progress, not only `Ответ: Расчёт...`.
- `failed`: show `Не удалось построить ответ`, not only `Ошибка`.
- `failed + creditRefunded`: show `Списание возвращено`.
- `answered`: keep clear verdict.

### 6.5 Button feedback

`HoraryForm` button must explain why disabled.

Current validation requires:

- text length;
- spendable credit;
- question place.

Add visible disabled reasons:

- no text → `Напиши вопрос минимум 5 символов`;
- no place → `Укажи место вопроса`;
- no credits → `Нужен хорарный вопрос на балансе`.

When submit starts, button label:

`Отправляем вопрос...`

## 7. UX copy

Processing:

```text
Карта вопроса строится
Мы фиксируем момент, место и тему вопроса. Обычно это занимает несколько секунд.
```

Long-running:

```text
Ответ готовится дольше обычного
Мы сохранили вопрос. Можно закрыть экран — ответ появится в истории, когда расчёт завершится.
```

Failure:

```text
Не удалось построить ответ
Мы не будем показывать общий текст вместо реального разбора. Попробуй задать вопрос ещё раз.
```

Refund:

```text
Списание возвращено.
```

Ready:

```text
Ответ готов
Карта уже разобрана — можно открыть подробности.
```

## 8. Tests

### Frontend tests

1. Submit success inserts processing card at top immediately.
2. Processing card shows orbit/progress/steps.
3. Answered poll update changes card to `Ответ: Да/Нет/Возможно`.
4. Failed poll update changes card to failure state.
5. Failed + `creditRefunded=true` shows `Списание возвращено`.
6. Detail page polls processing question and renders answer when ready.
7. Detail page polls processing question and renders failed state when failed.
8. Disabled button reasons are visible.
9. `NO_HORARY_CREDITS` maps to Russian user-facing message.
10. No broken silent state after click.

### Backend tests

1. Failed generation stores `failure_stage` and `failure_code`.
2. LLM short/thin response fails quality gate and retries.
3. Repeated thin response marks failed and refunds when refundable.
4. Good detailed response passes quality gate.
5. API response exposes safe public error info, not raw provider secrets.

### Integration/smoke

1. Create question → card appears as processing in history without page refresh.
2. Processing → answered updates without manual refresh.
3. Processing → failed updates without manual refresh and shows refund if applicable.
4. Opening `/readings/horary/{id}` while processing updates automatically.

## 9. Acceptance criteria

- User always gets immediate visible feedback after tapping submit.
- Newly created question appears in history immediately.
- Processing state is beautiful, soft, and clearly branded.
- Existing processing questions continue polling after page reload/revisit.
- Detail page does not get stuck forever on progress.
- Failed questions explain failure honestly and show refund state if applicable.
- Successful answers are detailed enough for a monetizable horary product.
- Thin/short LLM answers are rejected and retried; if still bad, fail/refund.
- No generic fallback answer is shown.
- Existing horary quality guard remains green.

## 10. Expected evidence from coder

Coder must provide:

1. Screenshot/DOM evidence of inline processing card.
2. Screenshot/DOM evidence of long-running state.
3. Screenshot/DOM evidence of failed card with refund notice.
4. Screenshot/DOM evidence of successful detailed answer.
5. Frontend test command/count.
6. Backend test command/count.
7. Guardrails output.
8. Production/local diagnosis of why the current latest card failed.
