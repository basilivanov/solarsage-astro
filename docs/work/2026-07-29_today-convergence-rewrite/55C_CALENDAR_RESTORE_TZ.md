# 55C — Календарь: вернуть старую вёрстку, маркеры по dayState (ТЗ §8.1)

Ты — coder. Skill coder-loop использовать НЕЛЬЗЯ. Ничего не коммить — коммит делает ревьюер.

Контекст: в коммите `0e450ff2` («calendar v2») экран календаря был переписан с 628 до 187 строк: убраны тоггл «Дни/Луна», крупные круглые ячейки 44px, lunar-лента, серифные цифры, и появился дублирующий заголовок («Август 2026» + «август 2026 г.» от grace-CalendarGrid). Владелец: «календарь поломался полностью, раньше был по-другому свёрстан, мы не должны были его трогать». Задача — вернуть старую вёрстку, но маркеры дней вести от ТЕКУЩЕГО backend-поля `dayState` (старого `dayStatus`/valence в backend больше нет), по нормативу `docs/work/2026-07-29_today-convergence-rewrite/03_W7_FRONTEND_DESIGN_TZ.md` §8.1.

## Факты (проверено ревьюером на живом dev API)

- `GET /api/calendar?month=YYYY-MM` отдаёт 92 дня с полями: `date, dayNumber, isCurrentMonth, isToday, disabled, dayState ("ordinary"|"hero"|"not-computed"), access {state, reason, ...}, lunar {phase, phaseIndex, phaseLabel, illumination, moonSign, moonSignLabel, lunarDay, voidOfCourse}`.
- Старая вёрстка доступна: `git show 0e450ff2^:components/calendar/calendar-screen.tsx` (628 строк). Она использует `getMonthCalendar` из `lib/api/calendar.ts`, `MoodIcon`, `LunarCalendarStrip`, `PhaseGlyph`, `lib/calendar.ts`, `lib/lunar-presentation.ts` — все файлы на месте, но read-model мог потерять поля `lunar`/`access`/`dayState` при переезде на generated contract.
- Текущий `components/calendar/calendar-screen.tsx` (187 строк) — НЕ сохранять, это и есть сломанная версия. `components/grace/CalendarGrid*` больше не нужен на этом экране (не удалять файл, используется ли он ещё где-то — проверить по `rg "CalendarGrid"`; если нигде — удаление допустимо, иначе оставить).

## Что сделать

1. Восстановить layout из `0e450ff2^`:
   - header: caps-подпись + serif-заголовок месяца (`data-testid="calendar-month-header"`), круглые кнопки prev/next (aria-labels «Предыдущий месяц»/«Следующий месяц»), разделитель;
   - тоггл «Дни / Луна» (два режима сетки);
   - сетка 7 колонок, ячейки-кнопки `h-11 w-11 rounded-full`, serif-цифры дня, today — `ring-1 ring-border`, selected — `bg-primary text-primary-foreground` (режим Дни) / ring (режим Луна), дни вне месяца — `opacity-30`, locked-дни (access.state != "full") — иконка Lock + `opacity-65`;
   - режим «Луна»: `PhaseGlyph` (phaseIndex), номер лунного дня, amber-точка void-of-course, `LunarCalendarStrip` над сеткой — всё из восстановленных компонентов (`components/calendar/lunar-calendar-strip.tsx`, `phase-glyph.tsx`, `mood-icon.tsx` на месте);
   - навигация по тапу на день — как в старой версии (переход на `/day/<date>` или через onOpenDay; свериться со старым кодом и текущим роутингом).
2. Маркеры вместо MoodIcon/valence — по `dayState` (ТЗ §8.1):
   - `hero` → заполненная точка 6px нейтральный ink под цифрой;
   - `ordinary` → ничего;
   - `not-computed` → пустой круг 6px (muted outline);
   - запрещены valence-заливки, tone-цвета, подписи. `MoodIcon` больше не использовать (можно не трогать сам файл).
3. Read-model: убедиться, что `lib/api/calendar.ts` / `lib/contracts/calendar.ts` принимают и пробрасывают `dayState`, `lunar`, `access`, `allowedRange`, `isCurrentMonth/isToday/disabled` (backend их отдаёт; сгенерированный contract проверить — если полей нет в schema, проверить `packages/contracts` и при необходимости починить backend-схему, а не руками). `dayStatus` (valence) НЕ воскрешать.
4. DOM-контракт: сохранить `data-testid="calendar-screen"`, `data-state="loading|ready|error"`, `calendar-grid`, `calendar-day-YYYY-MM-DD`, `calendar-month-header`, loading `role="status"`, error `role="alert"`. Добавить `data-day-state` на ячейку (hero/ordinary/not-computed). Дубля заголовка быть не должно — один заголовок месяца.
5. Тесты: привести `__tests__/components/CalendarScreen.test.tsx` к восстановленному экрану (тоггл, ячейки, маркеры dayState, locked). Обновить `e2e/mock-visual/calendar.spec.ts` ожидания под старую вёрстку (бейзлайн PNG переснимет ревьюер на deploy-этапе — в этом пакете только код и unit/e2e assertions; сами PNG не генерировать).

## Verification (обязательно, показать вывод)

- `npx vitest run __tests__/components/CalendarScreen.test.tsx 2>&1 | tail -4`
- `npx vitest run 2>&1 | tail -4`
- `npx tsc --noEmit`
- `python3 scripts/grace_front_lint.py | tail -2`
- `git diff --check`

GRACE-маркеры: у восстановленного файла обновить MODULE_CONTRACT/MAP (owned_tests, emitted_logs по факту). Не ломать `hooks/use-access.ts`, tab-bar и роуты вне календаря.
