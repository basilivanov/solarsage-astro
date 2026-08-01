# 55A — Today screen: подписи импульсов, DateHeader со свайпами, «Как это рассчитано»

Ты — coder. Skill coder-loop использовать НЕЛЬЗЯ. Ничего не коммить — коммит делает ревьюер.

Контекст: приёмка владельца на dev. Норматив — `docs/work/2026-07-29_today-convergence-rewrite/03_W7_FRONTEND_DESIGN_TZ.md` (§5, §9, §10). Шаблонные заглушки запрещены (§10).

## Скоуп файлов (только эти)

- `components/today-convergence/impulses-list.tsx`
- `components/today-convergence/main-event.tsx` (если нужно то же, что импульсам)
- `components/today-convergence/how-calculated.tsx`
- `components/today-convergence/today-screen.tsx` (передать snapshotId в ImpulsesList)
- `app/(grace)/day/[date]/page.tsx` (DateHeader + свайпы)
- `__tests__/components/today-convergence/today-screen.test.tsx` и релевантные тесты day page

НЕ трогать: `sphere-drilldown.tsx`, `sphere-page.tsx`, `sphere-navigator.tsx`, `calendar*`, backend.

## 1. Импульсы с подписью и drilldown-ссылкой (ТЗ §5.2)

Сейчас карточка импульса — `li` без ссылки, показывает только время/сферу/polarity-пилюлю. В payload у каждого impulse есть `summary.text` (LLM, человеческая строка) — проверено на живом API, приходит заполненным.

Сделать:
- Под строкой времени/сферы рендерить `impulse.summary.text` (перенос по словам, `text-wrap: pretty`, без обрезки). Если `summary == null` — не выдумывать текст, просто не рендерить строку (ТЗ §5.6/§10).
- Карточку сделать ссылкой на drilldown: если у TodayScreen есть `payload.snapshotId`, вести на `/day/snapshots/{snapshotId}/spheres/{sphere}` (тот же маршрут, что у маркированных тайлов в `sphere-navigator.tsx`). Если snapshotId нет — обычный `li` без ссылки. Сохранить `data-testid="impulse-{eventId}"`, `data-polarity`, `data-time-mode`; добавить стабильный `data-has-summary="true|false"`.
- ТЗ §5.2 подразумевает формат «время — описание события». Описание события (астро-драйвер) придёт отдельным backend-пакетом 55B как `title` у drilldown-событий; в импульсах НЕ дублировать — только summary + ссылка.

## 2. DateHeader: человеческая дата + свайпы (ТЗ §5, строка «DateHeader (← Сегодня, 30 июля →) [свайпы/стрелки]»)

Сейчас `DayDateNavigation` в `app/(grace)/day/[date]/page.tsx` показывает ISO `2026-08-01`, свайпов нет.

Сделать:
- Видимый label: «Сегодня, 1 августа» для сегодня, «Вчера, 31 июля», «Завтра, 2 августа», иначе «1 августа» (использовать существующие хелперы из `lib/date.ts`/`lib/today.ts`; год добавлять только если не текущий).
- Свайпы по экрану дня: touchstart/touchend (или pointer events) на контейнере страницы; горизонтальный жест с |dx| ≥ 48px и |dx| > 1.5·|dy| → навигация prev/next день через существующий `onDateChange(shiftDate(...))`. Свайп влево → следующий день, вправо → предыдущий. Не блокировать вертикальный скролл, не вмешиваться в жесты на интерактивных элементах ввода. Уважать те же границы, что и стрелки.
- Сохранить `data-testid="day-date-navigation"`, aria-labels кнопок.

## 3. «Как это рассчитано» — честный развёрнутый текст

Сейчас одна общая фраза. Заменить на статический текст (3–4 коротких абзаца, без LLM-полей):
- День считается по твоей натальной карте и точному положению планет (Swiss Ephemeris); результат публикуется как неизменяемый снимок (snapshot) расчёта.
- События и сферы отбираются детерминированными правилами из этого снимка; времена — точные моменты аспектов.
- Персональный текст поверх пишет языковая модель только по фактам снимка; если текст не готов, факты дня всё равно показываются.
Сохранить disclosure-контракт (`aria-expanded`, `aria-controls`, `hidden`, `data-testid="how-calculated"`).

## Verification (обязательно, показать вывод)

- `npx vitest run __tests__/components/today-convergence __tests__/app 2>&1 | tail -5`
- `npx vitest run 2>&1 | tail -4`
- `npx tsc --noEmit`
- `python3 scripts/grace_front_lint.py | tail -2`
- `git diff --check`

GRACE-маркеры: обновить MODULE_MAP/блоки при изменении entrypoints. DOM test contract не ломать, только добавки.
