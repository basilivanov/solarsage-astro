# W4 TZ: «Что сошлось именно сегодня», события со временем и быстрый Today

Дата: 2026-07-28

Статус: **pre-implementation product/backend contract**

Phase / Wave: **W4-TODAY-CONVERGENCE**

Связанные документы:

- [`00_MASTER_TZ.md`](./00_MASTER_TZ.md) — текущая композиция экрана Today;
- [`20_TZ_S2_DAY_SYNTHESIS.md`](./20_TZ_S2_DAY_SYNTHESIS.md) — текущий
  `mainAdvice`;
- [`12_TZ_V1_VALENCE_CANON.md`](./12_TZ_V1_VALENCE_CANON.md) и
  [`13_TZ_V2_FACTOR_LEDGER.md`](./13_TZ_V2_FACTOR_LEDGER.md) — источник
  честной valence и canonical factor identity;
- [`09_TZ_M6_DETERMINISTIC_WHY.md`](./09_TZ_M6_DETERMINISTIC_WHY.md) —
  принцип «причинность не принадлежит LLM».

Владелец продуктового решения: архитектор/ревьюер.

Визуальный дизайн: **отдельная дизайн-модель после утверждения этого
контракта**.

Коммит/пуш: только по правилам текущей волны.

---

## 0. Приоритет и границы

Этот документ переопределяет в пределах нового блока следующие старые
решения:

1. Верхние три сферы больше нельзя получать как `rows.sort(rank).slice(0, 3)`.
   Текущий `rank` — canonical order (`work`, `money`, `documents`, ...), а не
   персональная релевантность даты.
2. Три горизонта `long|medium|fast` остаются доказательным материалом, но UI
   не обязан каждый день показывать ровно три слоя и не должен выдавать
   годовой фон за новое событие дня.
3. «Почему так у меня» больше не должно быть LLM-портянкой из девяти секций.
   Факты, время, связи и выбор сфер рассчитываются детерминированно; LLM может
   только кратко сформулировать человеческий смысл уже выбранных фактов.
4. Полные 12 сфер сохраняются ниже как навигатор состояния дня. Они не
   являются двенадцатью независимыми событиями и не обязаны получать
   дорогостоящий LLM-текст до открытия пользователем.

Не входит в это ТЗ:

- выбор сетки, типографики, цветов, размеров, анимаций и окончательной
  композиции блока;
- изменение эфемерид, орбисов, астрономии или timing solver sidecar;
- обещание реальных внешних происшествий («будет ссора», «придут деньги»);
- квота «обязательно три сферы» или искусственное разнообразие сфер;
- миграция на другую LLM-модель без измеримого benchmark.

---

## 1. Продуктовая цель

Пользователь за несколько секунд должен понять:

1. **Что действительно выделяет эту дату**, а не повторяется весь год.
2. **Какие рассчитанные события происходят и во сколько** в его часовом
   поясе.
3. **Есть ли общий сюжет**, то есть сошлись ли несколько независимых факторов.
4. **В каких 0–3 сферах этот сюжет вероятнее проявится**.
5. Что делать практически — одной короткой рекомендацией, без портянки.

Главный продуктовый тезис:

> «Что сошлось именно сегодня» — не синоним «три самых сильных фактора» и не
> синоним «долгий + средний + быстрый». Это минимум два связанных,
> дедуплицированных фактора вокруг одной темы, среди которых есть хотя бы один
> привязанный к выбранной локальной дате импульс.

Если условие не выполнено, продукт не притворяется, что схождение есть.

---

## 2. Термины

### 2.1. Рассчитанное событие

**Рассчитанное событие** — астрологический факт с provenance и временем из
расчётного контура, например точный аспект или начало активного окна.

Это не предсказанное внешнее происшествие. Допустимо:

```text
19:52 — Марс напротив твоего Нептуна, точный пик.
Может быть сложнее отличить ясное решение от первого импульса — проверь план.
```

Недопустимо:

```text
19:52 — ты поссоришься с партнёром.
```

### 2.2. Дневной якорь

Фактор получает роль `anchor_today`, если в часовом поясе пользователя для
выбранной даты выполняется хотя бы одно из условий:

- `exact_at` попадает внутрь локального дня;
- `active_from` попадает внутрь локального дня и событие действительно имеет
  смысл «входит в действие»;
- действующий DayDelta/canon помечает физический фактор как новый или пиковый
  именно в эту дату.

Один только высокий `strength`, малый `orb` или активность на протяжении
нескольких дней не делает фактор событием «именно сегодня».

### 2.3. Поддерживающий фактор

`supporting` — активный фактор, который связан с дневным якорем общей
персональной точкой либо общей узкой темой и усиливает объяснение, но сам не
обязан начинаться или достигать пика сегодня.

### 2.4. Фон

`background` — длительный период: фирдар, профекция, return/progression или
долгий транзит без дневного пика. Фон объясняет, **почему сегодняшний импульс
важен в текущем периоде**, но не номинирует сферу и не создаёт схождение сам по
себе.

