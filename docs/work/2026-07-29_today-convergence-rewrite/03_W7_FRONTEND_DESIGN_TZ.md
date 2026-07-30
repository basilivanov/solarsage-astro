# W7 FRONTEND/DESIGN TZ — Today Convergence Rewrite (новая модель)

Дата: 2026-07-30
Статус: implementation-ready draft для design/вёрстка-модели. Визуальные токены и компоновки — предложение, утверждается владельцем по visual baseline (§14).
Нормативные входы: `00_MASTER_TZ.md` v1.12 (D1–D14, §16–17), `04_W2_W3_RUNTIME_CONTRACT_TZ.md`, `02_TONE_POLICY_AMENDMENT.md` (frozen, owner-approved 2026-07-30), распределения `analysis/corpus_replay_tone_v3.md`.

## 1. Наследование

**Визуальный язык берём из старого дизайн-ТЗ (S3):** тёплая бумага фона, serif для героя и заголовков сфер, сливовый (plum) акцент как фирменный/интерактивный, янтарный tense, карточки с радиусом 24 px, спокойные тени.

**НЕ переносим:** старые состояния (supportive/steady/tense как глобальный статус дня), чипы вердиктов сфер, зональный индикатор, DaySummaryCard, старые test-id и `data-status="calm|tense|favorable|neutral"` (весь старый UI-контракт — superseded; AGENTS.md уже синхронизирован, компоненты/fixtures заменяются W7, оставшийся runtime удаляется W9).

Wire-поля, nullability, endpoint semantics и access projection берутся только
из `04_W2_W3_RUNTIME_CONTRACT_TZ.md`. Frontend не объявляет параллельный ручной
shape и не восстанавливает отсутствующие поля из legacy payload.

## 2. Контрактные оси экрана (источник правды для всех макетов)

| ось | значения | откуда |
|---|---|---|
| `screenState` | loading / ready / error | transport/fetch |
| `state` | convergence_today / quiet_day / unavailable; `null` только при locked | расчёт |
| `dayTone` | steady / supportive / mixed / tense; `null` при unavailable/locked | tone policy (frozen) |
| `contentState` | ready / pending / unavailable / not_needed | LLM-фаза |
| `access` | full / preview / locked | доступ |
| `birthTimeMode` | exact / bucket / unknown | профиль |

Ортогональность обязательна: `quiet_day + steady` НЕ прячет импульсы;
`unavailable` (расчёт) ≠ `contentState=unavailable` (LLM) ≠ `locked` (доступ).
При locked расчётный `state=null`, snapshot и персональные события отсутствуют.
`screenState` не подменяет расчёт: network error — это `screenState=error`, а
валидный HTTP 200 с неготовым расчётом — `screenState=ready + state=unavailable`.

## 3. Цветовая система (semantic tokens)

Фон — тёплая бумага (наследуем из S3-токенов). Polarity-цвета — только как лёгкий фон/метка, никогда единственный носитель смысла (всегда + текст/иконка):

| token | назначение | цвет (предложение) |
|---|---|---|
| `--tone-supportive-bg` / `-fg` | supportive-метка | мягкий шалфейный зелёный |
| `--tone-tense-bg` / `-fg` | tense-метка | янтарный (наследуемый); **красный запрещён везде** |
| `--tone-mixed-bg` / `-fg` | mixed-метка | нейтральный тауп |
| `--tone-steady-*` | steady | базовый текст, БЕЗ акцента и без метки |
| `--accent` | интерактив, ссылки, hero-рамка | сливовый (только бренд, НЕ polarity) |

`dayTone` влияет на тон hero-блока и строку-индикатор (если есть). **Запрещено красить** 12 статических тайлов навигатора, календарные чипы (кроме hero-точки) и страницы сфер.

## 4. Типографика и базовая сетка

