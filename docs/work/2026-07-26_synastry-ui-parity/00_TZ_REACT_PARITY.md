# ТЗ: доведение React-интерфейса «Синастрия / Совместимость» до HTML-макета

**Дата:** 2026-07-26  
**Статус:** ready for implementation  
**Приоритет:** P1 — визуальная и продуктовая целостность уже работающей функции  
**Зона:** frontend React + минимальные расширения API-контракта, необходимые для визуализации карты  

---

## 1. Цель работы

Текущая React-версия технически отображает список партнёров, отчёт, аспекты, наложения домов, сферы и feedback, но визуально и композиционно почти не повторяет согласованный HTML-прототип.

Нужно не «слегка улучшить стили», а восстановить продуктовую логику макета:

1. Список должен быстро отвечать на вопрос **«кто мне подходит и насколько»**.
2. Детальный экран должен начинаться с эмоционального вывода и визуального баланса пары.
3. Астрологический слой должен быть **видимым**, а не превращаться в обычный список карточек.
4. Пользователь должен сразу видеть, где поддержка, где неоднозначность, где напряжение.
5. Технический фактор должен связываться с человеческим переводом и жизненным примером.
6. Вся страница должна выглядеть как один цельный mobile-first продукт Solar Sage, а не как набор универсальных Tailwind-карточек.

---

## 2. Источник истины

### Визуальный reference

Использовать HTML-прототип как главный visual source of truth:

- ветка: `prototype/synastry-html`
- entry point: `public/prototypes/synastry/index.html`
- основной макет: `public/prototypes/synastry/base.html`
- aspect drill-down: `public/prototypes/synastry/aspect-drilldown.css` и `aspect-drilldown.js`
- отсутствие точного времени: `public/prototypes/synastry/partner-time.css` и `partner-time.js`
- PR: `#11 Prototype: synastry UX with aspect drill-downs`

HTML не нужно переносить буквально. Нужно воспроизвести его:

- композицию;
- визуальную иерархию;
- плотность;
- размеры;
- цветовую драматургию;
- тексты и логику раскрытия;
- mobile-first поведение.

### Текущие React-компоненты

Основные точки доработки:

- `app/(grace)/synastry/page.tsx`
- `components/synastry/synastry-screen.tsx`
- `components/synastry/synastry-detail-screen.tsx`
- `components/synastry/synastry-add-sheet.tsx`
- `components/synastry/aspect-drilldown-sheet.tsx`
- `lib/api/synastry.ts`
- при необходимости `apps/api/app/schemas/synastry.py`
- визуальные тесты `e2e/mock-visual/synastry.spec.ts`

---

## 3. Главные расхождения текущей React-версии

### 3.1. Потерян hero списка

Сейчас экран начинается с маленького заголовка `Вместе` и текста `Совместимость и гармония натальных карт`.

В макете экран должен открываться крупным эмоциональным сообщением:

- eyebrow: `Синастрия`
- H1: `Кто тебе подходит?`
- пояснение: `Сначала — понятный вывод. Внутри каждого сравнения — полное астрологическое «мясо»: аспекты, орбисы, наложение домов и человеческий перевод.`
- большая CTA на всю ширину: `＋ Добавить человека`

Текущий компактный header выглядит как служебная страница. Нужен самостоятельный продуктовый hero.

### 3.2. Карточки списка слишком общие

Сейчас карточка показывает имя, тип отношений, summary и балл. Она почти не передаёт распределение хороших и напряжённых факторов.

В макете карточка должна дополнительно показывать:

- статус `Хорошо подходит / Нормально / Сложно`;
- короткий вывод в 1–2 строки;
- три компактных индикатора:
  - `N поддерживают`;
  - `N неоднозначны`;
  - `N напрягают`;
- отметку точности времени рождения;
- более заметный score;
- для лучшего кандидата — аккуратный ribbon `Лучшее совпадение` или аналогичный label.

### 3.3. Нет визуальной карты взаимодействия

В `synastry-detail-screen.tsx` секция с комментарием `WHEEL & ASPECTS` фактически выводит только список аспектов.

Необходимо вернуть главный визуальный элемент макета:

- два кольца планет;
- внутреннее кольцо пользователя;
- внешнее кольцо партнёра;
- линии аспектов;
- цвет линии по tone;
- интерактивная подсветка линии по нажатию;
- связь выбранной линии с карточкой аспекта.

