# W3 TZ: честные verdict-чипы на сферах (UI на row.assessment)

Дата: 2026-07-27
Phase / Wave: **W3-HONEST-VERDICT-CHIPS**, срез W3-UI
Контекст: W2 завершён; `ConcreteAdviceRow.assessment` (SphereValenceRead) уже
в payload при `TODAY_VALENCE_V1_ENABLED=true`; D2-удаление чипов отменяется.
Modules: `M-TODAY-CONCRETE-DAY-ADVICE`, `M-TODAY-SPHERE-DETAILS-SHEET`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal

Строки сфер и модалка сферы показывают ЧЕСТНЫЙ verdict из `row.assessment`
(engine day-valence-1.0), не из legacy salience. Fallback без assessment —
нейтральный вид (нет чипа), никакого вычисления verdict на фронте.

## 2. Exact write scope

- `lib/contracts/today.ts` — `ConcreteAdviceRowSchema` += `assessment`
  (тип из `packages/contracts` — wire source of truth, не рукописный).
- `components/today/concrete-day-advice.tsx` — на строке: компактный
  вердикт-индикатор (цветная точка + короткий лейбл) + `data-status`.
- `components/today/sphere-details-sheet.tsx` — бейдж вердикта рядом с
  заголовком сферы + `data-status` на root.
- Тесты: `__tests__/components/ConcreteDayAdvice.keyboard.test.tsx`,
  `__tests__/components/TodayScreen.v2-downstream.test.tsx`.
- e2e: `e2e/mock-visual/day.spec.ts`, `e2e/mock-visual/day-v2.spec.ts`,
  `e2e/dev-visible-sphere-status.spec.ts` (из no-verdict-гарда обратно в
  позитивный контракт чипов).

## 3. Presentation contract (закрыт)

```text
good     -> «Поддержка»          emerald, data-status="good"
neutral  -> «Ровный фон»         slate,   data-status="neutral"
caution  -> «Требует внимания»   amber,   data-status="caution"
avoid    -> «Лучше отложить»     rose,    data-status="avoid"
```

- Источник: ТОЛЬКО `row.assessment.assessment.verdict` (CamelCase wire:
  `assessment.verdict`). assessment отсутствует/null → чип НЕ
  рендерится, `data-status` не ставится (НЕ neutral-by-default!).
- Цвет вторичен, текст обязателен (контраст light/dark).
- Строка: точка + лейбл справа от названия сферы (слева от chevron),
  без изменения размеров строки.
- Модалка: бейдж под заголовком; при confidence="low" — бейдж приглушён
  (opacity ~60%), никаких дополнительных подписей.

## 4. Frozen / out-of-scope

- Backend, версии, флаги (ревьюер включает ENABLED на деве сам).
- Тексты story/why/advice (M6/M7 не трогать).
- Структура/порядок блоков экрана.

## 5. Must-preserve

- Все существующие testid (`concrete-day-advice-row`, `sphere-details-sheet`
  и пр.), поведение модалок, BANNED-copy e2e.
- Никаких frontend-вычислений verdict/balance.

## 6. Verification

```bash
npx vitest run __tests__/components/ConcreteDayAdvice.keyboard.test.tsx __tests__/components/TodayScreen.v2-downstream.test.tsx
```

## 7. Expected evidence

- Файлы, вывод verification, список обновлённых e2e-ожиданий.

## 8. Escalation rule

Нужен файл вне §2 — стоп, доложить. Ничего не коммить и не пушить.