Годовой фирдар может оставаться одним и тем же сотни дней. Это нормально в
расчёте и ненормально как ежедневно повторяемая новость.

### 2.5. Схождение

`convergence_today` существует только когда:

- после canonical dedup есть минимум два независимых физических фактора;
- минимум один из них — `anchor_today`;
- факторы связаны общей персональной точкой **или** одной узкой theme-group;
- при связи только через theme-group у факторов есть минимум одна общая
  продуктовая сфера;
- совпадение только по широкой сфере («оба про работу») недостаточно;
- один аспект, пришедший одновременно как signal и activation, считается один
  раз;
- две проекции одного фактора в разные technical/product spheres считаются
  одним фактором.

Наличие всех трёх горизонтов повышает объяснительную полноту, но не является
обязательным. Честное схождение может состоять из двух факторов; три слоя без
дневного якоря схождением не являются.

### 2.6. Одиночный импульс

`single_impulse` — один честный дневной якорь без второго связанного фактора.
Он показывается как событие дня, но над ним нельзя писать «Что сошлось».

---

## 3. Состояния продукта

Backend обязан выбрать ровно одно состояние:

| State | Условие | Что разрешено показывать |
|---|---|---|
| `convergence_today` | Есть хотя бы одно валидное схождение | «Что сошлось именно сегодня», события, 1–3 featured spheres |
| `single_impulses` | Есть дневные события, но нет общего сюжета | «События дня», без заявления о схождении |
| `background_only` | Есть только длительный/текущий фон | Короткий «Фон периода», без слова «сегодня сошлось» |
| `no_accent` | Расчёт успешен, выраженного акцента нет | Короткое честное neutral-состояние либо отсутствие блока |
| `unavailable` | Расчёт/контракт неполон или невалиден | «Не удалось рассчитать», retry; не подменять `no_accent` |

Нормативные тексты состояния:

```text
convergence_today: Что сошлось именно сегодня
single_impulses:   События дня
background_only:  Фон текущего периода
no_accent:         Сегодня нет выраженного схождения нескольких факторов.
unavailable:       Не удалось рассчитать акценты дня. Попробуй обновить позже.
```

Фраза `no_accent` не должна занимать большую hero-карточку. Окончательную
подачу решает дизайн-модель.

---

## 4. Детерминированный конвейер

### 4.1. Вход

Для v1 достаточно уже существующих данных:

- canonical factor ledger после signal↔activation dedup;
- `ActivationLayer` с `id`, technique/family, source/target, aspect/orb,
  strength/polarity, `active_from`, `exact_at`, `active_until`, `phase`;
- DayDelta для различения `new_today|peak|background`;
- corrected valence assessments 12 продуктовых сфер;
- horizon/theme mapping и product-sphere projection;
- профильный IANA timezone пользователя.

**Sidecar v1 менять и пересчитывать по новому алгоритму не требуется.** Он уже
возвращает timing для аспектных activation. Записи без `exact_at`, например
часть transit-in-house, не получают выдуманное время и не входят в timed
events. Точный момент ingress для них — отдельное возможное улучшение sidecar,
не blocker этой версии.

### 4.2. Нормализованный TodayFactor

API строит внутренний immutable object:

```python
class TodayFactor:
    factor_id: str                 # canonical physical identity
    activation_ids: tuple[str, ...]
    technique: str
    technique_family: str
    source_key: str | None
    target_key: str | None
    theme_keys: tuple[str, ...]
    product_spheres: tuple[str, ...]
    polarity: str
    strength: float
    salience: float
    active_from: datetime | date | None
    exact_at: datetime | date | None
    active_until: datetime | date | None
    phase: str | None
    temporal_role: Literal[
        "anchor_today", "supporting", "background", "unrelated"
    ]
```

`factor_id`, valence, salience, timing и sphere mapping не принадлежат LLM.

### 4.3. Группировка в сюжет

1. Применить существующий canonical physical dedup.
2. Рассчитать локальные границы выбранной даты `[00:00, 24:00)` по IANA
   timezone пользователя, затем классифицировать timing.
3. Создать seed-группу для каждого `anchor_today`.
4. Добавлять фактор к seed, только если есть строгая связь:
   - тот же `target_key`; или
   - общая узкая `theme_key` и общая product sphere.
5. Один фактор может быть кандидатом нескольких групп, но после ranking входит
   только в одну public convergence — в наиболее связную.
6. Группа без второго независимого фактора остаётся `single_impulse`.
7. Длительный фон можно приложить только после образования группы и нельзя
   учитывать как дневной якорь.

### 4.4. Ranking без магических LLM-оценок

Eligible groups сортируются лексикографически:

1. точность даты: `exact_today` → `starts_today` → `delta_peak`;
2. число независимых факторов, capped at 3 для ranking volume bias;
3. число независимых technique families/horizons;
4. строгая связь по `target_key` выше связи только по theme;
5. сумма effective magnitude независимых факторов после существующего
   family reducer из canonical ledger;
