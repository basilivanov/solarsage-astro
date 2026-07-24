# Slice 11 — authenticated promo gate and lost-response recovery

## Локальная цель

Связать pending session token, preview/redeem client и presentational sheet в
одной post-auth state machine. Не менять onboarding fields и backend.

## Preconditions

Приняты slices 01, 05, 09 и 10. Кодер читает только их public contracts и этот
документ.

## Разрешённые файлы

- новый `components/promo/promo-campaign-gate.tsx`;
- `app/(grace)/layout.tsx`;
- новый `__tests__/components/PromoCampaignGate.test.tsx`.

## Mount contract

`PromoCampaignGate` монтируется ровно один раз в normal authenticated branch
Grace layout:

- только после `useTelegramAuth().isAuthenticated=true`;
- присутствует и на ordinary routes, и на `/onboarding`;
- отсутствует в dev timing fixture shell;
- не меняет существующие auth loading/error states, AppShell или ProfileReset.

## State machine

React state хранит только safe `PromoOffer`, phase и safe error code/message.
Raw token никогда не хранится в state, props, DOM, log или Error; он читается
из sessionStorage непосредственно перед каждым API call.

```text
idle
 -> resolving preview
    -> invalid/expired/full: clear -> idle
    -> ALREADY_REDEEMED: clear -> completed refresh
    -> profileComplete=false + unlockNatal: retain -> requiredFor=promoNatal
    -> profileComplete=false + no natal: retain -> requiredFor=promoBase
    -> offer: show sheet ready
 -> redeeming
    -> 200 redeemed: clear -> completed refresh
    -> ALREADY_REDEEMED: clear -> completed refresh
    -> PROFILE_INCOMPLETE: retain -> required onboarding
    -> INVALID/EXPIRED/FULL: clear -> safe terminal error/dismiss
    -> RATE_LIMITED/network/5xx: retain -> retryable error
```

While pathname starts with `/onboarding`, gate не вызывает preview и не
показывает sheet. После выхода pathname меняется, preview выполняется снова.
Query содержит только safe mode; token там отсутствует.

## Completed refresh

После 200 или `ALREADY_REDEEMED`:

1. clear pending token;
2. не вызывать redeem повторно;
3. выполнить ровно один hard reload (`window.location.reload`) для честного
   refetch day/access/quota;
4. StrictMode/remount не должен создать reload loop.

Это обязательный recovery path для случая «server commit состоялся, первый 200
потерян сетью».

## UI/events

- Sheet получает только offer/phase/callbacks.
- `promo.offer_viewed` пишется один раз на фактическое открытие sheet, safe
  payload только benefit config; display name/token отсутствуют.
- `Не сейчас` и close/backdrop очищают token без redeem.
- Storage failure fail-closed: gate ничего не показывает, auth/app продолжают
  работать; typed `frontend.flow_failed` может содержать только safe
  `operation=promo.intent_store`/reason code.

## Tests

- no token -> no API/sheet;
- valid complete preview -> exact custom name/benefits sheet;
- incomplete natal/base -> matching safe onboarding URL, token retained;
- pathname onboarding -> no preview; exit -> preview/show;
- dismiss -> clear, no redeem;
- redeem 200 -> one clear + one reload;
- simulated lost 200/network, затем ALREADY -> one reload, no duplicate UI;
- invalid/expired/full clear; rate/network retain and Retry;
- StrictMode does not duplicate offer event/reload;
- raw token absent from rendered DOM and every logger mock call;
- fixture shell never mounts gate.

## Targeted verification

```bash
npx vitest run __tests__/components/PromoCampaignGate.test.tsx
```

## Out of scope

Onboarding field behavior, backend rate limit, Nginx, CLI, access-card copy.
Не коммитить и не пушить.
