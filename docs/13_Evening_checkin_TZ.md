---
id: doc-13-evening
status: active
wave: W-EVENING
last_review: 2026-06-06
---
# 13. Evening CheckIn — оценка дня и точность прогноза

## Суть

Продуктовая петля: **вечером отметил → утром получил closure**. Это превращает приложение из «гороскоп на сегодня» в «дневник, который тебя знает». Главный wow-момент: «вчера ты сказал, что тревожно → мы предсказали квадратуру Луны к Сатурну → сегодня она ушла, должно отпустить».

Дополнительная цель: **измерять точность прогноза**. Разделённая оценка (настроение + совпадение) даёт метрики для улучшения скоринга.

---

## 1. Контур

```
20:00 локального времени  →  пуш/баннер «Есть прогноз: напряжённый день.
                              Марс в квадрате к Сатурну. Каково было?»
                           →  [😫 😕 😐 🙂 🤩]    ← настроение (1 тап)
                           →  [Не совсем · Частично · Да, попал!]  ← точность (1 тап)
                           ↓
                           сохраняем в evening_checkins
                           ↓
                           метрики: response_rate, completion_rate, accuracy
                           ↓
утро следующего дня       →  GET /api/day/:date
                           →  composer подтягивает вчерашний checkin
                           →  TodayPayload.yesterdayEcho.closureText
                           ↓
фронт: блок «вчера ты отметил тревогу — сегодня Луна ушла в трин,
        должно отпустить к обеду»
```

---

## 2. Формат чекина — 2 тапа, не 5

Минимум трения для максимальной конверсии. Полная форма раскрывается по «Добавить детали».

### Шаг 1: Настроение (обязательно)

```
🌙 Сегодня был напряжённый день —
   Марс в квадрате к Сатурну. Каково было?

  😫    😕    😐    🙂    🤩
  1     2     3     4     5
```

Контекстный пуш — не «отметь день», а «мы тебе кое-что скажем про ТВОЙ прогноз». Человек видит персональный прогноз и хочет оценить — это диалог, а не фидбек.

### Шаг 2: Точность (обязательно)

После нажатия настроения мгновенно:

```
Прогноз попал?

  ❌ Не совсем    🤷 Частично    ✅ Да, попал!
```

Разделение настроения и точности — ключевое. Человек мог иметь ужасный день (`mood=1`), но прогноз именно это и предсказал (`accuracy=hit`). Без разделения мы не отличим «прогноз не попал» от «день был плохой».

### Шаг 3: Детали (опционально)

Раскрывается по кнопке «Добавить детали»:

```
Что подтвердилось?
  💼 Работа    💕 Отношения    💰 Деньги
  🏥 Здоровье  ✈️ Переезд      ⚡ Другое

Заметка (опционально):
  [                                        ]
```

---

## 3. Telegram inline-кнопки

В Telegram-боте конверсия выше, чем в приложении (пуш прямо в мессенджере, inline-кнопки).

### Этап 1: Настроение

```
🌙bot: Сегодня был напряжённый день — Марс в квадрате к Сатурну.
       Каково было?

[😫 Ужасно] [😕 Так себе] [😐 Нормально] [🙂 Хорошо] [🤩 Отлично!]
```

### Этап 2: Точность (после нажатия)

```
🌙bot: Принято! А прогноз попал?

[❌ Не совсем] [🤷 Частично] [✅ Да, попал!]
```

### Этап 3: Подтверждение

```
🌙bot: Спасибо! Завтра учтём — прогноз будет точнее 🔥

   Streak: 5 дней подряд
```

---

## 4. Мотивация и конверсия

### Стимулы для заполнения

1. **Контекстный пуш** — показываем прогноз, а не просто «отметь день»
2. **«Завтра точнее»** — даже если персонализация ещё не работает, фраза создаёт ощущение ценности
3. **Streak-счётчик** — `🔥 5 дней подряд!` Лень терять → нажимают
4. **Утренний CTA** — если вечером не заполнили, утром в разборе:

```
📊 Вчерашний прогноз пока без твоей оценки
   [Оценить за 5 секунд]  ← 2 тапа
```

### Целевые метрики конверсии

| Метрика | Целевое значение | Описание |
|---------|-----------------|----------|
| `response_rate` | ≥ 40% | Из тех, кто увидел пуш — нажали настроение |
| `completion_rate` | ≥ 70% | Из нажавших настроение — нажали точность |
| `streak_7plus_pct` | ≥ 15% (через месяц) | % людей со streak 7+ дней |
| `tag_fill_rate` | ≥ 20% | % заполнивших теги (опционально) |