6. стабильный tie-break: минимальный `factor_id`.

Не вводить скрытый LLM-score и не сортировать по длине/красоте текста.

### 4.5. Выбор featured spheres

Сферы получают relevance только из выбранных групп. В v1 запрещена новая
взвешенная формула с ещё одним набором магических коэффициентов. Используется
нормативный лексикографический порядок:

1. больше independent factor coverage;
2. больше anchor coverage;
3. выше effective salience;
4. выше confidence corrected valence;
5. canonical product key как стабильный tie-break.

Weighted relevance score можно вводить только отдельной версией canon с
boundary fixtures и no-drift сравнением; он не является зависимостью v1.

Public output содержит **0–3** featured spheres:

- `convergence_today`: максимум 3, только сферы выбранного схождения;
- `single_impulses`: featured spheres для блока «Что сошлось» отсутствуют;
- `background_only|no_accent|unavailable`: отсутствуют;
- полный список 12 сфер ниже остаётся в canonical order.

Это сохраняет пользу расчёта всех факторов и сфер: весь массив нужен, чтобы
дедуплицировать, сравнить, отвергнуть нерелевантное и честно выбрать акцент.
Ненужным является не расчёт 150 факторов, а отправка всех 150 в LLM и попытка
показать их пользователю одновременно.

---

## 5. Public API contract

Имена могут быть уточнены при OpenAPI-генерации, но семантика frozen:

```python
class TodayFocusEvent(CamelModel):
    id: str
    kind: Literal["exact", "starts", "peak", "building", "separating"]
    occurs_at: datetime | None       # UTC ISO instant, source of truth
    local_date: date
    timezone: str                    # IANA timezone used for classification
    precision: Literal["minute", "date", "window"]
    human_title: str                 # deterministic/canon-owned
    technical_title: str | None      # optional disclosure, no Transit_/Natal_
    meaning: str | None              # bounded validated copy
    source_activation_ids: list[str]

class TodayFeaturedSphere(CamelModel):
    key: ProductSphereKey
    relevance_rank: int
    state: Literal["convergence_today"]
    summary: str | None
    action: str | None
    convergence_id: str
    source_event_ids: list[str]
    source_activation_ids: list[str]

class TodayConvergence(CamelModel):
    id: str
    theme_key: str
    title: str
    summary: str | None
    independent_factor_count: int
    technique_families: list[str]
    source_activation_ids: list[str]

class TodayFocus(CamelModel):
    state: Literal[
        "convergence_today",
        "single_impulses",
        "background_only",
        "no_accent",
        "unavailable",
    ]
    convergence: TodayConvergence | None
    events: list[TodayFocusEvent]       # 0..3 public events
    featured_spheres: list[TodayFeaturedSphere]  # 0..3
    content_state: Literal["ready", "pending", "unavailable", "not_needed"]
```

Инварианты:

- `state != convergence_today` → `convergence is None` и
  `featured_spheres == []`;
- `events` сортируются по `occurs_at`, затем по stable `id`;
- `occurs_at` без timezone запрещён;
- `local_date` обязана совпадать с выбранной датой для `exact|starts|peak`;
- `building` с пиком завтра можно показывать только с явной формулировкой
  «пик завтра», а не как состоявшийся пик сегодня;
- public time выводится из `occurs_at + timezone`; сохранённая строка времени
  не является source of truth;
- `source_activation_ids` должны ссылаться на факторы payload/audit;
- пустой/невалидный LLM-текст не меняет state, события или ranking;
- timeout, provider error, невалидная schema либо провал claim validation →
  `content_state="unavailable"`; все LLM-owned поля атомарно равны `None`;
- `content_state="ready"` допустим только после полной проверки core batch;
- `content_state="pending"` допустим только при реально запущенной
  retryable-генерации, а не как бесконечный loading placeholder;
- `content_state="not_needed"` используется, когда состоянию не требуется
  LLM-интерпретация;
- `unavailable` не кешируется как `no_accent`.

При добавлении wire-полей обязательны:

- Pydantic/CamelModel → OpenAPI → generated TS/Zod;
- bump текущих `TODAY_V2_PAYLOAD_VERSION`, frontend contract version,
  content version и prompt version, если меняется LLM-input/output;
- новый cache identity не читает старый payload как current;
- frontend не пересчитывает convergence/ranking самостоятельно.

---

## 6. Текстовый контракт

### 6.1. Общий принцип

Текст идёт в порядке:

```text
один вывод → реальные события со временем → 0–3 сферы → одно действие
```

Не должно быть повторения одного аспекта в headline, `mainAdvice`, событии,
трёх сферах и девяти why-секциях разными словами.

### 6.2. Лимиты

| Элемент | Лимит |
|---|---|
| Заголовок схождения | до 64 символов, без точки |
| Summary схождения | 1–2 предложения, до 220 символов |
| События | максимум 3 |
| `human_title` события | до 72 символов |
| `meaning` события | 1 предложение, до 160 символов |
| Featured sphere summary | 1 предложение, до 140 символов |
| Featured sphere action | 1 императивная фраза, до 100 символов |
| Техническое объяснение | только disclosure, не в первом потоке |