Без этой карты интерфейс теряет главный визуальный смысл синастрии.

### 3.4. Детальный экран выглядит как ряд одинаковых белых блоков

Сейчас почти все разделы имеют одинаковую конструкцию `rounded-3xl border bg-card p-6 shadow-sm`.

В макете у блоков разные функции и разная подача:

- hero пары — без тяжёлой рамки, с центрированной композицией;
- score — отдельная крупная карточка;
- wheel — цветная светлая поверхность внутри карточки;
- аспекты — интерактивные строки;
- наложения домов — лавандовые мини-карточки;
- человеческий перевод — белые карточки с цветной точкой и отдельной сценой;
- сферы — accordion;
- reality check — спокойный завершающий блок.

Нужно убрать ощущение «один компонент Card размножили семь раз».

### 3.5. Drill-down аспекта слишком короткий

Текущий `AspectDrilldownData` содержит только:

- explanation;
- один scenario;
- один advice.

Согласованный макет требует:

- что означает первая планета;
- что означает вторая планета;
- что делает конкретный тип аспекта;
- 3–4 жизненных сценария;
- несколько repair-действий;
- блок `Это не означает`.

Особенно важен пример `Меркурий □ Меркурий`.

### 3.6. Есть ошибка маршрутизации в drill-down из human translation

В `synastry-detail-screen.tsx` кнопка `Что значит?` передаёт `item.tech` в `handleOpenAspectDrilldown`, хотя endpoint ожидает `aspectId`.

Нужно передавать стабильный `aspectId`, связанный с translation, а техническую подпись использовать только для отображения.

### 3.7. Tone vocabulary не нормализован на frontend

Backend может отдавать:

- `good / mid / bad`;
- `supportive / mixed / tense`;
- исторически также `harmony / tension / neutral`.

Frontend должен иметь единую функцию нормализации:

```ts
normalizeSynastryTone(tone) => "good" | "mid" | "bad"
```

Все цвета, классы, счётчики и состояния должны работать через неё.

---

## 4. Общая визуальная система

### 4.1. Палитра

Использовать существующие глобальные токены Solar Sage, но для синастрии привести их к макету:

```text
background: #fbf8f2
card:       #fffdf9
ink:        #3e3347
muted:      #7d7284
line:       #e8e0e8
primary:    #795a86
lavender:   #f1e9f4
good:       #43806d
good-bg:    #eaf5f0
mid:        #b07b36
mid-bg:     #fbf1de
bad:        #a64d59
bad-bg:     #fae9ec
```

Не использовать яркий зелёный Tailwind emerald и стандартный destructive red как основные цвета синастрии. Цвета должны быть приглушёнными, тёплыми и согласованными с HTML.

Создать локальные CSS variables или semantic utility classes:

```css
--syn-good
--syn-good-bg
--syn-mid
--syn-mid-bg
--syn-bad
--syn-bad-bg
```

### 4.2. Фон

Экран должен иметь тёплый молочный фон и два очень мягких radial-gradient пятна:

- лавандовое справа сверху;
- персиковое слева в верхней трети.

Градиенты не должны мешать чтению и не должны выглядеть как яркий космос.

### 4.3. Шрифты

В проекте уже подключены:

- Inter;
- Instrument Serif;
- Lora с кириллицей.

Использовать:

- display-заголовки: `font-serif`, weight 400–500;
- интерфейсный текст: Inter;
- не ставить `font-bold` на крупные serif-заголовки;
- кириллица должна визуально идти через Lora.

Основные размеры:

```text
List H1:             38–40 px, line-height 0.98–1.04, weight 400–500
Detail pair title:   32–34 px, line-height 1.05
Section H2:          20–22 px
Card title:          15–18 px
Body:                13–15 px
Eyebrow:             10–11 px, uppercase, tracking 0.10–0.14em
Metadata:            11–12 px
Score list:          28–30 px serif
Score detail:        34–42 px serif
```

### 4.4. Радиусы и тени

```text
Main cards:          22–26 px
Small nested cards:  14–18 px
Inputs:              14–17 px
Avatar:              16–18 px, не обязательно круг
CTA:                 16–18 px
```

Тени мягкие, широкие, почти незаметные. Не использовать стандартный `shadow-sm` везде одинаково.

### 4.5. Контейнер

