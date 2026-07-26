# Дополнение к ТЗ: интерактивная SVG-карта синастрии уровня существующих карт Solar Sage

**Статус:** нормативное дополнение к `00_TZ_REACT_PARITY.md`  
**Приоритет:** P0  
**Зона:** `SynastryWheel`, frontend/API contract, visual/E2E tests

## 1. Главный принцип

Синастрийную карту нельзя делать как новый упрощённый SVG-рисунок. Она должна быть того же визуального и технического класса, что уже существующие интерактивные астрологические карты проекта.

Внутренние source of truth:

- `components/today/day-chart.tsx` — эталон визуального стиля, интерактивности, анимаций, touch hit-area, keyboard accessibility и detail popover;
- `components/readings/natal-chart-wheel.tsx` — эталон астрологической геометрии: зодиакальный круг, дома, углы, реальные longitude, planet glyph и линии аспектов;
- `app/globals.css` — существующие `chart-svg-root`, `data-chart-center`, `chart-fade-in`, `chart-glow`, `prefers-reduced-motion`.

Нельзя сделать статичный круг из нескольких `<circle>` и тонких линий и считать задачу закрытой. Карта должна сразу восприниматься как родной интерактивный chart Solar Sage.

## 2. Что уже хорошо сделано в проекте и должно быть переиспользовано

### 2.1 `DayChart`

В `components/today/day-chart.tsx` уже реализованы:

- fluid SVG с `viewBox`;
- тёплый radial-gradient фон;
- 12 зодиакальных секторов с alternating tint;
- отдельные кольца домов;
- реальные longitude → polar coordinates;
- collision offset для близко стоящих планет;
- индивидуальные цвета и glyph планет;
- кликабельная SVG-group для каждой планеты;
- прозрачная увеличенная hit-area;
- `role="button"`, `tabIndex={0}`, обработка `Enter` и `Space`;
- русский `aria-label`;
- spring-анимация выбранной планеты через `motion.circle`;
- animated detail popover через `AnimatePresence`;
- русская легенда аспектов;
- visual/E2E contract, проверяющий click и содержимое popover.

Это минимальный уровень интерактивности для `SynastryWheel`, а не optional polish.

### 2.2 `NatalChartWheel`

В `components/readings/natal-chart-wheel.tsx` уже реализованы:

- полный зодиакальный круг;
- house cusps и номера домов;
- ASC/MC и другие углы;
- реальные aspect lines между planet points;
- planet glyph и planet colors;
- кликабельные planet nodes;
- прозрачная hit-area;
- selected state;
- синхронный список планет под wheel.

Для синастрии нужно развить эту модель до двух карт, а не заменять её декоративной схемой.

## 3. Композиция `SynastryWheel`

Создать:

`components/synastry/synastry-wheel.tsx`

Карта должна включать:

1. fluid SVG с `viewBox`, `width: 100%`, без canvas и без растровой подложки;
2. внешний зодиакальный ring с 12 секторами и glyph знаков;
3. мягкое чередование фона соседних секторов;
4. концентрические направляющие двух карт;
5. inner planet ring — планеты владельца;
6. outer planet ring — планеты партнёра;
7. planet positions по реальной longitude;
8. collision resolution для близких planet points;
9. aspect lines между конкретными planet IDs;
10. мягкий center glow;
11. центральную подпись `ТЫ + {partnerName}`;
12. компактную русскую legend под картой.

### 3.1 Approximate time

При `precision === "approximate"`:

- planet longitude и доступные межпланетные аспекты остаются;
- не рисовать недостоверные дома партнёра;
- не рисовать недостоверные ASC/MC партнёра;
- не создавать визуально точные house overlays из отсутствующих данных;
- показывать компактную подпись о сниженной точности.

## 4. Визуальный язык

Использовать существующие проектные tokens/patterns:

- `PLANET_SYMBOLS`;
- `PLANET_COLORS`;
- `SIGN_SYMBOLS`;
- `ASPECT_COLOR`;
- `chart-svg-root`;
- center glow через `data-chart-center`;
- reduced-motion правила.

Не создавать отдельную несовместимую палитру только для синастрии.

Требования:

- тёплый молочно-лавандовый radial gradient диска;
- тонкие, но читаемые кольца и spokes;
- planet disk: светлая заливка, цветной stroke, glyph поверх;
- базовые aspect lines спокойные;
- выбранная линия ярче и толще;
- несвязанные линии dim;
- tense/supportive/mixed различаются цветом и при необходимости opacity/dash pattern;
- анимации не должны работать принудительно при `prefers-reduced-motion: reduce`.

## 5. Интерактивность планет

Каждая планета — интерактивная SVG-group.

Обязательно:

- видимый planet disk радиусом примерно 9–11;
- прозрачная hit-area минимум `r=13–16`;
- click/tap выбирает планету;
- повторный click снимает выбор;
- `role="button"`;
- `tabIndex={0}`;
- `Enter` и `Space` активируют планету;
- русский `aria-label`, например:
  - `Твой Марс в Овне`;
  - `Марс партнёра в Овне, 5 дом`;
- selected planet увеличивается spring-анимацией;
- selected planet получает более толстый stroke;
- при выборе подсвечиваются все связанные аспекты;
- несвязанные линии приглушаются;
- под wheel появляется animated detail popover.

### 5.1 Planet popover

Popover должен содержать:

- glyph;
- `Твоя/Его/Её {планета}`;
- знак;
- дом, когда он достоверен;
- отметку approximate, когда нужно;
- короткий человеческий смысл этой планеты именно в отношениях пары.

