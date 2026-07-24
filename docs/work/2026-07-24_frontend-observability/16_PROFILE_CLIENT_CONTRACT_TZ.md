# Slice 16 — profile client response contract

## Цель

Подключить generated ProfileRead contract к GET/PUT profile client, сохранив
request body и backend error priority.

## Разрешённые файлы

- `lib/api/profile.ts`
- `__tests__/api/profile-client.test.ts` (новый)
- `__tests__/api/onboarding-payload.test.ts`

## Требования

1. `getProfile` и `updateProfile` используют существующий
   `instrumentedFetch` с response contract:
   - `ProfileRead`/`v1`;
   - `ProfileReadWireSchema.safeParse`;
   - safe issue paths без raw values/messages.
2. После HTTP success оба endpoint делают authoritative
   `ProfileReadWireSchema.parse(await res.json())`.
3. Сохранить exact operations/templates/URLs/credentials/headers/PUT body.
4. Сохранить response error priority: detail string -> detail.message ->
   validation array messages -> endpoint fallback.
5. Полная GRACE module/function/block разметка и реальные emitted events;
   imports только в обычном import section.

## Tests

Новый profile-client test:

- mock `instrumentedFetch` boundary;
- проверить GET и PUT wiring/contracts, включая exact JSON body;
- validator принимает canonical ProfileRead fixture с UUID и отклоняет `{}`;
- invalid HTTP 200 отвергается authoritative parse;
- error priority для string/object/array/fallback сохранён.

Существующий onboarding payload test:

- сохранить assertions request body/timezones;
- привести mock success ProfileRead к generated contract (валидный UUID и
  canonical birth field names), не ослаблять production parse;
- cleanup globals/mocks.

Проверка:

```bash
npx vitest run __tests__/api/profile-client.test.ts __tests__/api/onboarding-payload.test.ts __tests__/hooks/useProfile.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
