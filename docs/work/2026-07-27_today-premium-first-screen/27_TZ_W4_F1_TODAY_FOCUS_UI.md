# W4-F1 TZ: блок TodayFocus на экране Дня (по дизайн-контракту 22_TZ)

Дата: 2026-07-28
Phase / Wave: **W4-TODAY-CONVERGENCE**, срез F1 (frontend)
Дизайн: `docs/work/2026-07-27_today-premium-first-screen/22_TZ_W4_TODAY_CONVERGENCE_DESIGN.md` — ОБЯЗАТЕЛЕН как binding oracle (композиция, состояния, кардинальность, testid, запреты)
Данные: `payload.focus` (TodayFocus) уже в payload на деве — contentState ready/unavailable/not_needed
Modules: новый `M-TODAY-FOCUS-CARD`, `M-TODAY-TODAY-SCREEN`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal

На экране Дня появляется блок «Что сошлось именно сегодня»/«События дня»
точно по дизайн-контракту: время первым столбцом моно, 0–3 события, 0–3
featured spheres с переходом в SphereDetailsSheet, пять product states и
четыре content states без единого пустого placeholder.

## 2. Exact write scope

- `components/today/today-focus.tsx` — **новый** компонент:
  - Root: `<section data-testid="today-focus" data-state={state} data-content-state={contentState}>`, `px-5`.
  - `convergence_today`: hero-карточка (eyebrow «СОШЛОСЬ СЕГОДНЯ» + счётчик
    факторов «0N ▸»; title serif 22; summary; divider; события; «Где
    проявится:» featured; пилюля действия из `featuredSpheres[0].action`;
    technical disclosure «Как это рассчитано»).
  - `single_impulses`: та же карточка, eyebrow «СОБЫТИЯ ДНЯ», без
    title/summary/featured/действия.
  - `background_only|no_accent`: одна muted-строка без карточки (тексты
    нормативные из родителя §3).
  - `unavailable`: muted-строка «Не удалось рассчитать акценты дня.
    Попробуй обновить позже.» + text-button «Обновить»
    (`data-testid="today-focus-retry"`, reload страницы дня через
    существующий refetch-механизм родителя; если его нет — скрыть кнопку).
  - **Event row**: `data-testid="today-focus-event"`, `data-event-kind`;
    время `w-12 font-mono tabular-nums text-[15px] font-semibold`
    (локальное время из `occursAt`+`timezone`, 24-часовой формат);
    title semibold; kind-текст («точный пик / начинается / пик завтра /
    ослабевает», цвет по семантике из дизайна §2); meaning muted под
    title; «пик завтра» — `opacity-60`.
  - **Featured row**: `data-testid="today-featured-sphere"`,
    `data-sphere-key`, `aria-haspopup="dialog"`, компактная
    (`min-h-[52px]`) версия строки из «Все сферы дня» (squircle-иконка +
    название + chevron), тап → `onSphereSelect(key)` родителя (открывает
    существующую SphereDetailsSheet).
  - **Content states**: `pending` — детерминированный skeleton (eyebrow,
    title, строки событий с временем видны; серые плейсхолдеры вместо
    meaning, `role="status" aria-busy`, sr-only «Разбор пишется…»);
    `unavailable` — факты видны, вместо LLM-полей muted-строка
    «Персональный разбор пока не готов»; `not_needed` — без LLM-секций.
  - Technical disclosure: `data-testid="today-focus-technical-toggle"`
    (aria-expanded/controls) + `today-focus-technical-content`: technical
    titles, число source activations, timezone, state label.
- `components/today/today-screen.tsx` — вставить блок **между
  DaySummaryCard и ActivationEvidenceCard** (позиция §1 дизайна),
  прокинуть `payload.focus` и `onSphereSelect`.
- `lib/contracts/today.ts` — типы TodayFocus из wire (generated), НЕ
  рукописные.
- `__tests__/components/TodayFocus.test.tsx` — все 5 states, 0/1/2/3
  events × 0/1/2/3 featured (кардинальность без placeholder), content
  states (ready/pending/unavailable/not_needed), kind-тексты, клик по
  featured вызывает onSphereSelect, «пик завтра» приглушён.

## 3. Frozen / out-of-scope

- Backend, LLM, тексты нормативных состояний (не менять).
- SphereDetailsSheet (использовать как есть), why-блок, disclosures.
- e2e и visual baselines (срез F2 — ревьюер).

## 4. Must-preserve

- Дизайн-запреты §13 родителя: нет трёх карточек ради симметрии, нет
  времени в абзаце, нет универсального текста вместо unavailable, нет
  цвета как единственного носителя состояния.
- Нет клиентского ranking/sorting фактов (порядок из payload как есть).
- GRACE-разметка + owned_tests; существующие testid экрана нетронуты.

## 5. Verification

```bash
npx vitest run __tests__/components/TodayFocus.test.tsx __tests__/components/TodayScreen.test.tsx
```

## 6. Expected evidence

- Файлы, вывод verification, список покрытых states/variants.

## 7. Escalation rule

Нужен файл вне §2 — стоп, доложить. Ничего не коммить и не пушить.
