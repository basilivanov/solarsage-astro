# W4 DESIGN: «Что сошлось именно сегодня» — визуальная система блока TodayFocus

Дата: 2026-07-28
Статус: **design contract, готов к frontend implementation TZ**
Родительский контракт: [`21_TZ_W4_TODAY_CONVERGENCE_EVENTS_PERFORMANCE.md`](./21_TZ_W4_TODAY_CONVERGENCE_EVENTS_PERFORMANCE.md) (§3 states, §5 API, §6 текст, §12.4 testid, §13 бриф)
Дизайн-система: премиум-минимализм W1 (тёплая бумага, serif display, один violet-акцент, hairline-карточки, мягкие тени, 250ms premium easing, reduced-motion).
Этот документ не меняет смысловые правила родительского контракта. Любое расхождение — в пользу родителя.

---

## 0. Дизайн-тезис

Блок читается за 3 секунды как **хроника дня, а не карточка прогноза**:

> вывод (одна строка) → события со временем (время — первый визуальный столбец) → 0–3 сферы → одно действие.

Время — самый сканируемый элемент: оно никогда не прячется в предложении, всегда стоит в фиксированной колонке слева, моноширинными цифрами. Состояние блока читается без единого прочитанного слова: по наличию/отсутствию строк событий, а не по цвету.

---

## 1. Позиция в композиции экрана

Текущий порядок экрана (W1) сохраняется; блок встаёт **между карточкой статуса и карточкой истории**:

```text
1. DateHeader
2. [TrialBanner] [вечерний чекин]
3. DaySummaryCard (статус + зона)
4. **TodayFocus (новый блок, data-testid="today-focus")**
5. ActivationEvidenceCard («Именно для тебя» + «Главное» + ranked top-3)
6. «Все сферы дня» (12 строк, навигатор состояния)
7. «Почему так у меня» (teaser → модалки горизонтов)
8. Disclosure «Полный разбор дня» / «Как это рассчитано»
9. Footer disclaimer
```

На state=`background_only|no_accent|unavailable` блок НЕ героический: одна тихая строка (§4), экран визуально переходит сразу к карточке истории. Hero-карточку строим только при `convergence_today`; при `single_impulses` — компактная карточка событий.

---

## 2. Анатомия блока (state = convergence_today)

```text
┌─────────────────────────────────────────┐
│ СОШЛОСЬ СЕГОДНЯ                    01 ▸ │  ← eyebrow + счётчик факторов (дет.)
│                                         │
│ Тема личного темпа и самоощущения       │  ← convergence.title (serif 22px)
│                                         │
│ Вечером несколько факторов одновременно │  ← convergence.summary (max 220)
│ задевают одну тему. Оставь запас между  │
│ первой реакцией и решением.             │
│ ─────────────────────────────────────── │
│ 19:24  Луна в напряжении с твоим        │  ← event row: ВРЕМЯ (моно) + title
│        Солнцем · точный пик             │
│        Реакция может быть глубже        │  ← event.meaning (max 160, muted)
│        обычного.                        │
│                                         │
│ 19:40  Луна напротив твоей Луны ·       │
│        точный пик                       │
│                                         │
│ Где проявится:                          │  ← featured spheres (0–3)
│ ▸ Спорт и тело      ▸ Решения           │
│                                         │
│ [ Осторожнее с импульсивными решениями ]│  ← одно действие (сфера action)
│ ─────────────────────────────────────── │
│ Как это рассчитано                    ⌄ │  ← technical disclosure
└─────────────────────────────────────────┘
```

Спецификация:

- **Root**: `<section data-testid="today-focus" data-state="convergence_today" data-content-state="ready" class="px-5">`, карточка `rounded-[24px] border border-border/60 bg-card p-5 shadow-[0_18px_48px_-28px_rgba(76,29,149,0.35)]`.
- **Eyebrow**: «СОШЛОСЬ СЕГОДНЯ» — `text-[11px] font-semibold uppercase tracking-[0.16em] text-violet-700`. Счётчик `01 ▸` — число independent факторов (детерминированное), muted, справа. Не LLM.
- **Title**: `font-serif text-[22px] leading-tight`, backend title (max 64).
- **Summary**: `text-[15px] leading-relaxed text-foreground/85`, max 220.
- **Divider**: `border-t border-border/40` с `my-3.5`.

### Event row (главный повторяемый элемент)

```text
┌────────┬──────────────────────────────────┐
│ 19:24  │ Луна в напряжении с твоим Солнцем │
│ моно   │ · точный пик                      │
│ 15px   │ Реакция может быть глубже обычного.│
└────────┴──────────────────────────────────┘
```