AppShell уже ограничивает приложение `max-w-md`. Внутри `/synastry`:

- убрать лишний `max-w-xl`;
- убрать одинаковый `p-4` вокруг всего экрана;
- позволить hero и topbar иметь собственные отступы;
- стандартная горизонтальная зона контента: 18 px;
- нижний отступ должен учитывать TabBar и safe area.

---

## 5. Экран списка партнёров

### 5.1. Структура сверху вниз

1. Product hero.
2. Большая CTA.
3. Search.
4. Filters.
5. Заголовок списка и количество.
6. Карточки.
7. Empty/loading/error states.

### 5.2. Hero

Заменить текущую строку `Вместе + маленькая кнопка справа`.

Точный рекомендуемый copy:

```text
СИНАСТРИЯ
Кто тебе
подходит?

Сначала — понятный вывод. Внутри каждого сравнения — полное астрологическое «мясо»: аспекты, орбисы, наложение домов и человеческий перевод.
```

CTA:

```text
＋ Добавить человека
```

CTA на всю ширину, высота 50–54 px.

### 5.3. Поиск

- высота 48 px;
- radius 17 px;
- icon 20 px;
- placeholder `Найти по имени`;
- фон белый с небольшой прозрачностью;
- focus ring лавандовый, а не ярко-фиолетовый.

### 5.4. Фильтры

Оставить:

- `Все`;
- `Хорошо подходит`;
- `Нормально`;
- `Сложно`.

Активный фильтр в макете — тёмный `ink`, а не primary plum.

- горизонтальный scroll;
- без scrollbar;
- размер текста 12 px;
- высота около 34 px.

### 5.5. Заголовок списка

```text
Твои сравнения                         4 человека
```

- H2 20 px;
- счётчик 12 px muted.

### 5.6. Карточка партнёра

Карточка должна быть `button` на всю ширину, но delete action нельзя оставлять вложенным `role=button` внутри button.

Исправить семантику одним из способов:

- внешний контейнер `article/div`, внутри отдельная кнопка открытия и отдельная кнопка удаления;
- либо удаление вынести в context menu/swipe/action sheet.

Состав карточки:

#### Верхняя строка

- avatar 46×46, rounded 17 px;
- имя 18 px, Inter semibold/bold или Lora 18 px;
- relation/дата/точность 11–12 px;
- score справа 29 px serif;
- подпись `/100` или `из 100` очень мелко.

#### Status pill

Использовать человеческие названия:

- `Хорошо подходит`;
- `Нормально`;
- `Сложно`.

Не использовать на списке:

- `Отличная связь`;
- `Нормальный потенциал`;
- `Высокое трение`.

#### Summary

- 1–2 строки;
- размер 14 px;
- текст должен описывать конкретную динамику, а не `Отличная совместимость натальных карт`.

#### Баланс аспектов

Три равных мини-блока:

```text
8 поддерживают | 2 неоднозначны | 2 напрягают
```

Цветные фоны по tone.

#### Precision

Если `precision === approximate`, показывать ненавязчивую строку:

```text
Время рождения неизвестно · расчёт без домов партнёра
```

Не прятать точность только внутри detail.

### 5.7. Лучшее совпадение

На карточке с максимальным score среди готовых отчётов показывать маленький ribbon:

```text
ЛУЧШЕЕ СОВПАДЕНИЕ
```

Не показывать ribbon, если:

- отчёт ещё считается;
- в списке один человек;
- score отсутствует.

### 5.8. Pending state карточки

Вместо просто `Считаем…`:

- оставить карточку партнёра;
- score заменить компактным loader;
- показать stage из generation status;
- copy: `Собираем аспекты` / `Готовим человеческий перевод`;
- карточка не должна выглядеть сломанной.

---

## 6. Детальный экран пары

### 6.1. Topbar

В макете:

- слева квадратная icon button `‹`;
- по центру `Совместимость`;
- справа share icon, пока disabled/future.

Не использовать текстовую pill-кнопку `Назад` — она утяжеляет header.

Topbar должен иметь высоту около 58 px и быть визуально отделён от hero только воздухом.

### 6.2. Hero пары

Hero не должен быть белой карточкой с рамкой.

Структура:

1. два overlapping avatar;
2. eyebrow relation type;
3. H1 `Ты + Максим`;
4. метаданные рождения обоих;
5. precision badge, если время приблизительное.