Один и тот же смысл не может одновременно занимать summary и action.

### 6.3. Время

При `precision=minute` событие начинается со времени пользователя:

```text
19:52 — точный пик
00:49 — точный пик
Пик завтра в 00:49
Пик прошёл в 00:55, влияние ослабевает
```

Правила:

- использовать 24-часовой формат локали ru-RU;
- не писать «сегодня», если `occurs_at` после конвертации попадает в другую
  локальную дату;
- при date-only precision не выдумывать часы;
- при window precision писать интервал или «в течение дня»;
- timezone может быть показан в disclosure; расчёт всегда хранит IANA zone;
- переход через полночь и DST покрывается тестами.

### 6.4. Тон

- На «ты», коротко и конкретно.
- Чётко разделять факт расчёта и возможное проявление в жизни.
- Для проявления использовать «может», «вероятнее», «обрати внимание».
- Не использовать фатализм, диагнозы, финансовые гарантии или обещание
  поступков другого человека.
- В основном тексте запрещены `Transit_`, `Natal_`, raw identifiers, орбисы и
  машинные theme keys.
- Астротермин допустим в коротком technical title только с человеческим
  пояснением и без машинных префиксов.
- Долгий фон формулируется как «контекст периода», а не как новое событие.

### 6.5. Примеры на обезличенном live-кейсе владельца

Примеры ниже — copy-эталон и canary, а не обещание окончательной визуальной
композиции.

Для 28 июля 2026, Europe/Moscow:

```text
События дня

13:31 — Луна в напряжении с твоим Плутоном, точный пик.
Реакция может быть глубже обычного — не принимай её за окончательное решение.

19:52 — Марс напротив твоего Нептуна, точный пик.
Перед действием проверь факты: импульс сегодня легче спутать с ясным планом.
```

Факторы с пиком 29 июля около `00:49–00:55` нельзя назвать пиком 28 июля.
Допустимо: «к вечеру тема набирает силу; пик завтра около 00:49».

Для 29 июля 2026, Europe/Moscow:

```text
Что сошлось именно сегодня

Вечером несколько факторов одновременно задевают тему личного темпа и
самоощущения. Оставь запас между первой реакцией и решением.

19:24 — Луна в напряжении с твоим Солнцем, точный пик.
19:40 — Луна напротив твоей Луны, точный пик.
```

Длительный фирдар Солнца может объяснять контекст этой темы, но не должен
каждый день выводиться как отдельное событие «сегодня».

### 6.6. Ошибка LLM и запрет fallback-копирайтинга

Шаблонные fallback-тексты запрещены. При timeout, provider error, пустом
ответе, невалидной JSON/schema или провале claim validation:

```json
{
  "contentState": "unavailable",
  "convergence": {
    "summary": null
  },
  "events": [
    {"meaning": null}
  ],
  "featuredSpheres": [
    {"summary": null, "action": null}
  ]
}
```

UI показывает отдельное честное status-сообщение:

```text
Персональный разбор пока не готов
```

Это сообщение принадлежит состоянию интерфейса и не записывается вместо
LLM-полей. Запрещены подстановки вида «Ваш персональный разбор дня», «Данные
временно недоступны», «Будь внимательнее» или иная универсальная
интерпретация, не полученная и не проверенная для этой даты.

Правило действует на **все** LLM-owned поля Today, включая временно
сохраняемые legacy-поля. При переходном контракте они становятся nullable:

```text
headline
reading
notes
daySummary.mainAdvice
concreteAdvice.rows[*].details.story
concreteAdvice.rows[*].details.advice
planet interpretations
LLM-generated why/meaning/summary/action
```

При неуспешном core batch эти поля/контейнеры равны `null`, а не пустой строке,
не массиву из fallback-абзаца и не старому закэшированному тексту под новой
cache identity. Нельзя выставить `contentState="ready"` по наличию только
одного удачного legacy-поля.

Проверенные расчётные поля остаются доступны:

- product state и наличие convergence;
- время и technical/human title события;
- выбранные sphere keys и provenance;
- valence/verdict и остальные deterministic facts.

Важно различать два случая:

- `state="unavailable"` — не удалось получить или проверить сам расчёт;
- `contentState="unavailable"` — расчёт валиден, но персональная
  LLM-интерпретация не готова.

Core LLM batch атомарен: частично валидный ответ не публикуется кусками. При
провале хотя бы одного обязательного поля все LLM-owned поля этого core batch
становятся `null`, результат получает `contentState="unavailable"` и
планируется на повторную генерацию.

---

## 7. Граница LLM

### 7.1. LLM не владеет

- наличием/отсутствием схождения;
- временем и фазой события;
- связью факторов и canonical dedup;
- выбором, числом и ranking featured spheres;
- valence, verdict, confidence, counts;
- названиями рассчитанных технических фактов;
- решением `no_accent|unavailable`.

