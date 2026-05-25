---
id: doc-08-frontend-state
status: active
wave: W-2.0
last_review: 2026-05-25
---
# 08. Frontend current state and alignment

## Роль документа

Этот документ фиксирует состояние v0.app MVP-фронта на момент последней проверки и расхождения с проектными документами.

---

# Что уже хорошо совпадает

Роутинг сделан близко к проектной модели:

- `/`
- `/day/[date]`
- `/calendar`
- `/readings`
- `/readings/natal`
- `/readings/natal/[section]`
- `/profile`

Модель **Today = экран выбранного дня** соблюдена. Дата живёт в URL. Стрелки, свайпы и 7-дневная лента меняют день через route.

Натальная карта близка к зафиксированной архитектуре:

- `schemaVersion: "natal/v1"`;
- `sections[].blocks[]`;
- `block.type → component`;
- overview `/readings/natal`;
- отдельные главы `/readings/natal/[section]`.

Также хорошо:

- `next.config.mjs` без `ignoreBuildErrors`;
- есть API-фасады `lib/api/*`;
- компоненты не ходят напрямую в fixtures;
- есть Zod-валидация mock-данных;
- верхние флаги раскрываются хинтами;
- `WhyExpanded` рассчитан на секции / абзацы / bullets;
- онбординг сохраняет профиль;
- календарь ограничен ±1 месяц;
- тап по дню ведёт на `/day/:date`.

---

# Главные расхождения с документами

## 1. TodayPayload

В документах:

```ts
TodayPayload = {
  meta
  date
  title
  subtitle?
  headline
  access
  dayStatus
  dayQuality?
  topFlags
  reading
  whyThisHappens
  weekStrip
  actions?
}
```

В коде было ближе к:

```ts
TodayPayload = {
  date
  notes
  reading
  why
  keyInsight
}
```

Нужно выровнять:

| Документ | Текущий фронт | Действие |
|---|---|---|
| `topFlags` | `notes` | переименовать |
| `summary` | `description` | привести к `summary` |
| `hint.whyToday` | `hint.whyImportant` | привести к документу |
| `hint.howItFeels` | `hint.howForMe` | привести к документу |
| `whyThisHappens.sections` | `why` | завернуть в объект |
| `headline` | нет / keyInsight | добавить / выровнять |
| `access` | отдельно через `useAccess` | добавить в payload |
| `dayStatus/dayQuality` | нет | добавить |
| `weekStrip` | считается на фронте | позже должен приходить с backend |
| `meta` | нет | добавить versioning |

---

## 2. Статусы дня

В документах:

```ts
"supportive" | "steady" | "tense"
```

Во фронте:

```ts
"supportive" | "even" | "tense"
```

Нужно заменить:

```text
even → steady
```

UI-лейбл остаётся **ровный**.

---

## 3. CalendarPayload

В документах:

```ts
{
  meta,
  month,
  title,
  allowedRange,
  days: CalendarDay[]
}
```

Во фронте было ближе к status map:

```ts
Record<date, DayStatus>
```

Для backend нужно добавить:

- `access`;
- `isCurrentMonth`;
- `isToday`;
- `allowedRange`;
- `disabled` для дней вне диапазона;
- `meta`.

---

## 4. Access contract

Нужно разделить два уровня:

### UserAccessState

```ts
"trial" | "subscription" | "expired" | "none"
```

Это состояние пользователя.

### ContentAccessState

```ts
{
  state: "full" | "preview" | "locked"
  reason?: string
}
```

Это состояние конкретного дня / разбора.

В API не должно быть `Date`-объектов. Только ISO strings.

---

## 5. Readings contract

В документах:

```ts
ReadingsPayload = {
  meta
  sections: ReadingSection[]
}
```

Во фронте было:

```ts
{
  available: AvailableReading[]
  coming: ComingReading[]
}
```

Проблема: в данных нельзя хранить `LucideIcon`, потому что backend не может сериализовать React-компонент.

Нужно заменить на:

```ts
iconName: "sparkles" | "horary" | "calendar_range" | ...
```

Frontend мапит:

```ts
iconName → LucideIcon
```

---

## 6. Natal contract

Архитектура близкая, но есть расхождения.

### Meta

В документах:

```ts
meta: {
  title
  subtitle?
  generatedAt
  calculationVersion?
  interpretationVersion?
  person?
}
```