Пример:

```text
РОМАНТИЧЕСКИЕ ОТНОШЕНИЯ
Ты + Максим
14 мая 1981 · 9 сентября 1987 · 08:15 · Москва
```

Для approximate:

```text
Примерный расчёт · без ASC и домов партнёра
```

### 6.3. Score panel

Отдельная большая карточка:

- слева score в лавандовом квадрате 78×78;
- справа verdict и summary;
- снизу три цветных блока counters.

Не размещать score, статус и counters в одну горизонтальную строку, которая сжимается на мобильном.

Рекомендуемый состав:

```text
89     Хорошо подходит
       Много естественной поддержки: легко разговаривать,
       сближаться и действовать вместе. Главное напряжение — темп и контроль.

8 поддерживают | 2 неоднозначны | 2 напрягают
```

### 6.4. Использовать hero narrative из API

Сейчас schema содержит `heroTitle` и `heroDescription`, но React их не использует.

Правило:

- `verdict` — status headline рядом со score;
- `summary` — executive summary;
- `heroTitle` — более эмоциональный заголовок пары, если заполнен;
- `heroDescription` — дополнительное описание, если оно не дублирует summary.

Не выводить три одинаковых абзаца подряд. Нужен fallback chain и дедупликация.

---

## 7. Карта взаимодействия: обязательный блок

### 7.1. Внешний вид

Внутри карточки:

- eyebrow `Карта взаимодействия`;
- H2 `Где между вами ток`;
- пояснение про линии;
- светлая gradient surface;
- SVG 320–340 px шириной;
- legend;
- список ключевых аспектов.

### 7.2. Два кольца

SVG должен рисовать:

- внешний круг партнёра;
- внутренний круг пользователя;
- центральный круг с `ТЫ + ИМЯ`;
- planet points с glyph;
- aspect lines.

### 7.3. Данные для реальной карты

Текущий frontend contract не содержит координаты планет. Для честной визуализации расширить API.

Рекомендуемый контракт:

```ts
type SynastryPlanetPoint = {
  key: string
  label: string
  glyph: string
  longitude: number
  sign?: string | null
  degreeText?: string | null
}

type SynastryAspectItem = {
  id: string
  ownerPlanetKey: string
  partnerPlanetKey: string
  aspectType: "conjunction" | "trine" | "sextile" | "square" | "opposition" | "quincunx" | string
  aspectSymbol: string
  orbText: string | null
  title: string
  techSignature: string | null
  tone: SynastryTone
  description: string | null
}

type SynastryReportData = {
  ownerPlanets: SynastryPlanetPoint[]
  partnerPlanets: SynastryPlanetPoint[]
  aspects: SynastryAspectItem[]
}
```

Позицию точки на кольце рассчитывать по `longitude`.

Не использовать случайные позиции.

Допустимый временный fallback на этапе frontend parity:

- если координаты не пришли, расположить планеты детерминированно;
- обязательно пометить development-only fallback;
- не оставлять fallback как production final.

### 7.4. Цвета линий

- good/supportive/harmony → green;
- mid/mixed/neutral → amber;
- bad/tense/tension → muted red.

Default opacity около 0.55–0.65.

При выборе аспекта:

- выбранная линия opacity 1, stroke-width 4;
- остальные opacity 0.08–0.12;
- соответствующая карточка получает border highlight;
- если карточка скрыта под `Показать все`, раскрыть список.

### 7.5. Click area

SVG line сама по себе слишком тонкая для пальца.

Рисовать поверх каждой линии прозрачный hit target stroke 12–16 px.

### 7.6. Legend

```text
● поддержка   ● неоднозначно   ● напряжение
```

Размер 10–11 px, центрировано.

---

## 8. Список аспектов под картой

### 8.1. Карточка аспекта

Каждый aspect row:

- цветной square с символом;
- техническая строка;
- orb;
- человеческий short title;
- hint `Нажми — подробное значение и примеры`.

Пример:

```text
□  Меркурий квадрат Меркурий        орб 1°05′
   Смысл теряется в форме
   Нажми — подробное значение и примеры
```

### 8.2. Терминология

В заголовке использовать локализованные названия:

- соединение;
- тригон;
- секстиль;
- квадрат;
- оппозиция;
- квиконс.

Не показывать пользователю `sun_trine_moon`.

