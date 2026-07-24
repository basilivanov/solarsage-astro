# Slice 01 — closed start_param routing and storage privacy

## Локальная цель

Без backend promo/API/UI безопасно разделить существующий Telegram
`start_param` на referral, promo intent и ignored. После slice opaque token ни
при каких условиях не должен уйти в referral endpoint, localStorage или log.

## Разрешённые файлы

- новый `lib/telegram/start-param.ts`;
- `hooks/use-telegram-auth.ts`;
- `__tests__/hooks/useTelegramAuth.test.ts`;
- новый `__tests__/lib/start-param.test.ts`.

Другие product/backend files не менять.

## Реализация

1. Создать pure classifier с closed result:

```ts
type StartParamIntent =
  | { kind: "referral"; code: string }
  | { kind: "promo"; token: string }
  | { kind: "ignored" }
```

2. Routing exact:

```text
/^\d+$/ -> referral
/^(?=.{12,16}$)(?=.*[a-hj-km-np-z])[a-hj-km-np-z2-9]+$/ -> promo
else -> ignored
```

3. Export safe constants/helpers for:

```text
PROMO_PENDING_SESSION_KEY = __astro_pending_promo_token
read/write/clear pending token through sessionStorage only
```

Storage helpers validate again on read and never throw. Invalid stored value is
removed. Они не используют localStorage.

4. В `useTelegramAuth` после successful Telegram auth:

- referral intent продолжает текущий auto-claim;
- только numeric referral может попасть в existing referral localStorage key;
- promo intent записывается в sessionStorage и referral call не выполняется;
- ignored не сохраняется и не отправляется;
- старый non-numeric value из referral localStorage удаляется;
- sessionStorage failure не ломает auth;
- sessionStorage failure может писать только typed `frontend.flow_failed` с
  safe `operation=promo.intent_store`/reason code, без token/start param;
- promo processing завершается до `isAuthenticated=true`, чтобы gate в
  следующей волне увидел pending value сразу.

5. Считать/classify start param в начале authenticate effect, до backend auth
fetch и текущей 500ms задержки. После чтения URL fallback удалить только
`tgWebAppStartParam` из visible URL через `history.replaceState`:

- не делать navigation/reload;
- сохранить pathname, hash и остальные query params;
- не помещать raw token в новый URL, log или history state;
- cleanup failure не ломает auth.

6. Удалить raw-sensitive logging:

- не логировать referral code/start param/promo token;
- убрать `authKey.slice(...)`/любой fragment initData;
- safe logs могут содержать только intent kind/boolean, без length для token;
- Error logging не должно присоединять request body или start param.

7. Исправить существующие tests `ref123`/`ref789` на реальные numeric referral
codes. Не менять `/api/referral/claim` contract.

## Acceptance

- `123456` -> referral;
- `m7q4n9x2r5kd` -> promo;
- all-digits никогда не promo;
- 11/17 chars, uppercase, `_`, `-`, `0/o`, `1/l/i`, word-like invalid values -> ignored;
- promo содержит минимум одну букву;
- promo auth вызывает только `/api/auth/telegram`, не `/api/referral/claim`;
- pending token есть в sessionStorage и отсутствует в localStorage;
- `tgWebAppStartParam` исчезает из visible URL, остальные query/hash сохранены;
- invalid param не создаёт storage keys;
- mocked logger calls не содержат raw token/initData fragment;
- auth success/failure semantics вне start-param branch не изменены.

## Targeted verification

```bash
npx vitest run __tests__/lib/start-param.test.ts __tests__/hooks/useTelegramAuth.test.ts
```

## Out of scope

Promo preview/redeem, sheet, layout gate, backend models, event registry,
contracts generation. Этот slice является rollback compatibility floor: после
распространения promo links production нельзя откатывать на build без этого
routing/privacy contract. Не коммитить и не пушить.
