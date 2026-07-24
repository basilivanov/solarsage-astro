# Slice 12 — pure onboarding profile prefill primitive

## Локальная цель

Научить onboarding reducer детерминированно и без side effects создавать
initial state из уже загруженного Profile. UI/routing/promo пока не менять.

## Разрешённые файлы

- `lib/reducers/onboarding-reducer.ts`;
- `__tests__/reducers/onboarding-reducer.test.ts`.

## Public helper

Добавить pure function с typed input из canonical frontend Profile contract:

```ts
onboardingStateFromProfile(profile: Profile): OnboardingState
```

Rules:

- existing birth date/time/gender/location преобразуются без timezone/date
  drift;
- отсутствующее время -> `{hours:"", minutes:"", unknown:true}`;
- birth location сохраняет city/lat/lon/timezone, если они доступны;
- current/birthday locations и same-as flags вычисляются детерминированно;
- initial step остаётся `welcome`; выбор required step делает следующий UI
  slice;
- исходный profile/state не мутируется;
- никакого localStorage/fetch/log.

Ordinary `initialOnboardingState`, reducer events и `unknown time is valid`
semantics остаются backward-compatible.

## Tests

- complete profile roundtrip into reducer state;
- unknown time;
- partial profile/null locations;
- location equality/same-as flags;
- input immutability;
- ordinary initial state/reducer tests unchanged.

## Targeted verification

```bash
npx vitest run __tests__/reducers/onboarding-reducer.test.ts
```

## Out of scope

React hydration, promo query, exact-time UI, API writes, navigation. Не
коммитить и не пушить.
