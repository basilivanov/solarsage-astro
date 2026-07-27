# S1 TZ: композиция минимального первого экрана Дня

Дата: 2026-07-27
Phase / Wave: **W-TODAY-PREMIUM-FIRST-SCREEN**, волна W1, срез S1
Master: `docs/work/2026-07-27_today-premium-first-screen/00_MASTER_TZ.md` (решения D1–D8 обязательны)
Modules: `M-TODAY-TODAY-SCREEN`, `M-TODAY-DAY-SUMMARY-CARD`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal (один наблюдаемый результат)

На `/day/[date]` и `/today` (accessible-ветка) первый экран содержит только:
DateHeader → [условные TrialBanner/чекин] → DaySummaryCard →
ActivationEvidenceCard → ConcreteDayAdvice → WhyExpanded (collapsed).
DayReading и DayChart+DevAuditDrawer перенесены в два collapsed disclosure.
WeekStrip, AstroHistoryWidget и строка «Тянет сегодня» из композиции убраны.
Locked-ветка не меняется.

## 2. Exact write scope

- `components/today/today-screen.tsx` — новая композиция accessible-ветки;
  обновить MODULE_CONTRACT/MODULE_MAP под новую композицию.
- `components/today/day-summary-card.tsx` — удалить блок «Тянет сегодня»:
  разметку `day-top-spheres` (обе ветки), `getTop2SphereTitles`, prop
  `sphereScores`, вызов в today-screen. `DayZoneIndicator` и relativeStatus
  НЕ трогать.
- `components/today/day-collapsible.tsx` — **новый** маленький
  disclosure-враппер (см. §4).
- `__tests__/components/TodayScreen.test.tsx`
- `__tests__/components/TodayScreen.v2-downstream.test.tsx`
- `__tests__/today/day-summary-card.test.tsx` — удалить ожидания
  «Тянет сегодня» / `day-top-spheres`.
- `e2e/mock-visual/day.spec.ts`, `e2e/mock-visual/day-v2.spec.ts`,
  `e2e/today.spec.ts` — синхронизировать с новым контрактом (см. §5).

## 3. Frozen / out-of-scope

- `components/today/concrete-day-advice.tsx` (срез S2), `why-expanded.tsx`,
  `activation-evidence-card.tsx`, `date-header.tsx`.
- Файлы `week-strip.tsx`, `astro-history-widget.tsx` НЕ удалять — только
  убрать из композиции TodayScreen. `WeekStrip.test.tsx` не трогать.
- Locked-ветка TodayScreen (paywall): состав зон не менять.
- Backend, `lib/contracts`, `lib/adapters`, `lib/presentation/today-v2.ts`.
- Любые визуальные рестайлы сверх композиции (это S3): не менять цвета,
  тени, типографику существующих блоков.

## 4. Требования к реализации

Новая accessible-композиция (порядок строгий):

1. DateHeader (как сейчас)
2. TrialBanner / YesterdayEchoLoader (условные, как сейчас)
3. DaySummaryCard (без «Тянет сегодня»; prop `sphereScores` убрать и здесь,
   и в вызове)
4. ActivationEvidenceCard (как сейчас)
5. ConcreteDayAdvice (как сейчас, компонент не меняется)
6. WhyExpanded (как сейчас, controlled open сохраняется)
7. `DayCollapsible` title="Полный разбор дня" `data-testid="day-reading-disclosure"`
   → внутри DayReading (сохранить его `data-testid="day-reading"`)
8. `DayCollapsible` title="Как это рассчитано" `data-testid="day-tech-disclosure"`
   → внутри DayChart (сохранить `data-testid="day-chart"` /
   `day-chart-unavailable`) и DevAuditDrawer
9. footer disclaimer (как сейчас)

`DayCollapsible`:

- нативный `<button type="button">` с `aria-expanded`, `aria-controls`;
  контент в `role="region"` с `aria-labelledby` на кнопку;
- collapsed по умолчанию (без deeplink-логики);
- закрытый = контент не смонтирован или скрыт так, что
  `toBeVisible()` === false (важно для e2e);
- минимальная стилизация в духе текущих карточек; анимации не требуются (S4);
- стабильные `data-testid` на root и кнопке: `<testid>` и `<testid>-toggle`.

## 5. Must-preserve инварианты

- `data-testid="today-screen"`, `data-state="ready|locked"`.
- Все сохранённые testid блоков (`day-summary-card`, `concrete-day-advice`,
  `why-expanded`, `today-bottom-disclaimer` и пр.) не меняются.
- Deeplink `?why=1`, свайпы дней, сброс состояния при смене даты,
  scroll/focus в строку сферы и в Why (функции `scrollAndFocusSphere`,
  `scrollAndFocusWhy`, `selectPersonalStorySphere`) работают как раньше.
- GRACE-разметка в редактируемых файлах обновлена под новую композицию
  (contract/map в today-screen.tsx; semantic blocks в day-summary-card.tsx).

e2e-синхронизация:

- `e2e/today.spec.ts` — убрать ожидания `week-strip`.
- `e2e/mock-visual/day.spec.ts` — убрать `week-strip` /
  `astro-history-widget` из ожиданий и sectionOrder; проверки
  `day-chart` / `day-reading` перевести на сценарий «disclosure закрыт →
  не виден; открыть toggle → виден» (включая тест popover планеты чарта —
  сначала открыть `day-tech-disclosure`).
- `e2e/mock-visual/day-v2.spec.ts` — то же для селекторов
  `day-chart` / `day-reading`.
- Прогон e2e в этом срезе НЕ требуется (бейзлайны — S4); спеки должны быть
  синхронны по селекторам.

## 6. Verification (одна targeted-команда)

```bash
npx vitest run __tests__/components/TodayScreen.test.tsx __tests__/components/TodayScreen.v2-downstream.test.tsx __tests__/today/day-summary-card.test.tsx
```

## 7. Expected evidence в отчёте

- Список изменённых файлов и краткий diff-вывод.
- Полный вывод verification-команды (все тесты зелёные).
- Список обновлённых e2e-ожиданий (файл:строка).

## 8. Escalation rule

Понадобился файл вне §2 (например, правка concrete-day-advice, lib/*,
backend, новые зависимости) — стоп, доложить в отчёте, ждать новый packet.
Ничего не коммить и не пушить.