- Заголовок hero: serif 28/34; имя сферы в hero: serif 20/26; подписи секций: sans 13/18 caps-muted; тело: sans 15/22; время: sans 15 tabular-nums.
- Сетка: контентная колонка mobile 360–430 px (padding 20), desktop max-width 1120 px, две колонки (основная 640 + рейл 400, gap 32): в рейл уходят «Контекст периода», «Сферы жизни», «Как это рассчитано».
- Карточки: radius 24, padding 20/24, тень спокойная (наследуемая), без бордеров у hero (рамка 1.5px `--accent` только в hero-режиме).
- Tap targets ≥ 44 px; фокус-visible обязателен; `prefers-reduced-motion` отключает анимации.

## 5. Экран дня — компоновки по состояниям

Общий скелет (mobile):

```text
DateHeader (← Сегодня, 30 июля →)        [свайпы/стрелки]
[TrialBanner] [вечерний чекин-баннер]    (условные)
<главный блок по state>
Контекст периода ▸                        (disclosure, collapsed)
Сферы жизни (12 статических тайлов, §6)
Как это рассчитано ▸                      (disclosure)
дисклеймер
```

### 5.1 convergence_today — hero

```text
┌──────────────────────────────────────┐
│ ЧТО СОШЛОСЬ СЕГОДНЯ            [tone]│ ← caps-подпись + tone-метка
│                                      │
│ Работа                               │ ← serif, имя сферы
│ Меркурий спорит с твоим Сатурном:    │ ← LLM summary (≤220 chars,
│ тема сроков обостряется, пик 15:40.  │   перенос по словам, без
│ Разговор о дедлайне перенеси         │   обрезки/многоточий)
│ на вечер: после 18:00 спадает.       │
│ Почему сошлось →                     │ ← ссылка в drilldown
│                                      │
│ Также сегодня:                       │ ← если 2–3 сферы
│ · Отношения — поддержка, пик 19:24   │
│ · Энергия — внимание к вечеру        │
│                                      │
│ Импульсы дня                         │ ← 1–3 строки (§5.4)
│ 19:24 — Луна в гармонии с Венерой    │
└──────────────────────────────────────┘
```

Правила: tone-метка только одна (у hero-блока, `dayTone`), у каждой сферы — своя polarity текстом («напряжение»/«поддержка»/«смешанно»), НЕ цветом карточки. Hero всегда один; вторичные сферы — строки 5–7 слов, кликабельны в drilldown.

### 5.2 quiet_day — импульсы (дефолтный режим, ~85–95% дней)

```text
┌──────────────────────────────────────┐
│ Импульсы дня                   [tone]│
│                                      │
│ 19:52 — Марс напротив твоего         │
│ Нептуна, точный пик.                 │
│ Спор о контроле быстро перерастает   │
│ в борьбу за принцип. Уступи          │
│ формулировку — забери суть.          │
│                                      │
│ 21:10 — Луна в гармонии с Меркурием  │
└──────────────────────────────────────┘
```

0–3 импульса. При 0 — блок импульсов не рендерится, но остаётся детерминированный
`periodContext` + навигатор. Для `kind=no_strong_accent` короткий заголовок:
«Без выраженного акцента» — без придуманного совета (steady ≠ пустой экран:
медиана 3 selected units по корпусу). Слово «сошлось» запрещено в любом тексте
режима (review-gate).

### 5.3 quiet_day + main_event

Как 5.2, но первый блок — «Главное событие дня» (одно редкое событие без пары): та же карточка, без метки «сошлось». Импульсы — ниже отдельной секцией.

### 5.4 quiet_day + personal:false (только unknown-time, крайний случай)

```text
Общий фон дня                        [ⓘ]
Луна в Тельце, Марс квадрат Сатурн (точный сегодня).
Персонального схождения без точного времени сегодня не видно.
Уточнить время рождения →
```

Маркер «не персональный прогноз» обязателен. LLM-текст запрещён — только детерминированные факты неба.

### 5.5 unavailable (расчёт)

Персональный snapshot и его факты не показываются: блок-статус «Не удалось
рассчитать день. Обновить» и retry-кнопка (single-flight, §9 и runtime §6). Без красного и
без имитации частичного персонального расчёта. Уже рассчитанные факты остаются
видимыми только в отдельном случае `contentState=unavailable`, когда сломался
LLM, а deterministic snapshot готов.

### 5.6 contentState=pending (LLM ещё пишет)