**Стратегия A/B**: если `response_rate` < 20% через неделю — упрощаем до 1 тапа (только настроение, без точности).

---

## 5. Схема БД

### 5.1. Миграция: обновить `evening_checkins`

Текущая таблица (MVP-заглушка) не соответствует ТЗ. Необходима миграция:

```sql
-- Добавить колонки
ALTER TABLE evening_checkins ADD COLUMN accuracy TEXT;  -- 'miss', 'partial', 'hit'
ALTER TABLE evening_checkins ADD COLUMN energy SMALLINT;  -- 1..5
ALTER TABLE evening_checkins ADD COLUMN tags TEXT[] DEFAULT '{}';
ALTER TABLE evening_checkins ADD COLUMN streak INTEGER DEFAULT 0;
ALTER TABLE evening_checkins ADD COLUMN filled_at TIMESTAMPTZ;  -- когда заполнил

-- Изменить mood: строка → число
-- Отдельная миграция: mood SMALLINT (1..5)
-- Временно: оставляем mood VARCHAR, добавляем mood_num SMALLINT
ALTER TABLE evening_checkins ADD COLUMN mood_num SMALLINT;
```

### 5.2. Итоговая схема

```sql
CREATE TABLE evening_checkins (
  id           BIGSERIAL PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  target_date  DATE   NOT NULL,                  -- день, ПРО который чекин
  mood         SMALLINT NOT NULL,                -- 1=ужасно .. 5=отлично
  accuracy     TEXT,                              -- 'miss', 'partial', 'hit'
  energy       SMALLINT,                         -- 1..5, опционально
  tags         TEXT[]   DEFAULT '{}',            -- закрытый список
  note         TEXT,                              -- ≤ 500 симв, опционально
  streak       INTEGER  DEFAULT 0,               -- текущий streak
  filled_at    TIMESTAMPTZ,                      -- когда заполнил (для конверсии)
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, target_date)
);

CREATE INDEX idx_checkins_user_date ON evening_checkins(user_id, target_date DESC);
```

### 5.3. Закрытый список тегов v1

```
work_win      — Победа на работе
work_fail     — Провал на работе
money_in      — Деньги пришли
money_out     — Деньги ушли
argument      — Конфликт
support       — Поддержка от кого-то
tired         — Усталость
energetic     — Энергичность
anxious       — Тревога
calm          — Спокойствие
focused       — Концентрация
scattered     — Рассеянность
lucky         — Удача
unlucky       — Неудача
social        — Общение
alone         — Одиночество
sport         — Спорт
sleep_bad     — Плохой сон
sleep_good    — Хороший сон
```

---

## 6. Pydantic-схемы (`apps/api/app/schemas/checkin.py`)

Заменить текущую MVP-заглушку на полную схему:

```python
from typing import Literal
from datetime import date, datetime
from pydantic import Field
from ._base import CamelModel


class CheckinCreate(CamelModel):
    target_date: date                                     # YYYY-MM-DD
    mood: Literal[1, 2, 3, 4, 5]                          # 1=ужасно .. 5=отлично
    accuracy: Literal["miss", "partial", "hit"] | None = None  # совпал ли прогноз
    energy: Literal[1, 2, 3, 4, 5] | None = None          # опционально
    tags: list[str] | None = None                          # из закрытого списка
    note: str | None = Field(None, max_length=500)        # опционально


class CheckinResponse(CamelModel):
    id: int
    target_date: str                                       # ISO date
    mood: int                                              # 1..5
    accuracy: str | None                                    # 'miss' | 'partial' | 'hit'
    energy: int | None                                      # 1..5
    tags: list[str]                                         # []
    note: str | None
    streak: int                                            # текущий streak
    filled_at: str | None                                   # ISO datetime
    created_at: str


class CheckinMetrics(CamelModel):
    """Агрегированные метрики для дашборда."""
    date: str                                              # ISO date
    eligible: int                                          # получили пуш
    responded: int                                         # нажали настроение
    completed: int                                         # нажали точность
    response_rate: float                                   # responded / eligible
    completion_rate: float                                 # completed / responded
    accuracy_distribution: dict[str, int]                  # {"miss": 5, "partial": 12, "hit": 33}
    mood_average: float | None                             # среднее настроение
    streak_avg: float                                      # средний streak
    streak_7plus_pct: float                                # % со streak 7+
```