Во фронте было ближе к:

```ts
meta: {
  name
  birth
  mode?
  houseSystem?
  generatedAt?
}
```

Лучше добавить `title`, `subtitle`, `person`.

### Highlights

В документах:

```ts
{ id, title, text, tone }
```

Во фронте было:

```ts
{ id, label, value, hint }
```

Нужно выбрать одну форму. Если это chips, можно переименовать в `chips`. Если highlights — привести к документу.

### Spheres

В документах:

```ts
{ id, title, score?, salience?, ease?, tension?, summary }
```

Во фронте было:

```ts
{ id, title, dominance, metrics?, tone? }
```

Нужно унифицировать до backend.

### Unknown block behavior

В документах: неизвестный `block.type` должен пропускаться и не ломать экран.

Renderer возвращает `null`, но Zod `discriminatedUnion` может упасть раньше.

Нужно сделать tolerant schema:

```ts
const UnknownBlockSchema = z.object({
  type: z.string(),
}).passthrough()
```

Или production-parse делать tolerant.

---

## 7. Пятая вкладка «Спросить»

В документах нижняя навигация: 4 вкладки.

- Сегодня
- Календарь
- Разборы
- Профиль

Во фронте появилась 5-я вкладка:

- Спросить
- route `/chat`

Нужно принять продуктово:

1. либо оставить чат в MVP и обновить документы;
2. либо убрать из нижней навигации до следующей версии.

Если оставлять, не смешивать с хораром. Чат — AI-ассистент по карте. Хорар — отдельный платный разбор.

---

## 8. Онбординг

### Кнопка «Пропустить»

Для dev-режима ок, но в настоящем MVP обычному пользователю нельзя показывать:

**«Пропустить и сразу открыть приложение»**

Без данных продукту нечего считать. Спрятать под dev flag.

### Термин «соляр»

На онбординге лучше не писать «соляр».

Лучше:

> Это нужно для точного годового разбора. Если город совпадает с текущим, просто подтверди.

---

## 9. LocationValue вместо строк

Для расчётов нужны не строки городов, а координаты и timezone.

Вместо:

```ts
birthPlace: string
currentCity: string
birthdayCity: string
```

Нужно:

```ts
type LocationValue = {
  name: string
  country?: string
  latitude?: number
  longitude?: number
  timezone?: string
}
```

Это важно для SolarSage, соляра, домов, Луны и текущего контекста.

---

## 10. Nested scroll

AppShell должен по возможности быть главным scroll-контейнером.

Внутренние `overflow-y-auto` на основных экранах могут конфликтовать в Telegram WebView.

Допустимы внутренние скроллы для:

- modal;
- edit sheet;
- bottom sheet.

Основные экраны лучше проверить на телефоне.

---

# Приоритет правок

1. Привести `TodayPayload` к документу `05`.
2. Переименовать `even → steady`.
3. Сделать полноценный `CalendarPayload`.
4. Разделить user access и content access.
5. Убрать `Date` из API-совместимых контрактов, использовать ISO strings.
6. Убрать `LucideIcon` из readings data, заменить на `iconName`.
7. Сделать natal blocks tolerant к неизвестным `block.type`.
8. Решить судьбу 5-й вкладки «Спросить».
9. Перевести города с `string` на `LocationValue`.
10. Спрятать «Пропустить» под dev flag.

---

# Оценка размера правок

Это не переписывание фронта.

Каркас уже правильный:

- роутинг есть;
- экраны есть;
- API-фасады есть;
- Zod-схемы есть;
- моки вынесены;
- block-renderer для натала есть;
- Today компонентно разложен.

Большинство правок — это выравнивание типов, fixtures, адаптеров и контрактов.

Оценка:

- базовое выравнивание контрактов: 1–2 дня;
- вместе с LocationValue, CalendarPayload, access separation и WebView-проверкой: 2–4 дня.

---

# Рекомендуемый prompt для frontend-агента

> Выровняй фронтовые контракты с документами `05 API contracts и TodayPayload` и `06 Натальная карта: контракт и фронт`. Сохрани существующий UI и роутинг. Не переписывай визуальные компоненты без необходимости. Основная задача — привести types, fixtures, Zod schemas и API facades к стабильным backend-ready payloads.
