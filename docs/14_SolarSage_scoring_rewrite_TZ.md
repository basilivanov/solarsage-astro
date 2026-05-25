---
id: doc-14-solarsage-scoring
status: planned
wave: W-SOLARSAGE-ALGO
last_review: 2026-05-25
---
# ТЗ: алгоритмический рерайт скоринга SolarSage (sphere_scores v2)

Версия: 0.1
Парный документ: `docs/11_SolarSage_rewrite_TZ.md` (инфраструктура — CLI → HTTP).
Этот ТЗ — про **алгоритм**, не про инфру. Они едут разными волнами.

## 0. Краткая причина существования

Текущий `apps/solarsage/collect_solarsage_western_deep.py` собирает богатейший
сырой пакет (профекция, прогрессии, solar arc, primary directions, фирдар,
лоты, миды, фикс-звёзды, варги). Но в финальный `derived.sphere_scores`
заходит **только натальная картинка + топ-40 major-аспектов**. Все
динамические техники остаются в `raw` и в скоринг сферы не складываются.

Следствие: продукт обещает «попадание в человека и в день», а движок
отвечает натальной плотностью. «Охуевание от точности» возникает только
когда несколько техник сходятся на одну планету / один дом — сейчас этой
конвергенции нет в формуле.

Параллельно в скрипте захардкожены три знаниевых слоя, которые должны
жить как данные, а не как код: SPHERES, `condition_factor`, отсечка
«топ-40 аспектов».

Этот ТЗ закрывает именно эти четыре пробела.

---

## 1. Что меняем (scope)

1. **Activation Layer** — новый промежуточный слой между `raw` и
   `derived.sphere_scores`. Сводит динамику (профекция, фирдар, solar return,
   solar arc, прогрессии, транзит target_date) в плоский список
   «активаций» по планетам / домам / лотам.
2. **Convergence Bonus** — отдельная функция, не множитель. Если на одну
   планету / один дом указывают ≥ 2 независимые техники — добавляется
   аддитивный бонус к salience сферы. Это и есть «откуда оно знает».
3. **Канонизация знаний.** SPHERES, `condition_factor`,
   бенефик/малефик-правила и порог отсечки аспектов выносятся из кода
   в `grace/canon/spheres.v1.yml`, `grace/canon/dignities.v1.yml`,
   `grace/canon/aspect_rules.v1.yml`. Скоринг читает их как данные.
4. **Threshold вместо top-40.** Аспекты отсекаются по
   `score_hint ≥ aspect_threshold` (значение — в `aspect_rules.v1.yml`),
   а не по фиксированному количеству.

**Out of scope** (отдельные ТЗ):
- HTTP-обёртка sidecar-а — doc 11.
- Кэширование `natal/period/daily/semantic/today` — doc 04, делается на
  стороне `apps/api`.
- LLM-промпт и пост-валидация текста — отдельная волна `W-LLM-CONTRACT`.

---

## 2. Activation Layer

### 2.1 Назначение

Один проход по `raw`, который для каждой натальной планеты и каждого
дома собирает список активирующих сигналов на target_date. Никаких
весов здесь не считается — только факт «эту планету/дом сейчас
подсвечивает такая-то техника».

### 2.2 Контракт

Добавляется в `derived` рядом с `sphere_scores`:

```jsonc
"derived": {
  "activation_layer": {
    "by_planet": {
      "MERCURY": [
        {
          "technique": "annual_profection",
          "kind": "lord_of_year",
          "evidence": "profected_house=3, lord=MERCURY",
          "active": true
        },
        {
          "technique": "transit_to_natal",
          "kind": "applying_aspect",
          "aspect": "SQUARE",
          "from": "SATURN",
          "orb": 1.42,
          "applying": true,
          "exact_at": "2026-04-16T11:23:00Z"
        },
        {
          "technique": "secondary_progression",
          "kind": "progressed_natal_orb",
          "orb": 0.9
        }
      ],
      "VENUS": [...]
    },
    "by_house": {
      "3": [
        { "technique": "annual_profection", "kind": "profected_house" },
        { "technique": "solar_return", "kind": "sr_planets_in_house",
          "planets": ["MARS"] }
      ]
    },
    "by_lot": {
      "FORTUNE": [
        { "technique": "transit_to_lot", "from": "JUPITER", "orb": 0.8 }
      ]
    }
  }
}
```

### 2.3 Источники активаций (минимум v2.0)

| Техника                | Что активируется                              |
|------------------------|-----------------------------------------------|
| `annual_profection`    | дом года, управитель года                     |
| `monthly_profection`   | дом месяца, управитель месяца                 |
| `firdar_major`         | планета мажорного периода                     |
| `firdar_minor`         | планета минорного периода                     |
| `solar_return`         | дом, в который попали SR-планеты; SR-MC/ASC   |
| `solar_arc`            | планеты в орбе ≤ 1° к натальным точкам        |
| `secondary_progression`| то же, орб ≤ 1°                               |
| `transit_to_natal`     | applying аспекты в орбе из `aspect_rules`     |
| `transit_to_lot`       | то же для главных лотов                       |
| `transit_to_angle`     | applying на ASC/DSC/MC/IC                     |
| `lunar_return`         | дом, в который попали LR-Луна и угловые       |
| `eclipse_window`       | планета/угол в орбе ≤ 3° к точке затмения    |