---

## 7. API контракты

### 7.1. POST /api/checkin

Создать или обновить чекин (upsert). Возвращает `CheckinResponse` со `streak`.

```json
// request
{
  "targetDate": "2026-06-05",
  "mood": 3,
  "accuracy": "partial",
  "tags": ["anxious", "work_win"]
}

// response
{
  "id": 42,
  "targetDate": "2026-06-05",
  "mood": 3,
  "accuracy": "partial",
  "energy": null,
  "tags": ["anxious", "work_win"],
  "note": null,
  "streak": 5,
  "filledAt": "2026-06-05T21:03:00Z",
  "createdAt": "2026-06-05T21:03:00Z"
}
```

### 7.2. GET /api/checkin/:date

Возвращает чекин за дату или 404.

### 7.3. GET /api/checkin/yesterday

Шорткат для composer-а. Возвращает чекин за вчера в TZ пользователя или `null`.

### 7.4. GET /api/checkin/metrics

Агрегированные метрики за период. Только для внутренних целей (админ-дашборд).

Параметры: `?from=2026-06-01&to=2026-06-07`

### 7.5. POST /api/checkin/send-reminder

Отправить вечернее напоминание (Telegram-бот или пуш). Для MVP — ручной триггер, потом — cron.

---

## 8. Composer: yesterdayEcho

В `services/today_composer.py` после нормализации/скоринга/microcopy:

```python
1. yesterday_checkin = checkin_service.get_checkin(user_id, yesterday_in_user_tz)
2. yesterday_payload  = day_cache.get(user_id, yesterday)
3. closure = yesterday_service.build_closure(
       yesterday_checkin,
       yesterday_events=yesterday_payload.normalized_events if yesterday_payload else None,
       today_events=today_payload.normalized_events,
       today_status=today_payload.day_status,
   )
4. today_payload.yesterday_echo = closure  # или None
```

### 8.1. Логика `build_closure`

- Если чекина нет → `yesterdayEcho = None`. Не выдумываем.
- Если есть, берём 1 событие вчера с самым высоким весом, которое тематически совпадает с тегами/настроением чекина.
- Сравниваем с сегодняшним: ушло / усилилось / трансформировалось.
- Берём фразу из словаря закрытий по ключу `(yesterday_polarity, today_polarity, transition)`.

### 8.2. Примеры closure_text

- `"Вчера давила квадратура Луна–Сатурн — ты отметил тревогу. Сегодня Луна ушла в трин, должно отпустить к обеду."`
- `"Вчера ты поймал волну (Венера в трине к Юпитеру) и сам это почувствовал. Сегодня волна стихает, не жди повтора — фиксируй."`
- `"Вчера прогноз попал частично — мы говорили про напряжение в отношениях, ты отметил спокойствие. Сегодня аспект мягчеет."`

### 8.3. Типы YesterdayEcho

```typescript
export type YesterdayEcho = {
  hadCheckin: boolean
  mood?: 1 | 2 | 3 | 4 | 5
  accuracy?: "miss" | "partial" | "hit"
  closureText: string        // 1–2 предложения
  transition: "released" | "intensified" | "shifted" | "continued"
  yesterdayHighlight?: string  // "Марс в квадрате к Сатурну"
}
```

---

## 9. TodayPayload — расширение

Добавить в `TodayPayload`:

```typescript
yesterdayEcho?: YesterdayEcho
```

Фронт показывает блок `yesterdayEcho` только если `hadCheckin === true`.
Иначе — CTA «Оценить вчерашний день» (если время > 08:00 и чекина за вчера нет).

---

## 10. Streak-логика

```python
def compute_streak(user_id: UUID, db: AsyncSession) -> int:
    """Посчитать текущий streak: сколько дней подряд заполнял чекин."""
    today = date.today()
    streak = 0
    for i in range(1, 366):  # макс 365 дней
        check = await db.execute(
            select(EveningCheckin).where(
                EveningCheckin.user_id == user_id,
                EveningCheckin.target_date == today - timedelta(days=i)
            )
        )
        if check.scalar_one_or_none():
            streak += 1
        else:
            break
    return streak
```

Streak обновляется при каждом `POST /api/checkin`. Хранится в `evening_checkins.streak`.

Используется в ответе и в геймификации:
- `🔥 5 дней подряд!`
- `🔥 30 дней! Ты огонь!` (уведомление при достижении 30)

