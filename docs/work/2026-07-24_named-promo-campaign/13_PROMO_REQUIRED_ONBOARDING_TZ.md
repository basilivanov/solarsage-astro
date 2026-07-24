# Slice 13 — campaign-aware promo profile completion mode

## Локальная цель

Устранить доказанный redirect loop: promo onboarding prefill-ит существующий
профиль; natal campaign требует точное время, access/credits-only campaign —
только base fields. Ordinary onboarding остаётся прежним.

## Preconditions

Приняты slices 04 и 12.

## Разрешённые файлы

- `app/(grace)/onboarding/page.tsx`;
- `components/onboarding/onboarding-flow.tsx`;
- `components/onboarding/step-birth.tsx`;
- `__tests__/components/OnboardingFlow.test.tsx`.

## Safe mode selection

Page читает только exact query:

```text
requiredFor=promoNatal
requiredFor=promoBase
```

Другие values игнорируются. Query не содержит и не читает promo token.
Ordinary `/onboarding` path не меняется.

## Prefill/loading

В обоих promo modes:

- загрузить canonical current profile через existing `useProfile`/API facade;
- пока profile не loaded — `role=status`, `aria-busy=true`;
- передать reducer initial state через `onboardingStateFromProfile`;
- не перетирать уже сохранённые birth/location/gender values;
- load error показывает `role=alert` + retry, не очищает pending token и не
  завершает onboarding.

## Exact-time contract

`OnboardingFlow`/`StepBirth` получают explicit `requireExactBirthTime`:

- checkbox «Не знаю точное время» скрыт/disabled;
- subtitle честно объясняет: точное время необходимо для полного натального
  разбора по промокоду;
- `unknown=true` или пустые hours/minutes делают step invalid;
- finish дополнительно fail-closed проверяет exact time до PUT;
- если user не знает время, он может выйти/закрыть Mini App; redemption/counter
  не расходуются, pending живёт только до конца sessionStorage session.

В `promoBase` mode exact-time flag false: unknown time остаётся допустимым, но
date, birth place/city и gender обязательны. Mode выбирает gate из
server-owned `offer.unlockNatal`, не из token/name.

После успешного PUT обычный page completion route возвращает на current day.
Gate при смене pathname повторно вызывает preview и показывает sheet.

Ordinary mode по-прежнему разрешает unknown time и сохраняет существующий copy.
Не менять backend `is_onboarded` semantics.

## Tests

- ordinary onboarding unknown time остаётся valid;
- promo-natal mode prefilled existing values;
- promo-natal unknown/empty time блокирует next/finish;
- promo-base unknown time valid, missing base field blocks completion;
- exact time сохраняется и completion navigates once;
- no token/sessionStorage value appears in URL/DOM/log;
- load failure does not call PUT/onComplete;
- successful flow не зацикливается обратно на onboarding в gate integration
  fixture.

## Targeted verification

```bash
npx vitest run __tests__/components/OnboardingFlow.test.tsx
```

## Out of scope

Unknown-time natal algorithm, global onboarding redesign, backend promo grant.
Не коммитить и не пушить.
