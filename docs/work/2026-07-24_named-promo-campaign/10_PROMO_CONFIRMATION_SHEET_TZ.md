# Slice 10 — generic named promo confirmation sheet

## Локальная цель

Создать stateless/presentational bottom sheet, который показывает server-owned
campaign name и реальный набор benefits. Никаких fetch/storage/router side
effects.

## Разрешённые файлы

- новый `components/promo/promo-confirmation-sheet.tsx`;
- новый `__tests__/components/PromoConfirmationSheet.test.tsx`.

## Props contract

Компонент получает только safe offer/phase:

```ts
type Props = {
  offer: PromoOffer
  phase: "ready" | "redeeming" | "error" | "success"
  errorMessage?: string | null
  onActivate: () => void
  onDismiss: () => void
  onRetry?: () => void
}
```

Token/campaign ID/hash не являются props.

## Content

```text
eyebrow: Промокод
title: {offer.displayName}
description: По промокоду вам доступно:
```

Benefit rows render conditionally:

```text
accessDays > 0   -> {N} дней полного доступа
bonusCredits > 0 -> {N} бонусных вопросов
unlockNatal      -> Полный натальный разбор
```

Не писать «пакет тестера»/`tester` hardcoded. Конкретная campaign может иметь
такое `displayName`, и UI просто отображает его.

Buttons:

- primary `Активировать`;
- secondary `Не сейчас`;
- while redeeming primary disabled, `aria-disabled=true`, `aria-busy=true`;
- error with retry has real button `Повторить`;
- close/backdrop follows `onDismiss`, имеет `aria-label=Закрыть`.

## Semantic contract

```text
root role=dialog aria-modal=true
data-testid=promo-confirmation-sheet
data-state=ready|redeeming|error|success
promo-offer-name
promo-benefits
promo-benefit-access
promo-benefit-credits
promo-benefit-natal
promo-activate
promo-dismiss
promo-error role=alert
```

Использовать существующий max-width/bottom-sheet visual language. Focus/escape
behavior должен быть accessibility-safe; можно переиспользовать Radix Sheet,
если semantic selectors сохраняются. Dynamic name React-escaped.

## Tests

- custom names «Пакет тестера» и «Для друзей» отображаются, hardcoded fallback
  отсутствует;
- exact conditional benefit matrix;
- buttons call correct handlers;
- redeeming state disables activation and exposes busy;
- error role/Retry;
- dialog/test IDs/data-state contract;
- token-like strings отсутствуют в fixtures/DOM.

## Targeted verification

```bash
npx vitest run __tests__/components/PromoConfirmationSheet.test.tsx
```

## Out of scope

API call, sessionStorage, auth/layout, redirect, success reload, analytics.
Не коммитить и не пушить.