Список техник версионируется через ключ
`activation_layer_version: "al-1.0"`. Добавление новой техники без
обновления версии — нарушение канона.

---

## 3. Convergence Bonus

### 3.1 Принцип

`salience` сферы по-прежнему считается из натальных факторов (как
сейчас). Но добавляется аддитивный бонус, считаемый из
`activation_layer`:

```text
For each planet P involved in sphere S:
  n = unique techniques in activation_layer.by_planet[P]
  if n >= 2:
    bonus += convergence_curve(n) * sphere_weight_of(P, S)

For each house H listed in sphere S:
  n = unique techniques in activation_layer.by_house[H]
  if n >= 2:
    bonus += convergence_curve(n) * house_weight_of(H, S)

sphere_scores[S].salience = soft_cap(natal_salience + bonus, scale=6.0)
```

### 3.2 `convergence_curve(n)`

Sublinear, чтобы 5 техник не дали 5x бонусов:

```text
convergence_curve(n) =
  0       if n < 2
  0.40    if n == 2
  0.65    if n == 3
  0.80    if n == 4
  0.90    if n >= 5
```

Точные значения — в `grace/canon/aspect_rules.v1.yml` под ключом
`convergence_curve`.

### 3.3 Что **нельзя** делать

- Нельзя считать convergence через множитель — иначе 1 активация
  убивает сигнал, а 5 взрывают. Только аддитивный бонус.
- Нельзя засчитывать одну и ту же технику дважды (например, и
  `annual_profection`, и `monthly_profection` указывают на Меркурий —
  это одна семья «профекция», а не две техники). Семьи определены в
  `aspect_rules.v1.yml` под ключом `technique_families`.
- Нельзя пробрасывать convergence наружу через `TodayPayload` без
  пост-формулировки. На фронт это попадает только как human-readable
  строка в `WhyBlock`, а не как число.

### 3.4 Антидоминирование

После применения бонуса проверяется:

```text
if sphere_scores[S].salience > 0.65 * sum_all_salience:
    sphere_scores[S].salience = 0.65 * sum_all_salience
    sphere_scores[S].dominance_capped = true
```

Это защита от дня, в котором одна сфера съела всё внимание и LLM
получает «единственный сигнал».

---

## 4. Канонизация знаний

### 4.1 `grace/canon/spheres.v1.yml`

Сейчас в скрипте словарь `SPHERES` захардкожен. Переносим:

```yaml
schema_version: spheres.v1
spheres:
  thinking_speech_learning:
    title: "мысли · речь · учёба"
    houses: [3, 9]
    planets:
      MERCURY: 1.0
      JUPITER: 0.4
    lots:
      - SCIENCE
    weight_multipliers:
      angular_house_bonus: 1.2
      ruler_weight: 0.30
  relationships_marriage:
    houses: [7]
    planets:
      VENUS: 1.0
      MOON: 0.6
      SATURN: 0.4
    lots:
      - MARRIAGE
      - EROS
  ...
```

Скоринг читает этот файл при старте. Astrolog-консультант может
ревьюить отдельно от python.

### 4.2 `grace/canon/dignities.v1.yml`

Перенос `condition_factor` с magic-numbers:

```yaml
schema_version: dignities.v1
condition_factor:
  bounds: [0.45, 1.35]
  modifiers:
    - { planet: VENUS, sign: TAURUS,  delta: +0.25, reason: "domicile" }
    - { planet: VENUS, sign: PISCES,  delta: +0.20, reason: "exaltation" }
    - { planet: SATURN, sign: LEO,    delta: -0.15, reason: "detriment" }
    - { planet: MARS,   sign: CANCER, delta: -0.20, reason: "fall" }
    ...
  retrograde_penalty:
    MERCURY: -0.10
    VENUS:   -0.10
    MARS:    -0.05
```

### 4.3 `grace/canon/aspect_rules.v1.yml`

```yaml
schema_version: aspect_rules.v1
orb_profile_default:
  SUN:     8.0
  MOON:    8.0
  MERCURY: 6.0
  ...
aspect_weights:
  CONJUNCTION: 1.00
  OPPOSITION:  0.95
  TRINE:       0.85
  SQUARE:      0.85
  SEXTILE:     0.55
  SEMI_SEXTILE: 0.25
  QUINCUNX:     0.40
benefic_softening:
  square_or_opposition_with_benefic:
    tension_delta: +0.20
    ease_delta:    +0.15
  trine_or_sextile_with_malefic:
    ease_delta:    +0.20
    tension_delta: +0.15
aspect_threshold:
  major: 0.35    # любой major-аспект ниже отсекается
  minor: 0.55    # минорные строже
convergence_curve:
  2: 0.40
  3: 0.65
  4: 0.80
  5: 0.90
technique_families:
  profection: [annual_profection, monthly_profection]
  firdar:     [firdar_major, firdar_minor]
  progressive: [secondary_progression, solar_arc]
```