- `data-testid="today-focus-event"`, `data-event-kind="exact|starts|peak|building|separating"`.
- **Время**: колонка фикс-ширины `w-12`, `font-mono text-[15px] font-semibold`, `tabular-nums`, цвет `text-foreground`. Всегда первым элементом строки — никогда в тексте.
- **Kind chip**: «точный пик / начинается / пик завтра / ослабевает» — `text-[12px] font-medium` после title через ` · `, цвет по семантике: exact/peak → violet-700, starts/building → amber-700, separating → slate-500. Текст обязателен, цвет вторичен.
- **Meaning**: `text-[13.5px] leading-relaxed text-muted-foreground`, max 160, под title с того же левого края (не под колонкой времени).
- Строки разделены `space-y-3.5` (без рамок между событиями — воздух вместо линий).
- При `precision=date|window` в колонке времени: «днем» / «весь день» (не выдуманные часы).
- «Пик завтра»: время НЕ показывается как сегодняшнее; строка получает kind «пик завтра» и приглушение (opacity-60), максимум одна такая строка после основных.

### Featured spheres

- Заголовок мелкий: «Где проявится:» `text-[12px] font-semibold text-muted-foreground`.
- Сферы — те же row-стили, что «Все сферы дня» (иконка-squircle + название + chevron), но **компактные** (`min-h-[52px]`), без verdict-чипа (state уже задан контекстом блока).
- `data-testid="today-featured-sphere"`, `data-sphere-key`, `aria-haspopup="dialog"`.
- Тап → существующая `SphereDetailsSheet` этой сферы (§6 click-flow).

### Одно действие

- Одна строка-пилюля: `rounded-2xl border border-violet-200/70 bg-violet-50/55 px-3.5 py-2.5 text-[14px] font-medium`, max 100 символов, из `featured_spheres[0].action` (первая сфера). Не дублирует summary.

### Technical disclosure

- «Как это рассчитано» — `DayCollapsible`-совместимый контрол (`aria-expanded/aria-controls`, `data-testid="today-focus-technical-toggle"`), внутри: technical titles событий (без Transit_/Natal_ префиксов), `source_activation_ids` count, timezone пользователя, state label. Только disclosure, никогда в потоке.

---

## 3. Остальные состояния (все 390×844)

### single_impulses — «События дня»

Та же карточка, но eyebrow «СОБЫТИЯ ДНЯ», **без title/summary схождения** (нет общего сюжета — не выдумываем). События 1–3 теми же строками. Featured spheres и action отсутствуют — после событий сразу disclosure. Никакой фразы «Что сошлось».

### background_only — «Фон текущего периода»

Не карточка, а **тихая строка** (без рамки): `px-5 text-[13px] leading-relaxed text-muted-foreground`, формат «Фон периода: {короткий детерминированный текст}». Максимум 2 строки. Никакого времени, никаких событий.

### no_accent

Одна muted-строка: «Сегодня нет выраженного схождения нескольких факторов.» — `text-[13px] text-muted-foreground/80`, без карточки, без иконки, без кнопки. Блок занимает ≤24px высоты и визуально «отпускает» взгляд к карточке истории.

### unavailable

`role="alert"` НЕ используем (это не ошибка пользователя). Тихая строка: «Не удалось рассчитать акценты дня. Попробуй обновить позже.» + маленькая text-button «Обновить» (retry, `data-testid="today-focus-retry"`). Без красного, без спиннера.

### content_state = pending

Блок рендерит **фактический skeleton немедленно**: eyebrow + title (детерминированные), строки событий с временем и title (детерминированные), вместо meaning — 2 серые строки-плейсхолдера (`animate-pulse`, `aria-busy="true"`, `role="status"` с текстом «Разбор пишется…» в sr-only). Никакого полноэкранного спиннера. Pending допустим только при реально запущенной retryable-генерации (контракт).

### content_state = unavailable

Детерминированные факты показываются (время, titles, state), LLM-поля — честная muted-строка «Персональный разбор пока не готов» ВМЕСТО summary/meaning. Никакого универсального текста вместо модели (запрет §6.6).

### content_state = not_needed

Как ready, но без LLM-секций вообще (state не требует интерпретации).

---

## 4. Кардинальность (запрет пустых placeholders)