### 7.2. LLM может владеть

Только компактной формулировкой уже рассчитанного результата:

- `convergence.summary`;
- `event.meaning` для максимум трёх событий;
- `summary + action` для максимум трёх featured spheres.

Все поля проходят schema, claim validation, banned vocabulary и provenance
check. Отказ LLM даёт `contentState="unavailable"` и `null` во всех LLM-owned
полях. Детерминированные факты сохраняются, но сервер не сочиняет вместо
модели универсальную интерпретацию.

### 7.3. Целевой вызов

Foreground/pregen core — **не более одного structured-output вызова**:

```json
{
  "convergence_summary": "...",
  "event_meanings": {"event-id": "..."},
  "featured_spheres": {
    "work": {"summary": "...", "action": "..."}
  }
}
```

Input содержит только выбранный compact evidence pack:

- до 3 public events;
- до 3 background/supporting factors;
- до 3 featured spheres;
- уже рассчитанные state/valence/timing labels;
- stable IDs для проверки claims.

Все остальные 12-сферные подробности генерируются лениво при открытии сферы
или заменяются детерминированным copy. `DayReading`, planet interpretations и
техническая расшифровка не входят в критический путь первого экрана.

Целевой budget core-call:

```text
input:              <= 3 000 tokens p95
max output:         <= 700 tokens
actual output:      <= 550 tokens p95
critical path calls: 0..1
```

Max tokens — потолок, а не доказательство фактической длины. Acceptance
смотрит на provider `usage.completion_tokens`, а не только на конфиг.

---

## 8. Диагноз текущих 75 секунд

### 8.1. Что доказано кодом и журналом

Текущий Today запускает пять верхнеуровневых branches, а interpretation branch
внутри делает ещё два LLM-вызова. Итого на cache miss возможно шесть provider
requests:

| Вызов | Текущий max output |
|---|---:|
| headline | 120 |
| reading | 500 по default settings |
| notes | 300 |
| why, 9 секций | 2 000 |
| 12 spheres + `day_main` | 2 400 |
| planet interpretations | 2 000 |
| **Сумма потолков** | **7 320** |

Параллельный запуск не складывает времена при нормальной работе provider, но
длиннейшая/очередная ветка определяет latency всей фазы. При nightly
concurrency=3 это до 18 одновременных внешних requests.

Live evidence 27–28 июля:

- обычные LLM-фазы завершались примерно за `5.7–10.3s`;
- один запуск достиг ровно `75 002ms`;
- завершено `4/5`, единственная timed-out branch — **`why`**;
- pregen для этого пользователя завершился примерно за `75.5s` и был
  напечатан как `ok`;
- соседние pregen-задачи имели длинный хвост примерно `46.7s` и `61.4s`;
- cache hits занимали примерно `20–146ms`;
- прямой расчёт sidecar на диагностическом кейсе был меньше секунды.

Следовательно, проблема действительно проявилась на 2000-token `why`, но
корневая причина шире, чем «nano медленный»:

1. `why` просит девять длинных секций, хотя блок collapsed и не нужен первому
   экрану.
2. Одновременно запускаются ещё пять генераций с суммарным потолком 5320
   output tokens.
3. Каждый request создаёт новый `httpx.AsyncClient`, поэтому connection pool
   между вызовами не переиспользуется.
4. Один provider attempt имеет timeout 60s, после чего возможен второй
   DeepSeek fallback; общий внешний retry-chain длиннее пользовательского
   бюджета.
5. Source default deadline сейчас 25s, комментарии обещают 10s, а live process
   логировал 75s. У дедлайна нет одного source of truth.
6. Pregen считает успехом любой неупавший payload, даже если важная LLM-ветка
   была отменена и закэширован fallback.
7. Нет per-call telemetry по input/output tokens, TTFT, upstream/provider,
   finish reason и длительности, поэтому без дополнительного измерения нельзя
   различить медленную генерацию, queueing, fallback и route/provider issue.

`openai/gpt-4.1-nano` официально позиционируется как low-latency модель. Это не
доказывает скорость маршрута через OpenRouter, но означает, что слепая замена
модели до измерения — неверный первый шаг.

### 8.2. Почему ночная предгенерация не является полным исправлением

Nightly job — это **materialization/cache pregen**, а не «прогрев модели».
Он делает первый пользовательский запрос быстрым только когда:

- нужный user/date действительно попал в выборку;
- cache identity совпадает с API runtime;
- provider/sidecar успешно отработали;
- `contentState` результата равен `ready|not_needed`;
- job закончился до первого открытия дня;
- смена timezone не изменила пользовательскую дату.

Pregen нужен, но не имеет права маскировать 75-секундный cold path и считать
`contentState="unavailable"` полноценным успехом.

---

## 9. Performance plan

### P0. Измерить до изменения модели

Добавить один canonical LLM client и per-call structured telemetry:

