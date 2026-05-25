---
id: doc-12-microcopy
status: planned
wave: W-MICROCOPY
last_review: 2026-05-25
---
## docs/12 — Словарь микро-описаний (Microcopy Dictionary)

Цель: иметь управляемый, версионируемый набор из ~70+ коротких астрологических фраз, который ежедневно склеивается в текст «чтобы все охуели» — конкретно про сегодняшний день этого пользователя, без воды.

Этот слой — **контент**, не нормализация и не скоринг. Он живёт между нормализацией и финальным composer-ом.

---

### 1. Где живёт

```
apps/api/
  app/content/
    microcopy.v1.json          # сам словарь, версионируемый
    microcopy.schema.json      # JSON Schema для валидации
  app/services/
    microcopy.py               # выбор top-N фраз под конкретный день
```

Словарь — **код-как-данные**: лежит в репозитории, ревьюится через PR, на проде подменяется атомарно (см. § 6 Версионирование).

---

### 2. Структура одной записи

```json
{
  "id": "sun_trine_jupiter_applying",
  "key": {
    "body": "sun",
    "aspect": "trine",
    "target": "jupiter",
    "polarity": "soft",
    "speed": "fast",
    "applying": true
  },
  "text_short": "Сегодня тебя несёт — пользуйся, не тормози.",
  "text_long": "Солнце в трине к Юпитеру: день, когда удача любит наглых. То, что ты откладывал из вежливости, можно делать сегодня.",
  "tone": ["bold", "supportive"],
  "tags": ["luck", "expansion", "social"],
  "weight": 1.0,
  "min_orb_deg": 0.0,
  "max_orb_deg": 6.0,
  "scales_hint": { "energy": +1, "risk": -1 }
}
```

Поля:
- **id** — стабильный slug, в `TodayPayload.microcopy[].id` уходит он же (для аналитики).
- **key** — ключ выбора. Совпадает с тем, что выдаёт нормализация на каждое событие.
- **text_short** — для бейджей/чипов в UI (≤ 80 символов).
- **text_long** — для секции «Почему сегодня так» (≤ 240 символов, 1–2 предложения).
- **tone** — стилистика, composer выбирает фразы под общий тон дня (`bold` для intense, `gentle` для tense без хорошего, и т.д.).
- **tags** — тематика, не для логики, а для отчётов и поиска дублей.
- **weight** — базовый приоритет (0.0–1.5). Composer умножает на orb-вес и значимость планет.
- **min/max_orb_deg** — фразу не показываем, если событие за пределами орбиса.
- **scales_hint** — куда сдвигает шкалы дня (для cross-check со scoring; не источник правды).

---

### 3. Покрытие (минимум 70 фраз)

Обязательное покрытие на v1:

- **Транзиты планет к натальным светилам и углам**: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto → к Sun, Moon, ASC, MC, Venus, Mars.
- **Аспекты**: conjunction, opposition, square, trine, sextile.
- **Полярность**: soft (trine/sextile) vs hard (square/opposition/часть конъюнкций).
- **Состояния**: applying / exact / separating (для exact — отдельная финальная фраза-удар).
- **Лунные акценты дня**: void-of-course, смена знака, фаза (new/full).
- **Ретрограды** (Mercury, Venus, Mars) — отдельные фразы про начало/середину/конец.

Не пытаемся покрыть всё сразу — на v1 хватит 70–90 ключей с самыми частыми сочетаниями. Дальше расширяем по аналитике пропусков (см. § 7).

---

### 4. Алгоритм выбора (microcopy.py)

Вход: `List[NormalizedEvent]` от нормализации + `Scales` от скоринга + `tone_target` от composer.

```
1. Для каждого события ищем microcopy по key (с fallback по полярности).
2. Считаем score = weight * orb_factor * planet_significance * tone_match.
3. Сортируем по score, берём top-K (по умолчанию K=6).
4. Дедуп по target (не два сообщения про одну и ту же натальную точку).
5. Возвращаем List[MicrocopyItem] для TodayPayload.
```

Если для события **нет** записи в словаре — событие **не пропадает**, но в payload идёт без текста (только событие + scales). В логи пишем `microcopy_miss` для будущего пополнения.

---

### 5. Формат в TodayPayload

Добавляется новое поле:

```ts
export type MicrocopyItem = {
  id: string;
  textShort: string;
  textLong: string;
  tone: ("bold" | "supportive" | "gentle" | "warning")[];
  scope: "today" | "morning" | "evening";
};

// в TodayPayload:
microcopy: MicrocopyItem[];   // top-K, отсортировано по приоритету
```

Фронт сам решает, куда их распихать: первые 1–2 в headline-зону, остальные — в `whyThisHappens` как bullets, или в отдельный «Что особенно сегодня» список.

---

### 6. Версионирование

- В `.env`: `CONTENT_VERSION=1` (новая переменная — добавить в `.env.example`).
- В payload: `meta.contentVersion: number`.
- Файл словаря именуется `microcopy.v{N}.json`. При мажорном изменении ключей — новый файл, старый не удаляем (для воспроизводимости старых дней из кеша).
- Минорные правки текстов — внутри текущей версии, но логируется git-хеш файла (для дебага «почему вчерашний день читается иначе»).

---

### 7. Аналитика и пополнение

- Каждый `microcopy_miss` пишется в таблицу `microcopy_misses(date, user_id, event_key, count)`.
- Раз в неделю — отчёт топ-50 пропусков, по нему пополняется словарь.
- A/B текстов: поле `variant` (опц.) внутри одного `id`, composer выбирает по hash(user_id + date) — стабильно для пользователя, разнообразно по аудитории.

---

### 8. DoD

- [ ] `microcopy.v1.json` содержит ≥ 70 валидных записей, покрывающих все мажорные транзиты к Sun/Moon/ASC.
- [ ] `microcopy.schema.json` валидирует словарь в CI.
- [ ] `services/microcopy.py` реализует выбор top-K с дедупом по target.
- [ ] Тесты: для эталонного `sample_params.json` (Vasiliy) на фиксированную дату возвращается ровно ожидаемый набор id (snapshot test).
- [ ] `TodayPayload.microcopy` всегда непустой для дней со статусом ≠ idle.
- [ ] `microcopy_miss` логируется и не ломает запрос.
