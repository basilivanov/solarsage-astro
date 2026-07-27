# S4 TZ: моушн-полировка экрана Дня (disclosure animation, press states, reduced-motion)

Дата: 2026-07-27
Phase / Wave: **W-TODAY-PREMIUM-FIRST-SCREEN**, волна W1, срез S4
Master: `docs/work/2026-07-27_today-premium-first-screen/00_MASTER_TZ.md` (§4 моушн)
Modules: `M-DAY-COLLAPSIBLE`, `M-TODAY-CONCRETE-DAY-ADVICE`, `M-TODAY-WHY-TIME-HORIZON-CARD`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal (один наблюдаемый результат)

Все раскрытия на экране Дня анимируются мягко и одинаково
(200–300ms, `cubic-bezier(0.22,1,0.36,1)`), интерактивные элементы имеют
press-state, при `prefers-reduced-motion` анимации отключаются. Структура
JSX/testid/тексты не меняются.

## 2. Exact write scope

- `components/today/day-collapsible.tsx` — анимация раскрытия.
- `components/today/concrete-day-advice.tsx` — анимация деталей сферы +
  press-state строк.
- `app/globals.css` — только добавить: `--ease-premium` токен и
  reduced-motion guard (если уже есть — переиспользовать).
- `components/today/why-time-horizon-card.tsx` — ТОЛЬКО если там раскрытие
  технического disclosure («Как это рассчитано») — применить тот же easing;
  если раскрытия нет, файл не трогать.

## 3. Frozen / out-of-scope

- `today-screen.tsx`, `day-summary-card.tsx`, `activation-evidence-card.tsx`,
  `date-header.tsx`, `why-expanded.tsx`, backend, lib.
- Новые зависимости (framer-motion и т.п.) — ЗАПРЕЩЕНЫ. Только CSS.
- Изменение текстов, testid, aria, структуры.

## 4. Техника

- Раскрытие региона: CSS `grid-template-rows: 0fr → 1fr` (или эквивалент
  без JS-измерений высоты) + `opacity`, 250ms `cubic-bezier(0.22,1,0.36,1)`.
  Контент региона остаётся в DOM во время анимации; полный unmount после
  закрытия допустим как сейчас, но открытие обязано анимироваться.
- Press-state интерактивных кнопок/строк: `active:scale-[0.985]` +
  `transition-transform` там, где его ещё нет (строки сфер, show-details,
  collapsible toggle).
- `prefers-reduced-motion`: все новые анимации отключены
  (`motion-reduce:transition-none` / media-query в globals).
- chevron rotate в DayCollapsible — тот же easing.
- Существующие анимации не ломать.

## 5. Must-preserve

- Все data-testid, aria-expanded/controls, role=region, поведение кликов.
- Vitest зелёный без изменений тестов (если тест всё же требует
  синхронизации — доложить в отчёте отдельно, не менять молча).

## 6. Verification (одна targeted-команда)

```bash
npx vitest run __tests__/components/TodayScreen.test.tsx __tests__/components/TodayScreen.v2-downstream.test.tsx __tests__/components/ConcreteDayAdvice.keyboard.test.tsx
```

## 7. Expected evidence

- Список файлов, краткое описание анимационной техники, вывод verification.

## 8. Escalation rule

Нужен JS-маунт/размер или файл вне §2 — стоп, доложить. Ничего не коммить
и не пушить.