```text
provider
upstream_provider (если доступен безопасно)
model
operation = today_core|today_why_legacy|sphere_detail|day_reading|...
prompt_version
input_tokens
output_tokens
cached_input_tokens (если provider сообщает)
ttft_ms (если доступен)
duration_ms
http_status / finish_reason / timeout_stage
attempt_number / fallback_used
request_id_hash
```

Prompt, generated text, Telegram data, birth data, UUID и raw aspects в лог не
попадают. Новые event names сначала добавляются в logging registry.

Обязательный controlled benchmark на одном sanitized evidence pack:

1. legacy `why` single call;
2. новый compact core single call;
3. concurrency `1`, `2`, `3`;
4. минимум 20 прогонов на варианте;
5. p50/p95 total, TTFT, output tokens, tokens/sec, errors, fallback rate;
6. отдельно OpenRouter route/upstream; direct provider — только если уже есть
   разрешённый production-compatible путь.

### P1. Убрать лишнее из eager critical path

- удалить legacy nine-section `why` из foreground;
- объединить headline/mainAdvice/event meanings/featured copy в один core JSON;
- не генерировать все 12 sphere stories заранее;
- planet interpretations и полный DayReading — lazy/on-demand;
- `background_only|no_accent|unavailable` по возможности обслуживать без LLM;
- facts/timing/technical why строить только детерминированно.

### P2. Ограничить provider chain

- один конфигурационный source of truth для phase deadline;
- request-local absolute deadline передаётся каждому provider attempt;
- fallback разрешён только если остаётся достаточный budget;
- отдельные connect/read/pool timeouts вместо двух независимых 60s окон;
- один переиспользуемый async HTTP client с connection pooling;
- bounded global LLM concurrency для pregen;
- cancellation обязана закрывать/дожидаться child tasks без платных утечек.

### P3. Сделать pregen проверяемым

Pregen result для пары user/date:

```text
cache_hit
complete
unavailable_retryable
failed_retryable
failed_terminal
```

`cache_hit` в этой классификации означает cache hit с
`contentState=ready|not_needed`. Найденный factual cache с
`contentState=unavailable` классифицируется как `unavailable_retryable`, а не
как успешный hit.

Требования:

- `ok` только при валидном factual payload и `contentState=ready|not_needed`;
- factual payload с `contentState=unavailable` можно сохранить для
  доступности проверенных расчётных фактов, но все LLM-поля в нём `null`;
- `contentState=unavailable` всегда ставится в retry queue и не считается
  complete coverage либо успешным прогревом;
- повторный проход до пользовательского утра с jitter/backoff;
- итоговая метрика coverage по **локальной дате пользователя**;
- raw user UUID не печатается; используется существующий redacted/hash context;
- алерт на провал job, unavailable rate и incomplete coverage;
- cache identity включает model/prompt/content/contracts/flags/timezone date;
- rollout не удаляет старые cache rows, а перестаёт читать их как current.

### P4. Prompt caching и streaming — вторичные меры

- Общий статический prompt prefix ставить первым, динамический evidence — в
  конец, чтобы provider prompt caching мог совпасть по exact prefix.
- Не считать prompt caching главным лечением: в этом кейсе latency определяет
  длинный output/queue, а не только input parsing.
- Streaming улучшает perceived latency, но не заменяет сокращение output.
  Для Today предпочтительнее сразу вернуть фактический skeleton и отдельно
  завершить validated narrative, чем стримить непроверенный JSON.

### P5. Модель менять только по результату benchmark

Сравнение кандидатов проходит на одном schema/evidence и проверяет:

- p95 latency и fallback rate;
- factual/claim validation pass rate;
- валидность structured output;
- качество русского текста на golden set;
- стоимость complete payload, а не цену одного token.

Победитель фиксируется точным model ID/provider policy; плавающий alias без
canary не допускается.

---

## 10. Performance SLO и acceptance

| Контур | Требование |
|---|---|
| Cache hit `/api/day/{date}` | p95 ≤ 500ms |
| Sidecar + deterministic aggregation | p95 ≤ 2s на production-like host |
| Первый usable factual payload на cold miss | p95 ≤ 3s, hard ≤ 5s |
| Core LLM pregen | p95 ≤ 10s, hard deadline ≤ 15s |
| Foreground eager LLM calls | 0..1 |
| Core actual completion tokens | p95 ≤ 550, hard max ≤ 700 |
| Public events / featured spheres | 0..3 / 0..3 |
| Pregen complete coverage | ≥99% active user/dates к 06:00 user-local |
| `contentState=unavailable` после retry-window | <1% |
| Provider error/timeout | factual payload с LLM-полями `null`, не HTTP 500 и не 75s wait |

Если async narrative materialization ещё не реализована, промежуточный rollout
может иметь cold response hard ≤15s. Он не считается финальной приёмкой и не
возвращает 75s deadline.

---

## 11. Наблюдаемость

Новые рекомендованные события (точные имена утвердить через registry):