### 8.3. Key vs all

- первые 3 — наиболее значимые, не просто первые из API;
- backend или frontend должны сортировать по impact/score/orb;
- кнопка `Показать все аспекты ↓`;
- при раскрытии текст меняется на `Скрыть второстепенные аспекты ↑`.

---

## 9. Наложение домов

### 9.1. Заголовок и copy

```text
НАЛОЖЕНИЕ ДОМОВ
Что у кого включается

Не просто «планета в доме», а какую часть жизни партнёр реально задевает.
```

### 9.2. Карточка overlay

- lavender surface;
- tech 11 px plum semibold;
- human text 12–13 px;
- radius 17 px;
- без тяжёлой рамки.

Пример:

```text
Его Венера → твой 7 дом
Он быстро воспринимается как подходящий партнёр: хочется договариваться и быть парой.
```

### 9.3. Approximate state

Если время неизвестно:

- не показывать пустой или «рассчитывается» блок;
- показать специальную карточку:

```text
Дома партнёра не рассчитаны
Без точного времени рождения нельзя честно определить ASC и домовые наложения. Планетарные аспекты в отчёте сохранены.
```

---

## 10. Человеческий перевод

### 10.1. Заголовок

```text
ЧЕЛОВЕЧЕСКИЙ ПЕРЕВОД
Что это делает с вами

Астрологическая причина → узнаваемое поведение → конкретная сцена. Никакой простыни.
```

### 10.2. Карточка translation

Состав:

- tone dot;
- H3;
- кликабельная tech signature справа;
- основной текст;
- scene в отдельной мягкой подложке.

Не выводить scene italic-цитатой через border-top. В макете это отдельный компактный блок.

Пример:

```text
● Вы слышите не те слова        Меркурий □ Меркурий · что значит?

Разница в сборке фразы и в том, что каждый считает очевидным.

[ Переписка превращает нейтральную фразу в претензию. ]
```

### 10.3. Связь с aspect ID

Расширить translation contract:

```ts
type SynastryTranslation = {
  tone: SynastryTone
  title: string
  aspectId: string | null
  tech: string | null
  text: string | null
  scene: string | null
}
```

Кнопка открывает drill-down по `aspectId`.

Если `aspectId` отсутствует:

- не показывать кнопку;
- не пытаться отправлять `tech` как ID.

---

## 11. Сферы отношений

### 11.1. Заголовок

```text
ПО ЖИЗНИ
Где легко, где придётся работать
```

### 11.2. Accordion

Каждая строка:

- tone dot;
- title;
- крупный score справа serif;
- chevron;
- при раскрытии human description.

Score не оформлять маленьким primary pill `84 / 100`. В макете число выступает отдельным визуальным элементом.

### 11.3. Порядок

Для romantic:

1. Близость;
2. Общение;
3. Быт;
4. Дела и деньги;
5. Поездки — если backend отдаёт.

Для business первым может идти `Дела и деньги`, но порядок должен приходить из backend или relation-specific config, а не случайно.

### 11.4. Initial open state

Первая сфера должна быть открыта по умолчанию после загрузки отчёта.

Сейчас `openSpheres` инициализирован пустым объектом — исправить.

---

## 12. Aspect drill-down sheet

### 12.1. Формат

Bottom sheet на мобильном:

- max-height 90dvh;
- rounded top 28 px;
- grabber сверху;
- scroll внутри sheet;
- background не чисто белый, а app background;
- close icon;
- CTA `Понятно` снизу.

### 12.2. Содержание

Обязательные секции:

1. Hero аспекта.
2. `Что именно соединяется`.
3. `Как работает квадрат/тригон/...`.
4. `Как это проявляется в жизни`.
5. `Что помогает`.
6. `Важно: это не означает`.

### 12.3. Hero

Пример:

```text
АСТРОЛОГИЧЕСКИЙ КОНТАКТ
Меркурий □ Меркурий

□  Два разных способа собирать смысл
Квадрат · орб 1°05′ · напряжённый контакт
```

### 12.4. Планеты

Показать две соседние карточки:

```text
ТВОЯ КАРТА
☿ Меркурий
Мышление, речь, логика, вопросы и способ понимать смысл.

КАРТА ПАРТНЁРА · КИРИЛЛ
☿ Меркурий
Мышление, речь, логика, вопросы и способ понимать смысл.
```

