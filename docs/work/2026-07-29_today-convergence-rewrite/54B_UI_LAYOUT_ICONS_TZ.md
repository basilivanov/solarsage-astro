# 54B — UI POLISH: LAYOUT + ICONS + MODALS TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(второй), cwd `/tmp/solarsage-convergence-b`, ветка `work/today-convergence-2b`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ — задачу
выполняешь сам и отчитываешься здесь ревьюеру. Параллельный кодер (54A)
делает tone-токены/формат времени в ДРУГОМ worktree — его файлы НЕ трогать
(§7).

## 1. Packet title

P7-POLISH-B — desktop двухколоночный layout с рейлом (03 §4), mobile
сетка тайлов, иконки сфер 24px, визуальная полнота модалок/drilldown/
sphere page/check-in по 03.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P7 polish (визуальная приёмка владельца).

## 3. Modules

- `M-TODAY-CONVERGENCE-SCREEN` — components/today-convergence/today-screen.tsx
- `M-SPHERE-NAVIGATOR` — components/today-convergence/sphere-navigator.tsx
- Новый: `M-SPHERE-ICONS` — components/today-convergence/sphere-icons.tsx
- Проверочные правки: sphere-drilldown, sphere-page, checkin, preview/paywall

## 4. Goal

Экран соответствует 03 §4 (desktop: основная 640 + рейл 400, gap 32,
max-width 1120; в рейле — Контекст периода, Сферы жизни, Как это
рассчитано), §6 (тайл = иконка 24px + название sans 13, сетка
mobile 3×4 / tablet 4×3 / desktop 6×2 — в рейле 3×4), §5-§9 (все
состояния экрана, модалки и disclosures полные, без упрощений).

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/03_W7_FRONTEND_DESIGN_TZ.md`
  ЦЕЛИКОМ (§4 сетка, §5 компоновки состояний, §6 навигатор, §7 drilldown/
  страница сферы, §8 календарь/check-in, §9 поведение, §11 test contract,
  §12 accessibility).
- Текущее: desktop — одна узкая колонка (нет рейла); тайлы — буква вместо
  иконки 24px; на 390px третий тайл обрезан.
- Живые скрины дефектов: /tmp/day-review/*.png (прочитать картинки!).

## 6. Exact write scope

- `components/today-convergence/today-screen.tsx`
- `components/today-convergence/sphere-navigator.tsx`
- `components/today-convergence/sphere-icons.tsx` (новый: 12 SVG-иконок
  сфер, простые stroke-формы, единый стиль)
- `components/today-convergence/sphere-drilldown.tsx`
- `components/today-convergence/sphere-page.tsx`
- `app/(grace)/day/snapshots/[id]/spheres/[key]/page.tsx`
- `app/(grace)/day/spheres/[key]/page.tsx`
- `components/checkin/checkin-screen.tsx` — только визуальные правки
- `__tests__/components/today-convergence/*.test.tsx`,
  `__tests__/components/CheckinScreen.test.tsx` — синхронизация assertions
  (DOM-контракт сохранить!)

## 7. Frozen / Out of scope

- `components/today-convergence/today-formatters.ts`,
  `convergence-hero.tsx`, `impulses-list.tsx`, `main-event.tsx`,
  `app/globals.css` — packet 54A, НЕ трогать.
- Backend, contracts, e2e specs (baseline обновляет ревьюер отдельно).

## 8. Функциональные требования

### 8.1 Desktop layout (03 §4)

- Контентная колонка mobile 360–430px (padding 20); desktop (≥1024px):
  grid `minmax(0,640px) minmax(0,400px)`, gap 32, max-width 1120, центр.
- Рейл (порядок): «Контекст периода» (period-context), «Сферы жизни»
  (sphere-navigator), «Как это рассчитано» (how-calculated).
- Основная колонка: дата-навигация, hero/main-event, импульсы,
  LLM-зона (narrative), lookahead, birth-time banner, general-sky.
- Mobile/tablet: всё в один поток, сферы после основного контента (как
  сейчас, но сетка по §6).

### 8.2 Навигатор сетка (03 §6)

- mobile 3×4, tablet (≥640px) 4×3, desktop (≥1024px) 6×2; в рейле —
  всегда 3×4. Тайлы резиновые (minmax(0,1fr)), НЕ обрезаются на 360px.
- Тайл: высота 88px, иконка 24px + название sans 13 (одно слово; длинные
  — типографическое сокращение, не многоточие). Маркер-точка 8px
  нейтральный ink в правом верхнем углу для `data-has-today=true`.
- 12 SVG-иконок в `sphere-icons.tsx`: единый stroke 1.5, без заливки,
  текущий цвет (currentColor). Простые геометрические метафоры
  (work — портфель/квадрат, money — монета, documents — лист,
  relationships — два круга, sport — пульс, communication — пузырь,
  health — крест/сердце, decisions — весы, travel — стрелка,
  creativity — искра, study — книга, shopping — пакет).
- Tap ≥44px, focus-visible.

### 8.3 Модалки и disclosures (проверка по 03, доделка)

- Drilldown (§7): заголовок «<Сфера> — сегодня», нумерованная цепочка
  событий (время по формату, polarity метка+текст), основание связи
  (convergence), disclosure «Как это рассчитано» (aria-expanded/controls,
  контент hidden, не удаляется из DOM). Если сейчас проще — доделать.
- Sphere page (§7): слой 1 «В твоей карте», слой 2 «Сейчас действует» с
  датой окончания; запрет слов «сегодня»/«завтра»; houses-hidden пометка
  при bucket/unknown.
- Check-in (§8.2): форма как раньше + forecast recap нейтральный;
  observed_spheres мультиселект — 12 сфер в 2 колонки ≥44px.
- Preview paywall (§5.7): teaser сфер + paywall сразу за ним, существующий
  `data-testid="paywall"`.
- Loading/error/disclosure/animation (§9): role=status скелетоны,
  role=alert ошибки, disclosure chevron-rotate 200ms, prefers-reduced-motion
  отключает анимации (проверить/добавить `motion-reduce:transition-none`).

### 8.4 DOM-контракт

Все data-testid/data-* из 03 §11 и AGENTS.md сохраняются (data-day-tone,
data-content-state, data-access-state, data-birth-time-mode,
convergence-hero, sphere-tile-{key}, sphere-navigator, drilldown,
sphere-page, today-narrative...). Layout-классы менять можно, атрибуты — нет.

## 9. Must-preserve invariants

- `npx vitest run` зелёный; `npx tsc --noEmit` чист; grace_front_lint PASS.
- Никаких красных цветов и tone-заливок тайлов/календаря.

## 10. Verification

```bash
cd /tmp/solarsage-convergence-b
npx vitest run __tests__/components 2>&1 | grep -E "Test Files|Tests "
npx vitest run 2>&1 | grep -E "Test Files|Tests "
npx tsc --noEmit 2>&1 | tail -2
python3 scripts/grace_front_lint.py 2>&1 | tail -1
NODE_ENV=production npx next build --webpack 2>&1 | tail -3
```

## 11. Expected evidence

- Diff по файлам; подтверждение DOM-контракта (grep data-testid до/после);
  текстовое описание новой раскладки (дерево блоков); иконки (список).
- Скриншоты не требуются — визуальную приёмку делает ревьюер отдельно.

## 12. Escalation rule

Нужно менять файлы 54A или DOM-контракт → СТОП, доложить.

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