Скелетон ТОЛЬКО в зоне LLM-полей (summary/meaning); детерминированные данные (время, сферы, импульсы) рендерятся сразу. `aria-live="polite"` на зоне: при готовности контент догружается без перерендера экрана. Никаких полноэкранных спиннеров.

### 5.6.1 contentState=unavailable (LLM не готов)

Детерминированные сферы, события, времена и `dayTone` остаются. Только в
LLM-зоне показывается честная строка «Персональный разбор пока не готов» и
retry с cooldown; все LLM-owned поля `null`. Скелетон, универсальный совет и
текст, имитирующий персональную интерпретацию, запрещены.

### 5.7 access=preview/locked

Preview показывает только `state`, `dayTone` и названия сфер из
`previewTeaser`, затем paywall; evidence, времена, drilldown и LLM-текст не
рендерятся. Locked — без расчётного state, convergence-содержимого и snapshotId.
Paywall-карточка наследуется из W1-визуала (сливовая), существующий
`data-testid="paywall"` сохраняется.

### 5.8 Плашка birth-time (bucket/unknown, один раз, dismissible)

```text
ⓘ Время рождения не указано: точные часы и дома не показываем. Уточнить →
```

Спокойная, не sticky, не модалка. После dismiss — только пункт в профиле.
Плашка показывается только при `birthTimePromptDismissed=false`; dismiss
персистится через Profile contract. Для legacy-профилей, мигрированных
`null → unknown`, migration сразу ставит `true`, поэтому релиз не создаёт
массовую плашку. Новые пользователи, явно выбравшие bucket/unknown, начинают с
`false`.

### 5.9 Lookahead (только quiet_day)

Опциональная одна строка «Завтра факторы сходятся в <сфере>» показывается только
если API передал `lookahead` из уже published snapshot следующего локального
дня. Frontend сам завтра не рассчитывает и при `lookahead=null` блок полностью
скрывает. Impression с `surface=lookahead` отправляется только когда строка
впервые вошла во viewport; `sourceSnapshotId` — snapshot открытого дня.

## 6. Навигатор «Сферы жизни»

- Сетка: mobile 3×4, tablet 4×3, desktop 6×2 (в рейле — 3×4).
- Тайл: высота 88 px, иконка 24 px + название sans 13 (одно слово, перенос запрещён — «Творчество» сокращается типографикой, не многоточием).
- Порядок фиксирован: work, money, documents, relationships, sport, communication, health, decisions, travel, creativity, study, shopping.
- Маркер «есть разбор сегодня»: точка 8 px в правом верхнем углу, цвет — нейтральный ink (НЕ tone-цвет, НЕ plum). Тап по маркированному → drilldown; по остальным → статическая страница сферы.
- Запрещено: бейджи, счётчики, стрелки, tone-заливка, «Нейтрально».

## 7. Drilldown «Почему сошлось» и страница сферы

Drilldown (см. master §16): заголовок «<Сфера> — сегодня», доказательная цепочка (нумерованные драйверы с временами), основание связи, окна, «Контекст сферы», disclosure «Как это рассчитано». Полностью детерминирован — loading только на подгрузке snapshot.

Страница сферы: слой 1 «В твоей карте» (натал, длинный текст, перенос по абзацам), слой 2 «Сейчас действует» (длинные темы с датами окончания). Review-gate: слова «сегодня»/«завтра» запрещены; дома при bucket/unknown скрыты с честной пометкой (§5.8).

## 8. Календарь и Yesterday/check-in

### 8.1 Календарь

Три различимых состояния дня (НЕ два):

```text
30 ●   — был hero (заполненная точка 6 px, нейтральный ink)
31     — обычный рассчитанный день (ничего)
—  ○   — данные ещё не рассчитаны (пустой круг 6 px, muted outline)
```

Запрещены: заливки старой valence (зелёный/красный фон), tone-цвета чипов, подписи. «Обычный» и «не рассчитан» визуально не перепутать: отсутствие маркера ≠ пустой круг.

### 8.2 Yesterday / вечерний check-in

Источник — только generated `YesterdayCheckinResponse` из runtime §6. Экран
сохраняет существующие mood/energy/accuracy, streak и один опциональный
мультиселект `observed_spheres`; per-sphere polarity/intensity matrix не
добавляется.