| Event | Поля |
|---|---|
| `day.convergence_built` | state, event_count, featured_count, independent_factor_count, duration_ms |
| `llm.call_completed` | operation, provider, model, token counts, duration, outcome, fallback_used |
| `day.pregen_item_completed` | cache state, content state, elapsed, retryable; user hash only |
| `day.pregen_batch_completed` | selected, complete, skipped, unavailable, failed, coverage |

Не логировать raw event titles/evidence: это персональные расчётные данные.

Dashboards:

- LLM p50/p95 по operation/model/provider;
- tokens/sec и output tokens;
- fallback/timeout/validation reject rate;
- pregen complete coverage по локальному часу;
- `convergence_today|single_impulses|background_only|no_accent|unavailable`
  distribution как диагностику, но не как квоту correctness;
- cache hit ratio и `contentState=unavailable` rate.

---

## 12. Тесты и canary

### 12.1. Pure unit

1. Один годовой фирдар → `background_only`, не convergence.
2. Один exact factor сегодня → `single_impulses`.
3. Два связанных фактора + exact today → `convergence_today`.
4. Два одновременных, но несвязанных exact factors → два события без
   convergence.
5. Signal+activation одного аспекта → один independent factor/event.
6. Один factor в трёх product spheres → independent count остаётся 1.
7. Фон присоединяется к уже созданному convergence, но не создаёт его.
8. Перестановка inputs не меняет state, ranking и IDs.
9. Ровно 0, 1, 2, 3 featured spheres; четвёртая не проходит public cap.
10. `exact_at=None` → часы не генерируются.
11. UTC instant до/после полуночи правильно попадает в Europe/Moscow и другую
    IANA zone.
12. DST gap/fold не создаёт невозможное или двойное public событие.
13. `unavailable` отличается от честного `no_accent`.
14. Timeout core batch → `contentState=unavailable`, все LLM-owned поля `null`,
    deterministic facts сохранены.
15. Один валидный и один невалидный элемент structured batch → атомарный
    reject всего LLM-content, без частичной публикации.
16. `contentState=unavailable` не засчитывается как pregen success и попадает
    в retry queue.

### 12.2. Contract/integration

- OpenAPI/TS/Zod parity;
- source IDs существуют в factor ledger/activation layer;
- frontend получает готовый ranking и не сортирует canonical `row.rank` как
  relevance;
- LLM mock не может изменить state/time/spheres;
- timeout каждого LLM operation возвращает factual payload;
- cache hit/miss дают одинаковые state/events/sphere IDs;
- cache version bump не читает старый payload как current;
- Today и pregen используют один exact runtime/flags/client contract;
- provider fallback не выходит за absolute request budget.

### 12.3. Sanitized live canaries

- `P-BASIL-2026-07-28`: дневные exact events отделены от пиков после полуночи;
- `P-BASIL-2026-07-29`: проверка вечерней связки вокруг Sun/Moon theme;
- дата только с длинным фирдаром;
- дата с двумя несвязанными быстрыми событиями;
- дата без точного timing;
- provider timeout, `contentState=unavailable`, null LLM fields и обязательный
  retry pregen.

Birth data, Telegram account и raw profile в fixture не сохраняются. Fixture
начинается с обезличенного normalized factor ledger.

### 12.4. UI semantic contract

Дизайн/реализация обязаны сохранить доступность и стабильные selectors:

```text
data-testid="today-focus"
data-state="convergence_today|single_impulses|background_only|no_accent|unavailable"
data-content-state="ready|pending|unavailable|not_needed"
data-testid="today-focus-event"
data-testid="today-featured-sphere"
data-event-kind="exact|starts|peak|building|separating"
```

- интерактивная строка — настоящий `button` или `a`;
- disclosure имеет `aria-expanded` и `aria-controls`;
- loading/pending — `role=status`/`aria-busy`;
- unavailable — `role=alert` только для реальной ошибки;
- dynamic LLM text не является единственной опорой теста.

---

## 13. Бриф для отдельной дизайн-модели

После утверждения backend/text contract отдельная модель должна добавить в
эту папку `22_TZ_W4_TODAY_CONVERGENCE_DESIGN.md` и, при необходимости,
prototype assets. Она не меняет смысловые правила этого документа.

### Вход дизайн-модели

- `TodayFocus` contract из §5;
- пять product states из §3;
- строгие текстовые лимиты из §6;
- variable cardinality: 0–3 events и 0–3 featured spheres;
- сохранённые 12 сфер ниже;
- existing Today visual system и semantic/test contract;
- mobile-first Telegram WebApp, затем desktop.

### Что должна решить дизайн-модель

- визуальную иерархию вывода, времени, событий, сфер и CTA;
- как различить «реальное рассчитанное событие» и «возможное проявление»;
- как показать время так, чтобы оно считывалось быстрее текста;
- как аккуратно показать 0, 1, 2 и 3 события без пустых placeholders;
- где живёт technical disclosure с аспектом/provenance;
- как выглядит `pending|unavailable`, не создавая длинного spinner;
- переход из featured sphere в существующий список/модалку 12 сфер;
- responsive, dark mode, focus, reduced motion и длинные локализованные строки.