Popover делать через `AnimatePresence`/`motion`, аналогично `DayChart`, а не браузерный `title` tooltip.

## 6. Интерактивность аспектов

Каждая aspect line обязана быть связана с реальным `aspectId`.

### 6.1 Touch hit-area

Тонкая видимая линия сама по себе непригодна для телефона.

Для каждого аспекта рисовать:

1. видимую line с нужным stroke;
2. поверх/под ней прозрачную line с увеличенным `strokeWidth`, которая принимает pointer events.

Пользователь должен уверенно попадать по линии пальцем.

### 6.2 Selection behavior

Click по aspect line:

- выбирает аспект;
- делает его линию ярче/толще;
- dim остальные линии;
- выделяет обе planet nodes;
- синхронно активирует соответствующую aspect card;
- не обязан немедленно открывать sheet, чтобы пользователь мог рассмотреть карту.

Click по aspect card:

- выбирает соответствующую линию;
- затем открывает `AspectDrilldownSheet`;
- передаёт реальный `aspectId`, не `techSignature`.

После закрытия sheet выбранный аспект остаётся подсвеченным.

### 6.3 Accessibility

Интерактивная aspect group должна иметь:

- `role="button"`;
- keyboard activation;
- русское `aria-label`, например:

`Твой Меркурий — квадрат — Меркурий партнёра, орб 1 градус 5 минут, напряжённый аспект`.

## 7. Единое состояние wheel и списка

Нельзя держать отдельный selected-state внутри SVG и другой selected-state внутри карточек.

Использовать общий controlled state:

```ts
interface SynastryWheelSelection {
  selectedPlanetId: string | null
  selectedAspectId: string | null
}
```

Рекомендуемый API:

```tsx
<SynastryWheel
  ownerPlanets={report.ownerPlanets}
  partnerPlanets={report.partnerPlanets}
  aspects={report.aspects}
  precision={report.precision}
  selection={selection}
  onPlanetSelect={handlePlanetSelect}
  onAspectSelect={handleAspectSelect}
  onAspectOpen={handleAspectOpen}
/>
```

## 8. Data contract

Frontend/API должны получать реальные данные для геометрии:

```ts
interface SynastryPlanetPoint {
  id: string
  owner: "user" | "partner"
  planet: PlanetCode
  glyph: string
  longitude: number
  sign: SignCode
  house: number | null
  houseReliable: boolean
}

interface SynastryAspectItem {
  id: string
  ownerPlanetId: string
  partnerPlanetId: string
  aspectType: AspectType
  aspectSymbol: string
  orbDegrees: number
  orbLabel: string
  tone: "good" | "mid" | "bad"
  title: string
  short: string
  techSignature: string
}
```

Запрещено:

- ставить planet points по индексу массива;
- угадывать longitude на frontend;
- связывать line с планетой по отображаемому имени;
- передавать `techSignature` вместо `aspectId`;
- рисовать дома/углы, надёжность которых backend не подтвердил.

Если текущий API не отдаёт longitude и стабильные planet IDs, сначала расширить schema/API, затем верстать wheel.

## 9. Переиспользование кода

Не копировать целиком `DayChart` или `NatalChartWheel` в третий файл.

Перед реализацией выделить общие primitives/utilities там, где это безопасно:

- `lib/astro/chart-geometry.ts`:
  - longitude → angle;
  - polar coordinates;
  - arc helpers;
  - collision offsets;
- `components/astro/astro-chart-tokens.ts`:
  - planet glyph;
  - sign glyph;
  - planet colors;
  - aspect colors;
- при необходимости `components/astro/interactive-planet-node.tsx`;
- при необходимости `components/astro/astro-chart-legend.tsx`.

Большая миграция уже работающих карт не обязательна, но новая карта обязана использовать их proven patterns.

## 10. Обязательные тесты

Добавить E2E/visual tests по образцу `e2e/mock-visual/day.spec.ts`.

Проверить:

1. wheel содержит responsive SVG `viewBox`;
2. количество planet nodes соответствует payload;
3. planet nodes имеют русские `aria-label`;
4. planet nodes доступны через keyboard;
5. click по планете открывает popover;
6. click по планете подсвечивает связанные lines;
7. click по transparent aspect hit-line выбирает аспект;
8. соответствующая aspect card получает active-state;
9. click по card открывает drill-down с правильным `aspectId`;
10. закрытие sheet сохраняет selected line;
11. approximate payload скрывает недостоверные дома/ASC;
12. fixture с близкими longitude не создаёт наложение glyph;
13. `prefers-reduced-motion: reduce` отключает необязательную motion-анимацию;
14. в пользовательском SVG/popover нет English planet/sign labels.

Visual snapshots:

- good report default;
- bad report default;
- selected planet;
- selected aspect;
- approximate time;
- width 320 px;
- width 390 px.

## 11. Definition of Done

SVG-карта считается принятой, когда:

- визуально выглядит частью той же системы, что `DayChart` и `NatalChartWheel`;
- использует реальные longitude;
- содержит два различимых planet rings;
- planet nodes кликабельны и удобны на touch;
- есть keyboard/aria contract;
- selected planet имеет анимацию и popover;
- selected aspect синхронизирован с карточкой;
- по тонкой линии реально можно попасть пальцем через transparent hit-line;
- aspect card открывает drill-down по реальному `aspectId`;
- approximate time не создаёт ложной точности;
- visual snapshots приняты владельцем продукта;
- не появилась третья отдельная система glyph, цветов и chart geometry.