До submit пользователь видит дату и форму, но не `dayTone`, `sphereKeys` и не
строку «Прогноз: …»: это не должно подсказывать ответ. Допустима только
нейтральная отметка «Прогноз за этот день сохранён», если
`forecastAvailable=true`. После успешного submit/refetch:

```text
Как прошёл вчерашний день              [сохранено]
Твои отметки: …

Что было в прогнозе
Работа · Общение
Тон: смешанный
```

Post-submit recap показывается только при `forecastRecap != null`; при
отсутствии impression или snapshot блок целиком скрыт, check-in остаётся
доступен. Recap нейтральный, без tone-заливки и без оценки «угадали/не угадали».
Стабильные selectors: `checkin-screen`, `observed-spheres`,
`yesterday-forecast-available`, `yesterday-forecast-recap`.

## 9. Поведение: loading, retry, disclosure, анимации

- Loading зон: `role="status"`, скелетоны по форме контента (не спиннер).
- Ошибка самого fetch: root `data-screen-state="error"`, `role="alert"` и одна
  кнопка повторной загрузки; она не изображается как `state=unavailable`.
- Retry: одна кнопка, disabled + countdown после клика (single-flight lease, master §5.3); ошибки retry — текстовая подпись без красного.
- Disclosure: `aria-expanded`/`aria-controls`, chevron-rotate 200 ms; контент не удаляется из DOM при collapse (только `hidden`).
- Анимации: 150–250 ms ease-out, только opacity/transform; без bounce, без parallax; reduced-motion → мгновенно.
- Переход pending→ready: контент появляется fade-in 200 ms, без сдвига раскладки (зона зарезервирована).
- Impression `surface=day` отправляется после первого успешного paint доступного
  deterministic блока. Preview, locked, transport error и `state=unavailable`
  impression не создают; сбой telemetry endpoint не ломает экран.

## 10. Тексты: переносы и время

- LLM-тексты: UI рендерит только `.text` из claim-bound поля; жёсткие лимиты валидатора (`summary.text` ≤ 220 chars); перенос по словам, `text-wrap: pretty`; запрещены обрезка `…`, дефисы-переносы, многоточия в конце.
- Длинные названия сфер — типографическое сокращение, не многоточие.
- Время — tabular-nums; форматы по режиму:

| режим | пик | окно |
|---|---|---|
| exact | `15:40` | `пик 15:40, окно 13:00–18:00` |
| bucket | `во второй половине дня` | `ближе к вечеру` |
| unknown | часть суток или только дата | без окна |

- Шаблонные заглушки запрещены везде (норматив §6.6); отсутствие контента → честный статусный текст из C1-реестра констант.

## 11. Test contract (data-*)

Root: `data-testid="today-screen"`, `data-screen-state`, `data-state`,
`data-day-tone`, `data-content-state`, `data-access-state`,
`data-birth-time-mode`. Nullable расчётные атрибуты не получают строку `"null"`:
они отсутствуют при loading/error/locked.

| блок | selector | атрибуты |
|---|---|---|
| hero | `data-testid="convergence-hero"` | `data-day-tone`, `data-evidence-level="high"` |
| hero-сфера | `data-testid="convergence-sphere-{key}"` | `data-polarity` |
| вторичные | `data-testid="convergence-secondary"` | — |
| main_event | `data-testid="main-event"` | `data-polarity` |
| импульсы | `data-testid="impulses-list"` | `data-count` |
| импульс | `data-testid="impulse-{eventId}"` | `data-polarity`, `data-time-mode="exact\|partofday\|date"` |
| навигатор | `data-testid="sphere-navigator"` | — |
| тайл | `data-testid="sphere-tile-{key}"` | `data-has-today="true\|false"` |
| drilldown | `data-testid="sphere-drilldown"` | `data-sphere` |
| страница сферы | `data-testid="sphere-page"` | `data-sphere`, `data-birth-time-mode` |
| календарь | `data-testid="calendar-screen"` | — |
| день | `data-testid="calendar-day-{date}"` | `data-day-state="hero\|ordinary\|not-computed"` |
| общий фон | `data-testid="day-general-sky"` | — |
| плашка времени | `data-testid="birth-time-banner"` | — |
| LLM-зона | `data-testid="today-narrative"` | `data-state="ready\|pending\|unavailable\|not_needed"` |
| lookahead | `data-testid="today-lookahead"` | `data-target-date` |

