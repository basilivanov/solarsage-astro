# Review: W-NATAL-REDESIGN + W-HORARY-SUBMIT-FIX

Date: 2026-06-09
Requested scope: review completed natal redesign + horary submit fix
Verdict: BLOCKED — implementation commit not visible in GitHub connector

## What was checked

The user reported that both parts were completed:

1. Horary submit flow fixed:
   - button click always fires;
   - blocked reason shown;
   - inline submit API errors;
   - `createHoraryQuestion` throws `HoraryApiError`;
   - submit label changed to `Считаем карту...`.

2. Natal landing redesigned:
   - hero redesigned;
   - English removed;
   - compact visible chart section;
   - calculation depth uses structured Path B;
   - top-3 spheres/planets with expanders;
   - locked chapters compact;
   - backend text builders polished.

## Repository state found

The visible `main` branch head through the GitHub connector is still:

- `a9524a2e0da1c906224fca575f446720ff464ee4`
- commit message: `Add TZ for natal redesign and horary submit fix`

That commit only adds the task document:

- `docs/work/2026-06-09_natal_redesign_and_horary_submit_fix_TZ.md`

No later implementation commit was visible through the connector at review time.

## Searches performed

Searched for implementation indicators in commits/files, including:

- `horary submit natal redesign`
- `Считаем карту`
- `blockedReason`
- `submitError`
- `Показать все сферы`
- `Показать все планеты`

The connector did not find a visible implementation commit containing these changes on the accessible repository state. Search results pointed back to the TZ document or older commits only.

## Review decision

BLOCKED.

I cannot honestly accept or reject the claimed implementation because the actual implementation commit is not visible in the connected GitHub repository state.

## Required next action

Provide one of the following:

1. exact commit SHA with the implementation;
2. branch name where the implementation was pushed;
3. PR number if it was pushed to a pull request;
4. push the implementation to `main` / accessible branch and ask for review again.

## What the next review should verify

Once the implementation commit is visible, review these acceptance points.

### Horary submit

- button click works even when form is invalid;
- invalid click shows a visible blocked reason;
- valid submit changes label to `Считаем карту...`;
- `createHoraryQuestion()` throws typed `HoraryApiError`;
- API create errors are shown inline;
- created question appears immediately;
- processing state/polling starts;
- tests cover invalid click, API error, successful create, processing UI.

### Natal landing

- no visible English labels/signs remain;
- hero is compact and polished;
- signs are Russian;
- calculation depth no longer uses weak `50 факторов карты` as the main headline;
- spheres/planets are top-3 by default with expanders;
- locked chapters are compact;
- backend texts no longer repeat placeholder phrases;
- tests cover no-English UI, Russian signs, compact sections, 8 report topics, CTA safety.
