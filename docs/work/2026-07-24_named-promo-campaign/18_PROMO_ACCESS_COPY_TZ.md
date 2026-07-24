# Slice 18 — honest non-enrollment access copy

## Локальная цель

Пользователь с promo `AccessLedger(entry_type=subscription)`, но без настоящей
`Subscription`, не должен видеть ложные фразы «Подписка активна» и «оплаченный
период».

## Разрешённые файлы

- `components/profile/profile-screen.tsx`;
- `components/profile/access-card.tsx`;
- узкие existing tests этих компонентов.

## Contract

`getSubscriptionStatus()` уже возвращает `status="none"` при отсутствии
enrollment. ProfileScreen передаёт AccessCard не только renewing/cancelable, но
и truthful enrollment state.

Access card variants:

- `currentState=subscription`, status `none`:
  - title `Полный доступ активен`;
  - subtitle показывает access end;
  - footnote `Доступ предоставлен без автопродления.`;
  - secondary disabled `Автопродление не подключено`;
  - никакой оплаты/отмены/«подписка активна».
- status loading: generic `Доступ активен`, не утверждать enrollment;
- real pending/active/past_due/canceled/expired Subscription сохраняет текущую
  billing-derived semantics и cancelability.

Не пытаться определить promo по frontend storage/campaign name. Source of truth
— отсутствие настоящей Subscription при действующем ledger.

## Tests

- promo/no-subscription DOM copy exact safe contract;
- real active recurring path unchanged;
- canceled non-renewing paid period remains truthful;
- loading status no false paid claim;
- semantic data attributes различают `enrollment=none|loading|present`;
- billing buttons/cancel behavior unchanged for real subscriptions.

## Targeted verification

```bash
npx vitest run __tests__/components/AccessCard.test.tsx __tests__/components/ProfileScreen.test.tsx
```

Использовать actual existing filenames и отразить их в coder report.

## Out of scope

AccessSummary API/schema, AccessLedger entry type, campaign name on profile,
billing backend. Не коммитить и не пушить.

