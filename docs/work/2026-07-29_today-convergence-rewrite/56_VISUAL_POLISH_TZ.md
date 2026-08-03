# 56 — Visual polish: Today + drilldown + календарь «по красоте»

Ты — coder. Skill coder-loop использовать НЕЛЬЗЯ. Ничего не коммить — коммит делает ревьюер.

Контекст: владелец смотрит dev и говорит, что фронт выглядит как wireframe: плоские белые карточки на креме, нет типографической иерархии, сливовый акцент почти нигде не используется, всё серое и мелкое. Дизайн-язык (норматив `docs/work/2026-07-29_today-convergence-rewrite/03_W7_FRONTEND_DESIGN_TZ.md` §3): тёплая бумага фона, serif для героя и заголовков сфер, сливовый (plum, `--primary`) как фирменный/интерактивный, янтарный tense, карточки radius 24, СПОКОЙНЫЕ тени.

DOM test contract (data-testid, data-state и т.п.) НЕ менять — только классы/стили и, где указано, безопасные добавки. Snapshot-бейзлайны переснимет ревьюер — e2e PNG не трогать.

## 1. Токены (app/globals.css, блок :root с tone-*)

Добавить спокойные тёплые тени (использовать через arbitrary `shadow-(--shadow-card)` / `shadow-(--shadow-lift)`):

```css
/* Calm warm elevation for cards on warm paper. */
--shadow-card: 0 1px 2px rgb(62 51 71 / 0.05), 0 6px 20px rgb(62 51 71 / 0.06);
--shadow-lift: 0 2px 4px rgb(62 51 71 / 0.06), 0 10px 28px rgb(62 51 71 / 0.09);
```

## 2. Карточки — единый язык

Во ВСЕХ перечисленных ниже компонентах заменить паттерн `border border-border/60 bg-card ... shadow-sm` на: `border border-border/40 bg-card shadow-(--shadow-card)` — тонкая тёплая кромка + реальная спокойная тень. Компоненты: `impulses-list.tsx`, `main-event.tsx`, `convergence-hero.tsx`, `sphere-navigator.tsx` (тайлы), `how-calculated.tsx`, `today-narrative.tsx`, `today-lookahead.tsx`, `period-context.tsx`, `birth-time-banner.tsx`, `sphere-drilldown.tsx`, `sphere-page.tsx`, `today-unavailable.tsx`. Не трогать: paywall (свой визуал W1), checkin, profile, readings.

## 3. Экран дня — иерархия (quiet_day)

`impulses-list.tsx`:
- Секционный лейбл «Импульсы дня»: `text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground/80` (единый стиль для всех caps-лейблов экрана: «Сферы жизни», «Также сегодня», «Главное событие дня»).
- Карточка импульса (это ссылка!): radius `rounded-[20px]`, padding `p-4`; первая строка — время `text-[13px] tabular-nums text-muted-foreground` и НАЗВАНИЕ СФЕРЫ `font-serif text-[17px] leading-[22px] text-foreground`; polarity-пилюля остаётся; summary — основной текст `text-[15px] leading-[23px] text-pretty text-foreground/90`.
- Link affordance: справа chevron (`ChevronRight`, `h-4 w-4 text-muted-foreground/50`), на hover у карточки `shadow-(--shadow-lift)` + `border-primary/30`, transition 150ms, `motion-reduce:transition-none`. Chevron скрывать если карточка не ссылка (нет snapshotId).

`main-event.tsx`: тот же язык, что карточка импульса (serif-сфера 17px, summary как основной текст), лейбл «Главное событие дня» в едином caps-стиле.

`today-narrative.tsx`: текст `text-[15px] leading-[24px] text-pretty text-foreground/90`, карточка по §2. Pending-скелетон оставить.

## 4. Hero (convergence-hero.tsx)

- Сфера-ссылка: `font-serif text-[22px] leading-[28px]`, hover — `text-primary` (plum) вместо underline, сохранить focus-ring.
- «Также сегодня» строки: serif 15px для имён сфер.
- Evidence-строку «Доказательность: высокая/средняя» — `text-[12px] text-muted-foreground/80` с маленькой plum-точкой слева (`h-1.5 w-1.5 rounded-full bg-primary/60`).
- Сохранить plum-рамку 1.5px и tone-фоны.

## 5. Навигатор сфер (sphere-navigator.tsx)

- Тайлы: `bg-card` (не /60), кромка `border-border/40`, `shadow-(--shadow-card)`; hover: `shadow-(--shadow-lift)` + `-translate-y-0.5` (transform 150ms, motion-reduce:none); иконка `text-foreground/75`; label `text-[12.5px] font-medium`; has-today точка — оставить нейтральный ink (ТЗ §6).
- Лейбл «Сферы жизни» — единый caps-стиль из §3.

## 6. DateHeader (app/(grace)/day/[date]/page.tsx)

- Дата: `font-serif text-[17px] leading-[22px]`. Стрелки ←/→ заменить на `ChevronLeft/ChevronRight` (`h-4 w-4`) в круглых кнопках `h-9 w-9 rounded-full border border-border/50 bg-card shadow-(--shadow-card)`, сохранить aria-labels и data-testid.

## 7. Drilldown (sphere-drilldown.tsx)

- Заголовок «<Сфера> — сегодня»: `font-serif text-[28px] leading-[34px]`; caps-лейблы в едином стиле.
- Карточка события: title `text-[15px] font-medium leading-[21px]`; номер в круге — `bg-primary/10 text-primary` (plum-tint вместо серого secondary).
- Карточки по §2.

## 8. Страница сферы (sphere-page.tsx)

- Заголовки слоёв «В твоей карте»/«Сейчас действует»: serif 22px (уже) — оставить; абзацы натала: `text-[15px] leading-[26px] text-pretty text-foreground/90`.
- Карточки периодов: title `text-[15px] font-medium`, дата `text-[13px] text-muted-foreground`; карточки по §2.

## 9. Календарь (components/calendar/calendar-screen.tsx)

- УДАЛИТЬ строку легенды valence («ровный / поддерживающий / смешанный / напряжённый» с иконками) — backend dayStatus больше нет, легенда мертва.
- Цифры текущего месяца: `text-foreground/85` (сейчас слишком блёклые); выходные — `text-foreground/60`; not-computed кружок: `border-[1.5px] border-muted-foreground/45` (читабельнее), hero-точка `bg-foreground` 6px.
- Footer «СЕГОДНЯ»: caps-лейбл в едином стиле; дата `font-serif text-[20px]`; кнопка «Открыть день →» — `bg-primary text-primary-foreground rounded-full shadow-(--shadow-card)` (сейчас чёрная — привести к plum).
- БАГ: в footer дата склеена «1августа2026». Проверить `formatLong` в `lib/date.ts` (или местный форматтер): исправить на «1 августа 2026» (пробелы), покрыть unit-тестом если есть тест на формат.

## 10. Прочее

- `how-calculated.tsx`: disclosure-строка — карточка по §2, chevron `ChevronDown` с rotate-200ms вместо символов ⌄/⌃ (сохранить aria-expanded/hidden-поведение).
- `period-context.tsx`, `today-lookahead.tsx`, `birth-time-banner.tsx`: карточки по §2, текст иерархии как в §3.

## Verification (обязательно, показать вывод)

- `npx vitest run 2>&1 | tail -4`
- `npx tsc --noEmit`
- `python3 scripts/grace_front_lint.py | tail -2`
- `git diff --check`

НЕЛЬЗЯ: менять data-testid/data-state/aria-контракты, трогать backend, contracts, e2e PNG, календарную логику данных, тексты контента (кроме бага «1августа2026»).
