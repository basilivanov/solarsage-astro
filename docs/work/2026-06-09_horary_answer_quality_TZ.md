# TZ: W-HORARY-ANSWER-QUALITY-V1

Date: 2026-06-09
Status: ready for coder
Scope: horary answer quality, confidence wording, timing, failure handling

## 1. Goal

Improve horary answers so the user receives a detailed, understandable explanation instead of a short generic response.

Current product problems:

1. Answers are too short and do not explain what is happening.
2. Confidence is shown as if it were probability, often around the same value.
3. Timing often says the same range instead of being derived from the question or chart evidence.
4. If structured answer generation fails, the backend currently can save a generic short answer. This is no longer allowed.

## 2. Canon dependency

This packet must follow:

`docs/FAILURE_HANDLING_CANON.md`

No hidden generic fallback is allowed for user-facing results.

## 3. Product rules

### 3.1. Do not show probability

Horary confidence is not statistical probability.

Replace probability wording with one of:

- `Уверенность разбора: низкая / средняя / высокая`
- `Сила указаний: низкая / средняя / высокая`
- `Карта даёт слабые / умеренные / сильные свидетельства`

Do not show labels like `55% вероятность`.

### 3.2. Confidence levels

Use three public levels:

- low: weak or contradictory evidence;
- medium: mixed evidence or one main testimony without enough confirmation;
- high: clear main testimony plus supporting Moon/context testimony.

A numeric internal score may remain for debugging/storage, but UI must use label + explanation.

### 3.3. Timing must not be hardcoded

Remove hardcoded `2–3 недели` from prompts/templates.

Timing must be derived from:

1. explicit timeframe in the question, if present;
2. applying aspect distance/orb where available;
3. Moon movement/next major testimony where available;
4. category context only as low-confidence support;
5. if no timing evidence exists, return `not_enough_evidence`.

User-facing wording must be honest:

- `Срок по карте не выражен достаточно ясно.`
- `Вопрос задан без временной рамки, а карта не даёт уверенного срока.`

### 3.4. Answer must explain why

A complete answer should contain:

1. short verdict;
2. confidence label and why;
3. what represents the user;
4. what represents the question/topic;
5. evidence for;
6. evidence against;
7. timing;
8. what can change the outcome;
9. practical advice;
10. final summary.

## 4. Backend changes

### 4.1. Replace tuple verdict with structured result

Current engine returns roughly:

`verdict, confidence, involved_planets`

Replace or wrap with structured model:

- verdict: yes/no/maybe;
- confidence_score: internal 0..100;
- confidence_label: low/medium/high;
- confidence_explanation: string;
- involved_planets;
- testimonies_for;
- testimonies_against;
- neutral_factors;
- timing;
- calculation_warnings.

### 4.2. Evidence objects

Each testimony should include:

- type;
- title;
- explanation;
- weight;
- planets involved;
- aspect type if applicable;
- orb if available;
- applying/separating if available;
- source: computed.

Do not invent evidence in LLM.

### 4.3. LLM input

LLM should receive structured evidence, not only verdict/confidence/planet names.

The prompt must instruct:

- use only provided evidence;
- do not invent aspects, houses, timing, or causes;
- return valid JSON only;
- write for a normal user, not an astrologer;
- explain terms briefly.

### 4.4. Remove generic fallback answer

If LLM output is missing, invalid JSON, or fails schema validation:

- do not save generic answer blocks;
- mark question failed/error;
- refund credit if applicable;
- return a user-visible error state.

This replaces the current generic fallback behavior.

## 5. Frontend changes

### 5.1. Verdict card

Update the verdict card:

- remove probability wording;
- show confidence label;
- show one-sentence confidence explanation;
- optionally keep numeric score hidden/dev-only.

### 5.2. Error state

If question status is failed/error:

Show clear text:

`Не удалось построить ответ. Мы не будем показывать общий текст вместо реального разбора. Попробуй задать вопрос ещё раз.`

If backend indicates credit refunded, show:

`Списание возвращено.`

### 5.3. Timing block

Timing block must support:

- known time range;
- low-confidence timing;
- not enough timing evidence.

Do not render hardcoded default timing.

## 6. Tests

Add/update backend tests:

1. LLM invalid JSON => question failed/error, no answer row saved.
2. LLM unavailable => question failed/error, credit refunded when applicable.
3. No timing evidence => timing status `not_enough_evidence`.
4. Explicit timeframe in question is preserved as context.
5. Confidence labels map correctly to low/medium/high.
6. No user-facing probability wording is emitted by API contract.

Add/update frontend tests:

1. Verdict card renders confidence label, not probability.
2. Failed/error question renders honest error state.
3. Timing block renders `not enough evidence` state.
4. No hardcoded `2–3 недели` in rendered output unless backend explicitly sends it as computed/derived timing.

Add grep guard:

- fail if `2–3 недели` appears in horary prompt/template as a default value;
- fail if generic horary fallback text is present in answer generation code;
- fail if UI contains `вероятность` for horary confidence.

## 7. Acceptance criteria

- Horary answers are detailed enough for a non-astrologer to understand the reasoning.
- Confidence is shown as low/medium/high, not event probability.
- Timing is derived or honestly marked as unclear.
- No generic fallback answer is saved on generation failure.
- Failed generation produces honest failed/error state.
- Credit refund behavior remains correct.
- Backend and frontend tests pass.
- Grep guard catches hardcoded default timing and probability wording.

## 8. Out of scope

Do not change payment/subscription.
Do not change Today screen.
Do not change natal frontend.
Do not redesign the whole readings UI.
Do not change horary credit ledger beyond required failure/refund handling.
