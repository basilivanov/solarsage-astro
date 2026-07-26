# C4_TZ: purchase sheet + zero-credit UX + typed errors (Release B)

## 1. Packet title
Corrective wave, срез C4: `synastry-purchase-sheet`, убрать zero-credit dead end в `SynastryScreen`/`SynastryAddSheet`, typed `SynastryApiError`.

## 2. Phase / Wave
Post-synastry-live corrective, Release B. Master: `docs/work/2026-07-26_post-synastry-live-corrective/00_TZ.md` (§8.3, §9, §13 S8-S9 — читать обязательно). Зависит от C2 (capabilities contract) и C3 (purchase backend).

## 3. Modules
- `components/synastry/synastry-purchase-sheet.tsx` (новый)
- `components/synastry/synastry-screen.tsx`
- `components/synastry/synastry-add-sheet.tsx`
- `lib/api/synastry.ts` (SynastryApiError)
- `lib/api/payment.ts` (использовать существующие клиенты)

## 4. Goal

### 4.1. Purchase sheet (§8.3)
`components/synastry/synastry-purchase-sheet.tsx`:
- переиспользовать `getPaymentProducts()`, `startPurchase('synastry')`, `openProviderCheckout()`, `pollPurchaseStatus()` из `lib/api/payment.ts` (НЕ копировать логику);
- показывать цену ИЗ каталога (не хардкод);
- UI contract: root `data-testid="synastry-purchase-sheet"`; `data-state="loading|ready|waiting|error"`; CTA `data-testid="synastry-purchase-cta"`; ошибка — `role="alert"`; waiting — `role="status"`, CTA disabled + aria-busy; success ТОЛЬКО по локальному status `consumed|succeeded|delivered` (provider redirect НЕ доказательство);
- после success: обновить capabilities/quota (callback); если sheet открыт из заполненной partner form — поля НЕ терять; автоматический повторный POST partner БЕЗ явного подтверждения запрещён;
- Escape/overlay close (как остальные sheets).

### 4.2. Zero-credit UX (§9)
`SynastryScreen`: сначала capabilities, затем partners. Обязательные состояния:
- root `data-testid="synastry-screen"` сохраняется; `data-state="loading|ready|empty|error|locked"`;
- `creditBalance == 0 && canPurchase` → Add CTA открывает PURCHASE sheet с ценой из каталога;
- `creditBalance == 0 && !canPurchase` → честный unavailable state без неработающей кнопки;
- partner limit → CTA disabled + `aria-disabled` + объяснение;
- quota block: `data-testid="synastry-credit-gate"` (locked state);
- уже созданные reports читаемы при нулевом балансе (список всегда загружается);
- транспортная ошибка capabilities → fail-closed для нового расчёта, показанные данные не стирать.

### 4.3. SynastryApiError (§9)
- `lib/api/synastry.ts`: класс `SynastryApiError extends Error` с `status: number`, `code: string | null`; безопасный message (никакого `[object Object]` — detail object маппить в code/message).
- Все fetch-хелперы бросают его (вместо generic Error).
- `SynastryAddSheet`: на 402 `NO_CREDITS` → вызвать purchase callback (onNeedPurchase), поля формы сохранить, технический английский текст не показывать; на другие ошибки — понятное русское сообщение.

## 5. Exact write scope
- `components/synastry/synastry-purchase-sheet.tsx` (новый)
- `components/synastry/synastry-screen.tsx`
- `components/synastry/synastry-add-sheet.tsx`
- `lib/api/synastry.ts`
- `__tests__/synastry/synastry-purchase-sheet.test.tsx` (новый)
- `__tests__/synastry/synastry-screen.test.tsx`, `__tests__/synastry/synastry-add-sheet.test.tsx`

## 6. Frozen / Out of scope
- Backend (C1-C3), `lib/api/payment.ts` (только читать/переиспользовать), horary purchase sheet (паттерн-референс, не менять).
- Редизайн карточек/hero (приняты в X1/X2).

## 7. Must-preserve invariants
- data-testid контракт списка из X1 (hero, card, counters, filters).
- Успех покупки — только по локальному authenticated status.
- Форма не теряет данные при purchase detour.
- GRACE-разметка; все тесты зелёные.

## 8. Verification commands
```bash
npx vitest run __tests__/synastry
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/synastry.spec.ts
```
Кейсы: zero-balance → purchase CTA с ценой; waiting state; success → capabilities refresh; NO_CREDITS из add-sheet → purchase callback + поля сохранены; `[object Object]` не появляется нигде.

## 9. Expected evidence
- `git diff --name-only` — только scope-файлы.
- Вывод проверок.

## 10. Escalation rule
Нужен backend/payment.ts scope → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