Для разных планет тексты должны быть разными.

### 12.5. Жизненные сцены

API должен отдавать массив, а не одну строку:

```ts
scenes: Array<{
  title: string
  text: string
}>
```

Для `Меркурий □ Меркурий` минимум:

- `В переписке`;
- `Когда строите планы`;
- `В споре`;
- `После разговора`.

### 12.6. Repair actions

API должен отдавать массив:

```ts
repairs: string[]
```

Показывать numbered cards 1, 2, 3…

Для напряжённого Меркурия обязательны:

- назвать цель разговора;
- пересказать услышанное;
- не решать чувствительные темы короткими сообщениями;
- обсуждать один вопрос за раз;
- взять паузу и вернуться с конкретной просьбой.

### 12.7. Not means

API или frontend fallback:

```ts
notMeans: string[]
```

Пример:

- `не значит, что кто-то глупее`;
- `не доказывает ложь или манипуляцию`;
- `не запрещает научиться слышать друг друга`.

### 12.8. Новый контракт drill-down

```ts
type AspectDrilldownData = {
  aspectId: string
  title: string
  tone: SynastryTone
  techSignature: string | null
  aspectSymbol: string | null
  aspectKindLabel: string | null
  orbText: string | null
  headline: string
  ownerPlanet: {
    key: string
    label: string
    glyph: string
    meaning: string
  }
  partnerPlanet: {
    key: string
    label: string
    glyph: string
    meaning: string
  }
  explanation: string
  scenes: Array<{ title: string; text: string }>
  repairs: string[]
  notMeans: string[]
}
```

Старые `scenario` и `advice` можно временно поддерживать как fallback, но UI должен работать с новым массивным contract.

---

## 13. Форма добавления партнёра

Текущая функциональность unknown time уже близка к требованиям. Нужно довести визуально.

### 13.1. Header

```text
НОВОЕ СРАВНЕНИЕ
Добавить человека
```

Не использовать Sparkles icon внутри H2 как главный визуальный акцент.

### 13.2. Поля

Порядок:

1. Имя.
2. Тип связи.
3. Дата рождения.
4. Время рождения.
5. Switch `Точное время неизвестно`.
6. Precision notice.
7. Город рождения.
8. CTA.

### 13.3. Sheet height

На малых iPhone sheet может не помещаться. Добавить:

- `max-height: 92dvh`;
- внутренний scroll;
- safe-area bottom padding;
- sticky или просто всегда доступную CTA внизу после scroll.

### 13.4. Unknown time

Сохранить текущую логику:

- время очищается;
- поле disabled;
- сохранённое время восстанавливается;
- payload `birthTimePrecision: approximate`;
- notice видим.

Copy в notice:

```text
Примерный расчёт: без ASC и домов партнёра
Планеты и основные аспекты останутся. Дома и Асцендент партнёра не рассчитываются, а положение Луны и общий балл будут менее точными.
```

### 13.5. CTA

```text
Построить синастрию
```

Loading:

```text
Сохраняем данные…
```

После success переходить не сразу в пустой detail, а в processing state.

---

## 14. Loading, generation и error states

### 14.1. Не использовать голый spinner как единственный loading

Для detail во время генерации показать спокойный staged loader:

```text
Строим карту взаимодействия

✓ Сопоставили планеты
• Рассчитываем аспекты
• Готовим человеческий перевод
```

Stage брать из `SynastryGenerationStatus.stage/state`.

### 14.2. Polling

После создания партнёра:

- открыть processing screen;
- poll `/api/synastry/{partner_id}/status`;
- при `ready` загрузить report;
- при `failed` показать retry/error;
- остановить polling при unmount.

### 14.3. Error copy

Не оставлять английские ошибки вроде `Failed to load aspect drilldown`.

Все пользовательские fallback-сообщения — на русском.

### 14.4. Empty state

Различать:

- список действительно пуст;
- фильтр/поиск не нашёл совпадений.

Для пустого аккаунта:

```text
Добавь первого человека
Сравним ваши карты и покажем не только общий балл, но и конкретные точки притяжения и трения.
```

Для search empty:

```text
По этому имени никого нет
Сбросить поиск
```

---

## 15. Тексты и content contract

### 15.1. Общие правила