### 4.4 Loader

```
apps/solarsage/solarsage/canon/loader.py
  load_canon(name: str, version: str) -> dict
  validate_canon(payload, schema_path)  # jsonschema
```

При старте sidecar-а:

```python
SPHERES = load_canon("spheres", "v1")
DIGNITIES = load_canon("dignities", "v1")
ASPECT_RULES = load_canon("aspect_rules", "v1")
```

Если файл не валиден — sidecar **не стартует** (fail-loud, не fail-silent).

---

## 5. Threshold отсечки аспектов

Заменить:

```python
for aspect in major_aspects[:40]:
```

на:

```python
threshold = ASPECT_RULES["aspect_threshold"]["major"]
for aspect in major_aspects:
    if aspect["score_hint"] < threshold:
        continue
    ...
```

Это убирает риск «41-й аспект — exact-square Saturn-Pluto, и его никто
не увидел».

---

## 6. Версионирование

В ответе `/v1/natal` и `/v1/transits` (см. doc 11) добавляются
ключи:

```json
"meta": {
  "calculation_version": "ss-1.1.0",
  "scoring_version": "ss-scoring-2.0",
  "activation_layer_version": "al-1.0",
  "canon_versions": {
    "spheres":      "v1",
    "dignities":    "v1",
    "aspect_rules": "v1"
  }
}
```

`apps/api` хранит эти ключи в кэше. Любое расхождение — инвалидация
`semantic_layer` и `today_payload`. NatalDeepSnapshot инвалидируется
**только** при изменении `calculation_version` (натал не зависит от
скоринга).

---

## 7. Тестовый чек-лист (DoD)

- [ ] Перенос SPHERES / dignities / aspect_rules в `grace/canon/*.v1.yml`,
      jsonschema-валидация при старте, fail-loud при ошибке.
- [ ] Контракт `derived.activation_layer` присутствует в ответе и
      содержит ≥ 7 техник из таблицы §2.3.
- [ ] **Регрессионный тест на конвергенцию.** Натальный кейс «Меркурий
      ретро в 3-м доме» + год профекции 3-го дома + транзит Сатурна к
      Меркурию: `sphere_scores.thinking_speech_learning.salience` после
      бонуса ≥ 1.4 × pre-bonus salience и ≤ 2.0 ×.
- [ ] **Антидоминирование.** Кейс с пятью одновременными активациями на
      одну сферу: её доля ≤ 0.65 от `sum_all_salience`,
      `dominance_capped == true`.
- [ ] **Threshold.** Major-аспект с `score_hint = 0.34` не попадает в
      скоринг; `0.36` попадает.
- [ ] **Стабильность натала.** Если меняется только
      `activation_layer_version`, NatalDeepSnapshot хеш в `apps/api`
      **не меняется**.
- [ ] Снапшот-тест эталонного кейса (`tests/fixtures/vasiliy.json`):
      числа `sphere_scores` v2 совпадают с зафиксированной таблицей
      ±0.02.
- [ ] Бенч: добавление activation_layer и convergence-бонусов
      увеличивает время ответа `/v1/natal` < +10 %, `/v1/transits` <
      +20 %.

---

## 8. Миграционный план

1. Волна `W-SOLARSAGE-SVC` (doc 11) едет первой — нужен HTTP-каркас.
2. Внутри волны `W-SOLARSAGE-ALGO` (этот ТЗ):
   - 8.1. Канон-файлы + loader. Скоринг переписан на чтение из канона,
          результат **должен совпасть с pre-canon** (snapshot-тест на
          эталонном кейсе). Это шаг без изменения семантики.
   - 8.2. Activation Layer как чистый сборщик из raw, без подключения к
          скорингу. Контракт виден в ответе, но в `sphere_scores` не
          входит. Snapshot-числа всё ещё совпадают.
   - 8.3. Подключение convergence-бонуса. `scoring_version` → `2.0`.
          Snapshot-числа меняются — обновляются явно с подписью
          ревьюера в `grace/packets/W-SOLARSAGE-ALGO.md`.
   - 8.4. Антидоминирование + threshold. Финальный snapshot.
3. После каждого подшага гейт `pytest -q` + `solarsage` health должен
   быть зелёный.

---

## 9. Что не делаем в этом ТЗ

- Не трогаем varga / dasha / ashtakavarga (это отдельная астрологическая
  школа, для русского MVP не нужна).
- Не считаем «time-of-day peak» — это уже частично есть в
  `DailySnapshot.timeWindow`, доделается в `W-DAY-PEAKS`.
- Не вводим LLM-валидатор. Текст по-прежнему валидируется в `apps/api`,
  не в sidecar.
- Не меняем wire-контракт с фронтом (`TodayPayload`, `WhyThisHappens`).
  Все улучшения качества — в полях, которые уже существуют.
