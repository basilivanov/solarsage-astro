# Packet: grouped impulses and human-first modal

## Phase / Wave

`W-TODAY-HUMAN-FIRST / P2-IMPULSE-MODAL`

## Modules

- `M-TODAY-CONVERGENCE-IMPULSES`
- `M-TODAY-CONVERGENCE-FORMATTERS`
- `M-TODAY-CONVERGENCE-SCREEN`
- новый `M-TODAY-IMPULSE-DRILLDOWN`

## Goal

Импульсы одной сферы отображаются как один понятный блок с отдельными сигналами и явным CTA; по CTA открывается доступная bottom-sheet/desktop-modal с детерминированными фактами Today и лениво загруженным контекстом натальной сферы.

## Exact Write Scope

- `components/today-convergence/impulses-list.tsx`
- `components/today-convergence/today-formatters.tsx`
- `components/today-convergence/today-screen.tsx`
- `components/today-convergence/impulse-drilldown-sheet.tsx` (new)
- `__tests__/components/today-convergence/today-screen.test.tsx`

## Frozen / Out Of Scope

- Не менять backend/API, generated contract artifacts, `lib/api/spheres.ts`, route handlers.
- Не менять `sphere-navigator.tsx`, `sphere-page.tsx`, `how-calculated.tsx` — это следующий packet.
- Не менять e2e visual spec, masks или committed PNG baselines до апрува владельца.
- Не менять астро-факты и не генерировать новые интерпретации на клиенте.
- Не трогать unrelated/untracked worktree files.

## Must Preserve Invariants

- Сохраняются `data-testid="impulses-list"` и `data-testid="impulse-{eventId}"`, `data-polarity`, `data-time-mode` для каждого факта.
- Групповой CTA имеет стабильный test id и ясный текст `Разобрать, как это может проявиться`.
- Modal/sheet имеет `role=dialog`, `aria-modal`, доступное имя, закрытие кнопкой/Escape и стабильный `data-testid="impulse-drilldown-sheet"`.
- Mobile — bottom sheet; desktop — компактная modal/sheet поверх экрана без перестройки двух колонок.
- Локальные Today-факты видны сразу. `fetchSpherePage` вызывается лениво при открытии; loading/error/403 контекста сферы не скрывает Today-факты и не ломает modal.
- Содержание: сфера + сегодня; каждый сигнал с polarity, summary, product time; существующее action показывается только если есть; natal paragraphs/active periods — только из успешного sphere payload; ссылка на полный разбор сохраняет snapshot context.
- Формат exact времени предпочитает `peakAt/startAt/endAt` и `payload.timezone`; пример обязателен: `пик 1 августа, 11:34`, `окно: с 31 июля, 20:23 до 2 августа, 02:34`. Для старых fixture без absolute fields безопасно остаётся clock-only fallback.
- Один импульс и несколько импульсов одной/разных сфер покрыты тестами.
- Новый файл полностью размечен GRACE; contracts/maps изменённых файлов актуализированы.

## Verification Command

```bash
cd /opt/solarsage-astro && npx vitest run __tests__/components/today-convergence/today-screen.test.tsx
```

## Expected Evidence

- Список изменённых файлов.
- DOM/test summary для grouped card, CTA и dialog.
- Targeted vitest output и число passed tests.
- Явное подтверждение, что baseline PNG не менялись.

## Escalation Rule

Если нужен файл вне scope, изменение API, новый backend endpoint или перенос следующего packet внутрь этого — остановиться и доложить архитектору; не расширять scope самостоятельно.

## No Commit Rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