Старые id (`today-summary`, `data-status="calm|tense|favorable|neutral"`, `day-status-*`) удаляются при замене компонентов W7. AGENTS.md «UI Semantic/Test Contract» уже синхронизирован с новым публичным контрактом; оставшийся недостижимый backend/runtime удаляется W9.

## 12. Accessibility

- Loading: `role="status"`; ошибки: `role="alert"`; модалки/sheet: `role="dialog"` + `aria-modal`.
- Все icon-only кнопки — `aria-label`; навигация — `nav` + `aria-current`.
- Tone/полярность никогда не только цветом: всегда текстовая метка.
- Контраст AA на тёплой бумаге (проверить янтарный fg на бумаге — обязательный gate).

## 13. Эталонные fixtures и visual regression

Payload fixture-матрица (16 экранов; каталог
`__tests__/fixtures/today_convergence_v2/` создаётся в W7):

1. hero × supportive; 2. hero × tense; 3. hero × mixed (2 сферы); 4. hero 3 сферы; 5. quiet × steady (3 импульса + lookahead); 6. quiet × tense-импульс; 7. quiet × 0 импульсов; 8. main_event + 3 импульса + lookahead (максимальный legal quiet payload); 9. personal:false (общий фон); 10. pending; 11. contentState=unavailable; 12. state=unavailable; 13. bucket-режим; 14. unknown-режим; 15. preview; 16. locked.

Visual regression: структурные снапшоты, LLM-текстовые зоны — маскируются (динамический контент), geometry/tone-атрибуты — сравниваются. Базовые экраны: hero-tense, quiet-steady, calendar (3 состояния), navigator, drilldown, sphere-page, unavailable. Baseline утверждается владельцем (визуальный приёмочный прогон).

Transport harness дополнительно проверяет два состояния без API fixture:
initial loading и network error/retry. Они не увеличивают wire-матрицу из 16
payload'ов и не вводят новые calculation states.

Yesterday/check-in имеет отдельные три consumer fixtures: до submit с
`forecastAvailable=true` и скрытым recap; post-submit с recap; submit без
показанного snapshot и без recap. Они не входят в 16 Today payload fixtures.

## 14. Приёмка W7 (gates)

0. **Legacy fixture replacement:** в первом W7 changeset удаляется
   `__tests__/contracts/today-focus-canary-roundtrip.test.tsx` и остальные
   активные V1/V2 Today/Calendar/Yesterday fixtures; Git остаётся архивом,
   каталог `__tests__/legacy/` не создаётся. Удаление выполняется атомарно с
   добавлением новых contract fixtures, чтобы CI не оставался без покрытия.
   Gate:

   ```bash
   rg -n 'DayStatus|TodayFocus|relativeStatus' __tests__ \
     --glob '!**/audit/**'
   # expected after replacement: 0 active legacy matches
   ```

1. Новый frontend импортирует только
   `packages/contracts/today-convergence.ts`; прямые импорты legacy
   `TodayPayload`/`packages/contracts/today.ts` запрещены.
2. Все 16 Today payload fixtures, 2 transport-состояния и 3 Yesterday/check-in
   fixtures рендерятся по test contract §11 (unit + e2e).
3. Pre-submit check-in не рендерит `forecastRecap`; post-submit показывает его
   только при snapshot/impression lineage.
4. axe/контраст AA пройден.
5. Visual baseline утверждён владельцем.
6. Review-gates: «сошлось» только в hero; нет tone-заливки
   тайлов/календаря/recap; нет шаблонных строк; время по таблице §10.
7. AGENTS.md UI-контракт обновлён в том же PR.

## 15. Out of scope

Push-уведомления, paywall-редизайн, экраны horary/natal/synastry, анимационная система сверх §9, тёмная тема (если не была в S3 — отдельное решение).