- технический фактор всегда виден;
- рядом всегда есть человеческий перевод;
- один card — одна мысль;
- напряжение всегда содержит repair;
- никаких абсолютов `обречены`, `идеальная пара`, `никогда`;
- не оценивать интеллект по Меркурию;
- не приписывать умысел;
- unknown time явно снижает confidence.

### 15.2. Ограничения длины

```text
Verdict:              до 42 символов
Summary list card:    до 150 символов
Summary detail:       до 260 символов
Aspect short title:   до 54 символов
Translation title:    до 42 символов
Translation text:     до 220 символов
Scene:                до 180 символов
Sphere description:   до 320 символов
```

Frontend должен корректно работать с более длинным текстом, но backend/LLM prompt должен целиться в эти лимиты.

### 15.3. Негативный пример

В mock/fixture обязательно оставить сценарий, где почти всё плохо:

- score около 20–30;
- 1 good;
- 2 mid;
- 8–10 bad;
- красная карта;
- честный verdict;
- плохие показатели общения, быта и денег.

Нельзя тестировать интерфейс только на красивой зелёной паре.

---

## 16. Компонентная декомпозиция

Рекомендуемая структура:

```text
components/synastry/
  synastry-screen.tsx
  synastry-list-hero.tsx
  synastry-search-filters.tsx
  synastry-partner-card.tsx
  synastry-detail-screen.tsx
  synastry-pair-hero.tsx
  synastry-score-panel.tsx
  synastry-wheel.tsx
  synastry-aspect-row.tsx
  synastry-house-overlays.tsx
  synastry-translations.tsx
  synastry-spheres.tsx
  synastry-feedback.tsx
  synastry-add-sheet.tsx
  aspect-drilldown-sheet.tsx
  synastry-tone.ts
```

Не обязательно создавать ровно все файлы, но `synastry-detail-screen.tsx` не должен оставаться монолитом на 400+ строк.

### Tone helper

```ts
export type NormalizedSynastryTone = "good" | "mid" | "bad"

export function normalizeSynastryTone(value: string | null | undefined): NormalizedSynastryTone {
  if (["good", "supportive", "harmony"].includes(value || "")) return "good"
  if (["bad", "tense", "tension"].includes(value || "")) return "bad"
  return "mid"
}
```

---

## 17. Accessibility и interaction

Обязательно:

- нет вложенных interactive elements;
- все icon buttons имеют `aria-label`;
- bottom sheets закрываются по Escape;
- overlay click закрывает sheet;
- focus trap в modal/sheet;
- после закрытия focus возвращается на trigger;
- SVG aspect lines доступны через список аспектов;
- minimum touch target 44×44 px;
- `prefers-reduced-motion` отключает nonessential transitions;
- colors не являются единственным носителем смысла — всегда есть text label/symbol.

---

## 18. Анимации

Использовать умеренно:

- screen enter 180–240 ms;
- card active scale 0.99;
- selected aspect line 180 ms;
- sheet 220–280 ms;
- accordion 180–220 ms;
- score и counters не анимировать бесконечно.

Не добавлять:

- яркие звёздные particle effects;
- постоянные glow animation;
- bounce;
- тяжёлый parallax.

---

## 19. Responsive

Основная цель — Telegram Mini App 360–430 px.

Проверить минимум:

- 360×780;
- 375×812;
- 390×844;
- 430×932;
- desktop preview 768+.

На desktop:

- ширина приложения остаётся около 480–520 px;
- sheet можно центрировать как modal;
- не растягивать контент на всю ширину.

---

## 20. Тесты

### 20.1. Unit/component

Обновить/добавить:

- `synastry-screen.test.tsx`;
- `synastry-detail-screen.test.tsx`;
- `synastry-add-sheet.test.tsx`;
- `aspect-drilldown-sheet.test.tsx`;
- `synastry-tone.test.ts`.

Проверки:

- tone normalization;
- exact/approximate;
- filter/search;
- best match ribbon;
- card counters;
- selected aspect;
- show all;
- translation opens correct aspect ID;
- first sphere open;
- unknown time payload;
- processing state;
- error states.

### 20.2. Visual regression

Текущий visual test маскирует всю карточку партнёра. Это делает тест почти бесполезным для parity.

Новые screenshots без маскирования главного UI:

```text
synastry-list-good.png
synastry-list-mixed.png
synastry-list-bad.png
synastry-detail-good.png
synastry-detail-bad.png
synastry-detail-approximate.png
synastry-aspect-selected.png
synastry-aspect-drilldown.png
synastry-add-exact.png
synastry-add-approximate.png
synastry-processing.png
```

Маскировать только реально динамические данные, а не целые карточки.

### 20.3. E2E interaction

Сценарий:

1. открыть `/synastry`;
2. найти Кирилла;
3. открыть detail;
4. нажать `Меркурий □ Меркурий`;
5. проверить подсветку линии;
6. проверить sheet;
7. увидеть 4 жизненные сцены;
8. закрыть;
9. отправить feedback;
10. вернуться в список.

Отдельный сценарий:

1. добавить партнёра;
2. включить unknown time;
3. проверить disabled time;
4. submit;
5. увидеть processing;
6. получить approximate report;
7. не увидеть домовые наложения партнёра.

---

## 21. Критерии приёмки

Работа принимается только если выполнено всё ниже.

### Список

- [ ] Hero визуально соответствует HTML-макету.
- [ ] CTA занимает всю ширину.
- [ ] Search и filters соответствуют размерам и цветам макета.
- [ ] Карточки содержат score, status, summary, counters и precision.
- [ ] Есть негативная карточка с очевидно красным балансом.
- [ ] Нет вложенного button/role=button.

### Detail

- [ ] Pair hero не оформлен как обычная белая карточка.
- [ ] Score panel повторяет композицию макета.
- [ ] Реально отображается двухкольцевая SVG-карта.
- [ ] Линии аспектов интерактивны.
- [ ] Выбор в списке подсвечивает линию и наоборот.
- [ ] Есть legend.
- [ ] House overlays оформлены как отдельные lavender cards.
- [ ] Translations имеют tone dot, tech link и scene surface.
- [ ] Первая sphere открыта.
- [ ] Feedback визуально соответствует макету.

### Drill-down

- [ ] Открывается по реальному aspectId.
- [ ] Есть две planet cards.
- [ ] Есть explanation механики аспекта.
- [ ] Есть массив жизненных примеров.
- [ ] Есть массив repair actions.
- [ ] Есть `Это не означает`.
- [ ] `Меркурий □ Меркурий` содержит конкретные примеры переписки, планов и спора.

### Approximate

- [ ] Switch работает.
- [ ] Время блокируется и восстанавливается.
- [ ] API получает approximate.
- [ ] В списке и detail виден precision status.
- [ ] Дома партнёра не выдумываются.

### Quality

- [ ] `pnpm typecheck` проходит.
- [ ] `pnpm lint` проходит.
- [ ] unit tests проходят.
- [ ] Playwright interaction tests проходят.
- [ ] visual snapshots добавлены и просмотрены человеком.
- [ ] На 390×844 интерфейс визуально близок к HTML reference, а не только структурно похож.

---

## 22. Рекомендуемый порядок реализации

### Этап 1. Основа и список

- tone normalization;
- page spacing/background;
- hero;
- partner card;
- filters/search;
- exact/approximate states.

### Этап 2. Detail composition

- pair hero;
- score panel;
- overlays;
- translations;
- spheres;
- feedback.

### Этап 3. Wheel

- расширение API contract;
- SVG rings;
- planet points;
- aspect lines;
- selection state.

### Этап 4. Drill-down

- новый API contract;
- expanded sheet;
- scenes/repairs/notMeans;
- correct aspectId linking.

### Этап 5. Generation and testing

- processing state;
- polling;
- error states;
- screenshots;
- E2E;
- final visual comparison.

---

## 23. Не входит в задачу

- изменение астрологического scoring algorithm;
- изменение формулы общего score;
- публичное расшаривание отчёта;
- редизайн остальных разделов приложения;
- desktop-first layout;
- React Native;
- добавление новых платёжных механик.

---

## 24. Definition of Done

Функция считается завершённой, когда React-версия при открытии рядом с HTML-прототипом воспринимается как тот же интерфейс и тот же продукт:

- совпадает композиция;
- совпадает визуальная иерархия;
- совпадает цветовая логика;
- совпадает плотность;
- видна настоящая карта взаимодействия;
- техническая астрология связана с человеческими примерами;
- плохая совместимость выглядит действительно напряжённой;
- unknown time честно и заметно меняет точность отчёта;
- все данные идут из реального API, без production mock/fallback.