---

## 11. Уведомления

### 11.1. Вечерний пуш (20:00 локального времени)

Не «отметь, как прошёл день» (обязаловка), а контекстный:

```
🌙 Сегодня был напряжённый день —
   Марс в квадрате к Сатурну. Каково было?

[😫] [😕] [😐] [🙂] [🤩]
```

Inline-кнопки прямо в пуше (Telegram). В приложении — баннер с тем же текстом.

### 11.2. Утренний CTA (если не заполнили вечером)

В разборе дня, если чекина за вчера нет и время > 08:00:

```
📊 Вчерашний прогноз пока без твоей оценки
   [Оценить за 5 секунд]
```

### 11.3. Anti-spam

- Не больше 1 пуша в день
- Если чекин уже есть — не шлём вечерний пуш
- Если чекин за вчера есть — не показываем утренний CTA

### 11.4. Cron (будущее)

```
apps/api/app/workers/evening_push.py
```

Раз в час пробегает по пользователям, у кого `tz_offset` = текущему часу `20:00 - now`. Отправляет Telegram inline-кнопки.

---

## 12. Метрики конверсии и качества прогноза

### 12.1. Что собираем

| Событие | Где логируем | Какие данные |
|---------|-------------|-------------|
| Пуш отправлен | `checkin_metrics` | user_id, date, type=push_sent |
| Пуш открыт | webhook | user_id, date, type=push_opened |
| Настроение нажато | `POST /api/checkin` | user_id, date, mood |
| Точность нажата | `POST /api/checkin` | user_id, date, accuracy |
| Теги добавлены | `POST /api/checkin` | user_id, date, tags[] |

### 12.2. Агрегированные метрики

```python
class CheckinMetrics:
    date: str                                    # ISO date (день агрегации)
    eligible: int                                # сколько людей получили пуш
    responded: int                               # сколько нажали настроение
    completed: int                               # сколько нажали точность
    response_rate: float                         # responded / eligible
    completion_rate: float                       # completed / responded
    accuracy_distribution: dict[str, int]         # {"miss": 5, "partial": 12, "hit": 33}
    mood_average: float | None                   # среднее настроение (1-5)
    mood_by_day_status: dict[str, float]          # {"tense": 2.3, "steady": 3.1, "supportive": 4.0}
    streak_avg: float                             # средний streak
    streak_7plus_pct: float                       # % со streak 7+
```

### 12.3. Как используем метрики

1. **Мониторинг конверсии**: `response_rate` < 20% → упрощаем до 1 тапа (только настроение)
2. **Качество прогноза**: `accuracy_distribution` → `% hit + 0.5 * partial` = `overall_accuracy`
3. **Корреляция**: `mood_by_day_status` → если `tense` → `mood=2.1` — прогноз попадает в тон
4. **Улучшение весов**: если `accuracy=miss` чаще для конкретной сферы → перекалибровать `spheres.v1.yml`
5. **A/B тесты**: новый скоринг vs старый → сравниваем `overall_accuracy`

---

## 13. Безопасность и приватность

- `note` — свободный текст, может содержать персональное. Не логируем в общий лог, не шлём в LLM без явного согласия.
- В payload composer-у отдаём только `mood/accuracy/tags`, без `note`, если `prompt_version` не помечен как «note-aware».
- Удаление аккаунта → каскадно удаляются чекины (`ON DELETE CASCADE`).
- `filled_at` — используется только для аналитики конверсии, не показывается пользователю.

---

## 14. Фронтенд

### 14.1. Экран чекина (приложение)

```
┌─────────────────────────────────────┐
│  ← Разборы                          │
│                                     │
│  🌙 Как прошёл день?                │
│                                     │
│  Мы говорили: напряжённый,          │
│  карьера под ударом                 │
│                                     │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐│
│  │ 😫  │ │ 😕  │ │ 😐  │ │ 🙂  │ │ 🤩  ││
│  │  1  │ │  2  │ │  3  │ │  4  │ │  5  ││
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘│
│                                     │
│  Прогноз попал?                     │
│                                     │
│  [❌ Не совсем] [🤷 Частично] [✅ Да!] │
│                                     │
│  [Добавить детали ▾]                │
│                                     │
└─────────────────────────────────────┘
```

Раскрывшиеся «Добавить детали»:

```
│  Что подтвердилось?                  │
│  [💼 Работа] [💕 Отношения] [💰 Деньги]│
│  [🏥 Здоровье] [✈️ Переезд] [⚡ Другое]│
│                                     │
│  Заметка (опционально):            │
│  ┌─────────────────────────────┐   │
│  └─────────────────────────────┘   │
│                                     │
│  🔥 5 дней подряд                  │
└─────────────────────────────────────┘
```

### 14.2. Блок YesterdayEcho (в разборе дня)

```
┌─────────────────────────────────────┐
│  📊 Вчера ты отметил: 😐 нормально  │
│  «Марс в квадрате к Сатурну —       │
│   ты отметил тревогу. Сегодня       │
│   аспект мягчеет, должно отпустить» │
│                                     │
│  Прогноз совпал: 🤷 частично       │
└─────────────────────────────────────┘
```

Если чекина за вчера нет:

```
┌─────────────────────────────────────┐
│  📊 Вчера прогноз был без оценки    │
│  [Оценить за 5 секунд]             │
└─────────────────────────────────────┘
```

### 14.3. Файловая структура

```
components/checkin/
  checkin-screen.tsx         — Главный экран чекина
  mood-selector.tsx           — Выбор настроения (5 кнопок)
  accuracy-selector.tsx      — Выбор точности (3 кнопки)
  checkin-tags.tsx           — Теги (опционально)
  yesterday-echo.tsx          — Блок «Вчера» в разборе дня

lib/contracts/checkin.ts    — Zod-схемы + типы
lib/api/checkin.ts            — API-фасад
```

---

## 15. DoD

### Бэкенд
- [ ] Миграция alembic: добавить `accuracy`, `energy`, `tags`, `streak`, `filled_at` в `evening_checkins`; изменить `mood` с VARCHAR на SMALLINT
- [ ] Обновить `apps/api/app/schemas/checkin.py`: полная схема `CheckinCreate` (mood 1-5, accuracy, energy, tags, note)
- [ ] Обновить `apps/api/app/services/checkin_service.py`: upsert с новыми полями, streak computation
- [ ] `GET /api/checkin/yesterday` endpoint
- [ ] `GET /api/checkin/metrics` endpoint (агрегация за период)
- [ ] `services/yesterday_service.py`: `build_closure` + покрытие тестами на 6 кейсов (released/intensified/shifted/continued × had_data/no_data)
- [ ] `today_composer` подмешивает `yesterdayEcho` в TodayPayload
- [ ] Контракт `packages/contracts/checkin.ts` обновлён

### Фронтенд
- [ ] Экран чекина: mood-selector, accuracy-selector, теги, заметка
- [ ] Блок YesterdayEcho в разборе дня
- [ ] CTA «Оценить вчерашний день» если чекина нет
- [ ] Streak-отображение («🔥 5 дней подряд»)

### Telegram-бот (опционально, следующая волна)
- [ ] Inline-кнопки для чекина (mood → accuracy)
- [ ] Контекстный пуш с прогнозом дня
- [ ] Streak-уведомления при 7, 14, 30 днях

### Воркер (опционально, следующая волна)
- [ ] Cron: вечерние_PUSHи по TZ (20:00 локального времени)
- [ ] Anti-spam: не более 1 пуша/день, не шлём если чекин есть

---

## 16. Текущая реализация (MVP-заглушка)

Существующая реализация не соответствует ТЗ:

| Что | ТЗ | Реализация | Статус |
|-----|----|-----------|--------|
| `mood` | `1..5` (число) | `str` ("great"/"good"/"neutral"/"bad") | ❌ Нужно менять |
| `accuracy` | `"miss"/"partial"/"hit"` | Нет | ❌ Нет |
| `energy` | `1..5` | Нет | ❌ Нет |
| `tags` | `str[]` из закрытого списка | Нет | ❌ Нет |
| `note` | `≤500 chars` | `notes` (Text) | ⚠️ rename |
| `streak` | `int` | Нет | ❌ Нет |
| `filled_at` | `datetime` | Нет | ❌ Нет |
| `GET /api/checkin/yesterday` | Да | Нет | ❌ Нет |
| `GET /api/checkin/metrics` | Да | Нет | ❌ Нет |
| `yesterdayEcho` в TodayPayload | Да | Нет | ❌ Нет |
| Контекстный пуш | Да | Нет | ❌ Нет |
| Streak | Да | Нет | ❌ Нет |

Текущая реализация — базовый upsert с `mood: str` и `notes: str`. Нужна миграция ⬆️ и расширение сервиса.