---
id: doc-09-transfer
status: active
wave: none
last_review: 2026-06-08
---
# 09. Project transfer context

## Назначение

Этот файл — краткий контекст для переноса проекта в другой чат или передачи новому агенту. Детальные решения находятся в профильных ТЗ и GRACE-документах.

---

# Что за проект

Telegram Mini App с персональным астрологическим ассистентом.

Главный экран MVP — **Today screen**. Продукт не даёт общий гороскоп, а объясняет человеку:

> Это рассчитано именно про меня и объясняет мой день, состояние, фокус, трудности и опоры.

Главный принцип продукта:

```text
Не «что происходит на небе», а «как это проявляется у меня».
```

---

# MVP

В MVP входят:

- onboarding;
- Today screen;
- Calendar;
- Readings;
- Profile;
- soft lock / paywall.

Нижняя навигация:

- Сегодня;
- Календарь;
- Разборы;
- Профиль.

Во фронтовом макете появилась вкладка **Спросить** — её судьба всё ещё отдельное product decision.

---

# Today screen

Структура:

1. Дата + стрелки.
2. Верхние флаги «Сегодня важно учесть».
3. Основной текст дня.
4. Inline-раскрытие «Почему так у меня».
5. 7-дневная лента.
6. Нижняя навигация.

Главная ценность — персональный текст на 3–5 минут чтения.

---

# Верхние флаги

2–4 строки, оптимально 3.

Каждая строка:

- иконка / маркер;
- заголовок;
- короткая расшифровка;
- стрелка справа;
- tap раскрывает inline hint.

Флаги не открывают отдельный экран.

---

# Почему так у меня

Это inline-раскрытие внутри Today, не отдельный экран.

Структура:

1. Главная тема дня.
2. Быстрый слой дня.
3. Почему это задевает именно тебя.
4. Фон периода.
5. Что усиливает этот день.
6. Что смягчает этот день.
7. Через какие сферы это проявляется.
8. Астрологический смысл дня.
9. Что это значит practically.

Стиль: много астрологического мяса, но всё переводится в проявление для пользователя.

---

# 7-дневная лента

Для MVP используем 3 статуса:

- supportive / поддерживающий;
- steady / ровный;
- tense / напряжённый.

Календарь — навигация по дням, не месячный прогноз.

---

# Доступ и монетизация

Постоянного free-tier нет.

Основной бесплатный вход:

```text
Пригласи друга — вы оба получите 14 дней доступа.
```

Правило списания access-дней:

1. сначала тратятся подарочные / реферальные дни;
2. потом подписка;
3. если подписки нет — доступ закрывается.

Без доступа интерфейс остаётся видимым, но полный контент закрыт через soft lock / paywall.

Locked day должен открываться как preview + paywall, а не быть мёртвой датой.

---

# Хорар

Хорар входит в продуктовую карту и раздел «Разборы».

Актуальный source of truth: `docs/16_Horary_questions_TZ.md`.

Ключевые правила:

- активный доступ даёт **1 бесплатный хорарный вопрос в неделю доступа**;
- этот weekly-free вопрос называется `subscription_weekly_free`;
- weekly-free вопрос **не копится**;
- weekly-free вопрос **сгорает** в конце своей недели доступа, если пользователь его не использовал;
- продление trial/referral/gift/subscription создаёт будущие недели доступа, но не выдаёт все будущие weekly-вопросы сразу;
- paid-хорары копятся и не сгорают по умолчанию;
- gift/referral/adjustment-хорары живут по своему `expires_at`;
- порядок списания: `subscription_weekly_free` → expiring gift/referral/adjustment → paid.

Deprecated:

```text
weekly_bonus
3 стартовых бесплатных вопроса
+1 накапливающийся вопрос каждые 7 дней
questions_used / questions_limit как основная модель баланса
```

---

# SolarSage и расчёт

Подход:

```text
Считаем максимально много, но показываем только стабильный продуктовый слой.
```

Слои:

- SolarSage raw calculations;
- NatalDeepSnapshot;
- PeriodSnapshot;
- DailySnapshot;
- Normalized AstroSignal[];
- SemanticLayer;
- LLM interpretation;
- TodayPayload.

Формула:

```text
Day v1 = DailySky + PersonalActivations + PeriodBackground + NatalSensitivity + QualityModifiers
```

Контрастный день не должен превращаться в «ровный» из-за взаимного обнуления поддержки и трения.

Для тихих дней нужен fallback на daily sky, а не натягивание слабого аспекта на главный сюжет.

---

# LLM

LLM не получает raw SolarSage.

Она получает curated SemanticLayer:

- main theme;
- top flags;
- daily triggers;
- personal activations;
- period background;
- amplifiers;
- softeners;
- manifestation zones;
- practical direction.

LLM не должна упоминать internal scoring fields, raw JSON, backend evidence или internal ranking.

---

# API contracts

Главный endpoint:

```http
GET /api/day/:date
```

Фронт работает с `TodayPayload`, а не с raw SolarSage.

Стабилизируем форму выдачи, а не расчётную формулу.

---

# Натальная карта

Натальный разбор строится как versioned document:

```text
schemaVersion: "natal/v1"
sections[].blocks[]
block.type → component
```

Unknown block type не должен ломать экран.

---

# Текущий фронт

v0.app макет уже близок к архитектуре:

- route-per-day есть;
- Today screen есть;
- Calendar есть;
- Readings есть;
- Profile есть;
- Natal block renderer есть;
- Zod schemas есть;
- fixtures вынесены.

Нужно выровнять контракты:

1. `notes → topFlags`;
2. `why → whyThisHappens`;
3. `even → steady`;
4. добавить `meta`, `headline`, `access`, `dayStatus`, `dayQuality`;
5. сделать полноценный `CalendarPayload`;
6. разделить user access и content access;
7. заменить `LucideIcon` на `iconName`;
8. сделать natal block schema tolerant;
9. перейти от строк городов к `LocationValue`;
10. решить судьбу вкладки «Спросить».

---

# Backend следующий шаг

Проектировать backend вокруг:

```http
GET /api/day/:date
```

Фазы:

1. Telegram auth + profile;
2. access/referral;
3. mocked TodayPayload API;
4. SolarSage integration;
5. normalization/scoring;
6. LLM generation;
7. payments;
8. horary questions.

---

# Главные документы

- `00_Обзор_продукта.md`
- `01_MVP_экраны_и_навигация.md`
- `02_Today_screen.md`
- `03_Почему_так_у_меня.md`
- `04_SolarSage_нормализация_скоринг_кеширование.md`
- `05_API_contracts_и_TodayPayload.md`
- `06_Натальная_карта_контракт_и_фронт.md`
- `07_Backend_architecture_draft.md`
- `08_Frontend_current_state_and_alignment.md`
- `16_Horary_questions_TZ.md`
- `grace/requirements.xml`
