# D2_TZ: zone-индикатор и подпись относительного статуса — frontend

## 1. Packet title
Relative day status UI: подпись статуса относительно базлайна + индикатор «обычная зона ↔ сегодня» + акцентные сферы дня (ротация). Зависит от D1 (payload fields).

## 2. Phase / Wave
W-DAY, relative status UI. D1 даёт в payload: `relative_status {mode, status, z_support, z_tension, baseline {…, days}, band [lo,hi], marker 0..100}`.

## 3. Modules
- `components/today/day-summary-card.tsx` (или где сейчас заголовок статуса — уточнить по коду)
- `lib/api/day.ts` (тип поля relative_status)
- `__tests__/today/` (компонентный тест)

## 4. Goal

### 4.1. Подпись статуса
- mode="absolute" → текущее поведение (как сейчас).
- mode="relative" → подпись из маппинга: usual «Обычный день», softer «Легче, чем обычно», tenser «Напряжённее обычного», hard «Тяжёлый день», strong «Сильный день».
- Никаких z/score/сырых цифр в UI.

### 4.2. Zone-индикатор (только mode="relative")
Маленький компонент в карточке дня: горизонтальная шкала, полоса `band [lo,hi]` («ваша обычная зона»), маркер-точка `marker` (0..100) — «сегодня». Подпись к маркеру текстом (та же, что статус). data-testid="day-zone-indicator". Не показывать, если baseline.days < 5.

### 4.3. Акцентные сферы (ротация)
В карточке дня строка: «Тянет сегодня: {топ-2 сферы по скору}» — из существующих sphere scores payload (без новых вычислений). data-testid="day-top-spheres".

## 5. Exact write scope
- `components/today/day-summary-card.tsx`
- `components/today/day-zone-indicator.tsx` (новый)
- `lib/api/day.ts` (тип)
- `__tests__/today/day-summary-card.test.tsx` (обновить/новый)

## 6. Frozen / Out of scope
- Backend (D1), макет целиком (только эти блоки), другие экраны.

## 7. Must-preserve invariants
- data-testid контракт day-экрана; fallback при отсутствии поля (старые payload без relative_status — рендерится как раньше).
- vitest зелёный; lint чист.

## 8. Verification commands
```bash
npx vitest run __tests__/today
pnpm run lint
```

## 9. Expected evidence
- diff по scope-файлам, вывод vitest, скрин карточки с индикатором.

## 10. Escalation rule
Нужен backend scope → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
