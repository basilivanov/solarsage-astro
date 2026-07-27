# S3 TZ: премиальная визуальная система первого экрана Дня

Дата: 2026-07-27
Phase / Wave: **W-TODAY-PREMIUM-FIRST-SCREEN**, волна W1, срез S3
Master: `docs/work/2026-07-27_today-premium-first-screen/00_MASTER_TZ.md` (§4 дизайн-направление, D1–D9)
Modules: `M-TODAY-DAY-SUMMARY-CARD`, `M-ACTIVATION-EVIDENCE-CARD`, `M-TODAY-DATE-HEADER`, `M-DAY-COLLAPSIBLE`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal (один наблюдаемый результат)

Первый экран Дня выглядит дорого и спокойно: крупная serif-типографика в
герое и истории, воздух, единый радиус/волосные рамки, один violet-акцент.
Только CSS-классы — структура JSX, testid, обработчики, тексты и данные
не меняются. Визуальный ориентир: макет
`docs/work/2026-07-11_solarsage-v2-three-horizon-why-preview/assets/03-full-day-three-horizons-mobile.png`
(верхние ~2600px оригинала).

## 2. Exact write scope

- `components/today/date-header.tsx`
- `components/today/day-summary-card.tsx`
- `components/today/activation-evidence-card.tsx`
- `components/today/day-collapsible.tsx`

## 3. Frozen / out-of-scope

- `concrete-day-advice.tsx` (принят в S2+D9), `today-screen.tsx`,
  `why-expanded.tsx`, `why-time-horizon-card.tsx` (S4), `globals.css` (S4),
  всё остальное, backend/lib.
- Никаких изменений структуры JSX, data-testid, aria-атрибутов, текстов,
  пропсов, обработчиков — только className/стили.
- Моушн/анимации disclosure — S4 (transition-классы, уже стоящие, можно
  оставить; новые не добавлять).

## 4. Спецификация изменений

### 4.1 DateHeader

- eyebrow («Сегодня»/«День»): `tracking-[0.22em]` (было 0.14em).
- дата: `font-serif text-[24px]` (было 22px).
- стрелки: добавить `hover:border-violet-300 hover:text-violet-700
  dark:hover:text-violet-200 transition-colors`; `active:scale-95` сохранить.

### 4.2 DaySummaryCard — только humanFirst-ветка (герой статуса)

- statusLabel: `font-serif text-[26px] leading-tight` (было sans 16px
  semibold).
- statusLine: `text-[15px] leading-relaxed` (было 14px).
- иконка-squircle: `h-12 w-12 rounded-2xl` (было h-11 w-11).
- карточка: `p-5` (было px-4 py-4).
- отступ перед DayZoneIndicator: `mt-3`.
- legacy-ветку не трогать.

### 4.3 ActivationEvidenceCard (история)

- headline: `text-[28px] leading-[1.12]` (убрать sm:-вариант, один размер).
- карточка: `p-6` (было p-5).
- «Главное: …»: `py-3.5`.
- ranked sphere rows (`personal-story-sphere-link`): `min-h-[56px]
  rounded-2xl` (единый радиус с навигатором), иконка-shell `rounded-xl`.
- Why CTA (`personal-story-why-cta`): `min-h-12 rounded-2xl`.

### 4.4 DayCollapsible

- карточка: `rounded-[20px]`.
- кнопка: `px-5 py-4`; заголовок `text-[15px] font-semibold` (как сейчас).

### Общее

- Все dark:-классы обновить в паре со светлыми.
- Контраст текста не ухудшать; muted-фоны остаются мягкими.
- GRACE-разметку файлов обновить, если семантика блока уточняется
  (визуальные детали в contract не расписывать).

## 5. Must-preserve

- Все data-testid и их DOM-порядок; aria-контракты; условный рендер
  (null при отсутствии данных); бан-лист текстов (нет новых текстов).
- Поведение кликов/callbacks; swiper/scroll логика TodayScreen не затрагивается.

## 6. Verification (одна targeted-команда)

```bash
npx vitest run __tests__/components/TodayScreen.test.tsx __tests__/components/TodayScreen.v2-downstream.test.tsx __tests__/components/ActivationEvidenceCard.personal.test.tsx __tests__/components/DateHeader.test.tsx __tests__/today/day-summary-card.test.tsx
```

## 7. Expected evidence

- Список файлов, diff-вывод по классам (кратко), полный вывод verification.

## 8. Escalation rule

Нужен файл вне §2 или сомнение в макете — стоп, доложить, ждать новый
packet. Ничего не коммить и не пушить.