### Обязательные дизайн-артефакты

1. Mobile `390×844`: все пять states.
2. Mobile варианты 0/1/2/3 events и 0/1/2/3 spheres.
3. Desktop вариант.
4. Technical disclosure open/closed.
5. `ready|pending|unavailable|not_needed` content states.
6. Событие около полуночи с текстом «пик завтра».
7. Accessibility annotation и mapping на test IDs.
8. Короткий click-flow от featured sphere к полным 12 сферам.

### Запреты для дизайн-модели

- нельзя всегда дорисовывать три карточки ради симметрии;
- нельзя прятать время в длинном абзаце;
- нельзя превращать фон периода в событие дня;
- нельзя выводить технический жаргон в основной пользовательский поток;
- нельзя возвращать девять секций «Почему так у меня»;
- нельзя маскировать `contentState=unavailable` универсальным прогнозом;
- нельзя менять ranking на клиенте;
- нельзя использовать цвет как единственный носитель состояния;
- нельзя начинать production-компоненты до приёмки дизайн-артефактов.

---

## 14. План реализации

### Slice A — telemetry и benchmark

- унифицировать LLM-client boundary;
- добавить per-call metrics/usage;
- зафиксировать baseline legacy why и concurrency curve;
- привести deadline/comment/runtime к одному контракту.

### Slice B — deterministic convergence/events

- новый pure builder/presenter с GRACE contracts;
- схемы/OpenAPI/contracts/cache versions;
- unit и sanitized canaries;
- sidecar не менять.

### Slice C — compact LLM core

- один schema-bound call;
- удалить eager legacy why/12-sphere/planet text из первого экрана;
- absolute budget и честный `contentState=unavailable` без fallback-текста;
- quality/golden evaluation.

### Slice D — pregen reliability

- quality-aware result states;
- bounded concurrency, retry и coverage metric;
- user-local completion SLO;
- fail-safe factual cache.

### Slice E — design handoff

- отдельная дизайн-модель выпускает §13 artifacts;
- owner принимает 0/1/2/3 и error/content-unavailable states;
- только после этого пишется frontend implementation TZ.

### Slice F — frontend/rollout

- semantic/test contract;
- feature flag + dual read compatibility;
- dev canaries 28/29 July;
- staged production rollout и rollback по cache identity/flag.

---

## 15. Merge-blocking gates

| Gate | Evidence |
|---|---|
| Semantics | Background-only и unrelated impulses не называются convergence |
| Timing | UTC→user timezone boundary/DST tests, no invented minute |
| Dedup | Один physical factor не размножается source/sphere projection |
| Ranking | 0–3 backend-owned featured spheres, permutation stable |
| LLM boundary | Request spy: LLM не владеет facts/time/state/ranking |
| Text | Character limits, banned/fatalism validator, no repeated portянка |
| Latency | Baseline + post-change p50/p95/token benchmark |
| Failure | Provider/validation failure → factual payload, `contentState=unavailable`, все LLM-поля `null` |
| Pregen | Complete/unavailable разделены; unavailable не считается прогревом, обязательно retry; ≥99% local-morning coverage |
| Cache | Versioned miss/hit parity, old payload not current |
| Contracts | OpenAPI → generated TS/Zod clean |
| UI | Five states + 0/1/2/3 visual/semantic tests |
| Privacy | No TG username, UUID, birth data or raw evidence in logs/fixtures |

Любой провал factual provenance, локальной даты события или hard latency
deadline — merge blocker. Красивый текст не компенсирует неверный факт.

---

## 16. Rollback

- Один server-side flag отключает новый `TodayFocus` selection и compact LLM
  path вместе; нельзя оставить новый текст на старом ranking.
- Previous/current cache identities читаются совместимым SHA, но не смешиваются.
- Rollback не удаляет cache rows и не меняет sidecar.
- При аварии factual Today/12 spheres остаются доступны; новый focus блок
  скрывается или получает `unavailable`, без возврата 75-секундного legacy why.

---

## 17. Основания для performance-решений

- OpenAI рекомендует в первую очередь сокращать output tokens: генерация
  результата обычно является главным источником latency; также рекомендуются
  fewer requests, parallelization независимых задач, streaming для perceived
  latency и отказ от LLM там, где достаточно детерминированного кода:
  <https://developers.openai.com/api/docs/guides/latency-optimization>
- Prompt caching помогает при совпадающем статическом prefix, но не заменяет
  сокращение длинного output:
  <https://developers.openai.com/api/docs/guides/prompt-caching>
- Текущая configured модель GPT-4.1 nano описана как low-latency модель без
  reasoning; скорость конкретного OpenRouter route всё равно должна быть
  доказана нашим benchmark:
  <https://developers.openai.com/api/docs/models/gpt-4.1-nano>