| events | featured spheres | Рендер |
|---|---|---|
| 0 | 0 | state != convergence_today по контракту; hero-карточки нет |
| 1 | 0 | одна строка события, без секции «Где проявится» |
| 1 | 1 | строка + одна сфера |
| 2 | 2 | две строки + две сферы |
| 3 | 3 | максимум; четвёртой не бывает никогда |

Пустых рамок, серых карточек «здесь могло бы быть» и искусственной симметрии на 3 — **запрещено** (§13).

---

## 5. Как отличить «событие расчёта» от «возможного проявления»

Двухуровневая типографика без лишних подписей:

- **Факт**: время (моно, тёмный) + title события (foreground, semibold) — это расчёт.
- **Проявление**: meaning (muted, на 1px меньше, с «может/вероятнее/обрати внимание» по текст-контракту).

Визуально факт и проявление различаются весом и цветом, не иконками и не бейджами «факт/мнение» (шум).

---

## 6. Click-flow: featured sphere → 12 сфер

1. Тап по featured sphere → открывается существующая `SphereDetailsSheet` (та же модалка, что из «Все сферы дня»): story/why/advice + бейдж verdict.
2. Кнопка «Почему так у меня» в модалке ведёт в блок why (как сейчас).
3. Кнопка «Закрыть» возвращает фокус на featured row (`focus-visible` ring).
4. Никакой второй/специальной модалки для featured — один компонент, один контракт.

---

## 7. Responsive, dark, motion, длинные строки

- **Mobile-first 390px**: вся спецификация выше. Время не переносится на вторую строку; title события переносится по словам, meaning тоже.
- **Desktop**: блок ограничен той же колонкой `max-w-md` (система), сетку не растягиваем.
- **Dark mode**: пары классов на каждый светлый (bg-card, border, violet-*) по образцу DaySummaryCard.
- **Motion**: появление блока — `disclosure-in` (существующий keyframes, 250ms ease-premium); pending-плейсхолдеры — `animate-pulse`; всё под `motion-reduce:transition-none animation-none`.
- **Focus**: featured rows и retry — `focus-visible:ring-2 ring-violet-500 ring-offset-2`.
- **Длинные строки**: title до 64, summary до 220, meaning до 160 — line-clamp не применяем (лимиты backend-owned), перенос по словам; время не сжимается (tabular-nums держит колонку ровной).

---

## 8. Semantic/test contract (фиксировано по §12.4)

```text
section        data-testid="today-focus"
               data-state="convergence_today|single_impulses|background_only|no_accent|unavailable"
               data-content-state="ready|pending|unavailable|not_needed"
event row      data-testid="today-focus-event"   data-event-kind="exact|starts|peak|building|separating"
featured row   data-testid="today-featured-sphere" data-sphere-key aria-haspopup="dialog"
retry          data-testid="today-focus-retry"
tech toggle    data-testid="today-focus-technical-toggle" aria-expanded aria-controls
tech content   data-testid="today-focus-technical-content"
pending        role="status" aria-busy="true" (+ sr-only «Разбор пишется…»)
```

Запреты §13 соблюдены: нет раскраски-состояния без текста, нет клиентского ranking, нет девяти why-секций, нет универсального fallback-текста.

---

## 9. Артефакты приёмки (маппинг на §13.3)

| # | Артефакт | Где покрыт |
|---|---|---|
| 1 | Mobile 390×844 все 5 states | §2, §3 |
| 2 | 0/1/2/3 events × 0/1/2/3 spheres | §4 таблица |
| 3 | Desktop | §7 |
| 4 | Disclosure open/closed | §2 (technical) |
| 5 | ready/pending/unavailable/not_needed | §3 |
| 6 | Событие «пик завтра» у полуночи | §2 (event row, «пик завтра») |
| 7 | A11y + testids | §7, §8 |
| 8 | Click-flow featured → 12 сфер | §6 |

Финальные PNG-макеты по этому документу делает frontend-волна на mock-fixtures (`e2e/mock-visual` canary 28/29 июля из родительского контракта) — текстовая композиция здесь является binding oracle для них.

---

## 10. Решения владельца (2026-07-28, закрыто)

1. **Счётчик факторов «01 ▸» в eyebrow — ОСТАВЛЯЕМ.** Показывает силу схождения детерминированно, без LLM.
2. **Одно действие — из первой featured сферы (`action`), НЕ из `mainAdvice`.** mainAdvice уже живёт в карточке истории («Главное») и дублировал бы её. Если `action` отсутствует/null — пилюля действия скрывается (no-fallback политика).
3. **«Пик завтра» — приглушённой строкой в потоке** (opacity-60, после основных событий, максимум одна), как специфицировано в §2.
