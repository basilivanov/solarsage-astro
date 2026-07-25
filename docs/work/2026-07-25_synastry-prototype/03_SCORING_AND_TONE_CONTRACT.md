# Синастрия — scoring и tone contract v1

Статус: нормативное приложение к `01_TZ_REACT_ADAPTATION.md`.

Этот файл закрывает свободу исполнителя в deterministic-части MVP. Любое
изменение чисел ниже требует `CALCULATION_VERSION` bump, новых fixtures и
явного review; LLM не вычисляет и не корректирует ни одно из этих полей.

## 1. Граница расчётного слоя

Sidecar владеет только астрономическими фактами:

- положениями планет и доступных углов;
- межкарточными аспектами и орбисами;
- precision-флагами партнёрской карты.

API-модуль `M-SYNASTRY-SCORING` владеет:

- tone каждого аспекта;
- confidence и признаком `excluded_from_score`;
- итоговым score/status/counts;
- четырьмя sphere scores.

`applying` в cross-natal contract не входит: две карты построены для разных
моментов рождения, поэтому у поля нет однозначной временной семантики.

## 2. Допустимые факторы и орбисы

V1 использует Солнце–Плутон и доступный ASC каждой стороны. Хирон, Лилит,
лунные узлы, MC и астероиды в MVP не входят.

Для каждой направленной пары `owner body → partner body` выбирается не более
одного ближайшего аспекта:

| Aspect | Exact angle | Maximum orb |
|---|---:|---:|
| conjunction | 0° | 8° |
| opposition | 180° | 8° |
| square | 90° | 7° |
| trine | 120° | 7° |
| sextile | 60° | 5° |
| quincunx | 150° | 3° |

При равной дистанции выигрывает аспект с меньшим maximum orb, затем порядок
таблицы выше. Stable ID:

```text
owner-<body>__partner-<body>__<aspect>
```

## 3. Tone mapping

### 3.1. Базовая таблица

| Aspect | Default tone |
|---|---|
| conjunction | mixed |
| trine | supportive |
| sextile | supportive |
| square | tense |
| opposition | tense |
| quincunx | mixed |

### 3.2. V1 overrides

Пара нормализуется без учёта порядка сторон только для выбора tone. Направление
owner/partner в публичном аспекте сохраняется.

| Normalized pair | Aspect | Tone |
|---|---|---|
| Sun–Moon | conjunction | supportive |
| Moon–Venus | conjunction | supportive |
| Venus–Mars | conjunction | supportive |
| Sun–Jupiter | conjunction | supportive |
| Venus–Jupiter | conjunction | supportive |
| Sun–ASC | conjunction | supportive |
| Moon–Saturn | conjunction | tense |
| Sun–Saturn | conjunction | tense |
| Mars–Saturn | conjunction | tense |
| Mars–Pluto | conjunction | tense |
| Venus–Pluto | conjunction | tense |
| Venus–Uranus | square, opposition | mixed |
| Venus–Neptune | square, opposition | mixed |

Первое совпадение override побеждает базовую таблицу. Ретроградность, пол,
relation type и LLM-текст tone не меняют.

## 4. Численная формула

### 4.1. Константы

Tone value:

```text
supportive = 1.00
mixed      = 0.55
tense      = 0.15
```

Aspect importance:

```text
conjunction = 1.00
opposition  = 1.00
square      = 0.95
trine       = 0.90
sextile     = 0.75
quincunx    = 0.65
```

Body importance:

```text
Sun, Moon                    = 1.25
Mercury, Venus, Mars         = 1.15
ASC                          = 1.10
Jupiter, Saturn              = 1.00
Uranus, Neptune, Pluto       = 0.85
```

Confidence multiplier:

```text
high   = 1.00
medium = 0.65
low    = 0.00
```

Confidence определяется до scoring:

- `low`: аспект содержит partner Moon при `birth_time_precision=unknown`;
- `high`: остальные аспекты с `orb / maximum_orb <= 0.50`;
- `medium`: остальные аспекты внутри допустимого орбиса.

### 4.2. Вес аспекта

Для аспекта `a`:

```text
orb_ratio(a) = clamp(orb_degrees / maximum_orb, 0, 1)
orb_decay(a) = 0.25 + 0.75 × (1 - orb_ratio(a))²
pair_importance(a) = sqrt(owner_body_weight × partner_body_weight)

effective_weight(a) =
  aspect_importance
  × pair_importance
  × orb_decay
  × confidence_multiplier
```

При `confidence=low` аспект остаётся видимым, получает
`excluded_from_score=true`, но не входит в denominator и counts.

### 4.3. Итог

```text
raw = Σ(effective_weight × tone_value) / Σ(effective_weight)
score = clamp(round_half_up(raw × 100), 0, 100)
```

Минимум — три аспекта с ненулевым effective weight. Если их меньше, отчёт не
получает искусственный score: generation завершается кодом
`INSUFFICIENT_SCORING_DATA`, кредит возвращается.

Status:

```text
good: score >= 78
mid:  45 <= score < 78
bad:  score < 45
```

`counts.good|mid|bad` считает только аспекты с ненулевым effective weight и
маппит `supportive→good`, `mixed→mid`, `tense→bad`. Для UI дополнительно
возвращаются `visible_aspect_count` и `excluded_aspect_count`.

## 5. Sphere scores

Сфера получает аспект, если хотя бы один endpoint входит в её body set:

| Sphere | Body set |
|---|---|
| closeness | Moon, Venus, Mars, Pluto, ASC |
| communication | Mercury, Moon, Jupiter, Uranus |
| home | Moon, Venus, Mars, Saturn, ASC |
| work_money | Mercury, Venus, Mars, Jupiter, Saturn |

Внутри сферы применяется та же формула. При менее чем двух ненулевых факторах
`score=null`, `tone=null`, UI показывает «Недостаточно данных», а LLM не
получает числовой score этой сферы.

## 6. Unknown-time invariants

- Sidecar игнорирует присланное время и всегда использует `12:00` в локальном
  IANA timezone партнёра.
- Partner Moon aspects видимы, но всегда `confidence=low`, weight=0.
- Partner ASC и partner houses отсутствуют.
- Owner ASC и owner houses остаются доступны из `NatalContextService`.
- Замена `birth_time` на `00:00`, `12:00`, `23:59` при precision=`unknown` не
  меняет ни один scored aspect, counts, sphere score и общий score.

## 7. Golden и trap fixtures

### 7.1. Pure scoring fixtures

На aggregation boundary с одинаковыми effective weights:

| Fixture | Tones | Expected score/status |
|---|---|---|
| all_supportive | 3 × supportive | 100 / good |
| all_mixed | 3 × mixed | 55 / mid |
| all_tense | 3 × tense | 15 / bad |
| balanced | 2 supportive + mixed + tense | 68 / mid |

Отдельные boundary tests обязательны для 44/45/77/78, round-half-up, max orb,
zero denominator и unknown-Moon exclusion.

### 7.2. Prototype data

Максим≈89, Ирина≈78, Кирилл≈61 и Денис≈24 — visual copy targets, не engine
goldens. Прототип содержит только часть аспектов, а counts описывают более
широкий невидимый набор; полного owner birth input там нет. Подгонять formula
под эти четыре числа запрещено.

Visible prototype aspects используются только как tone-mapping fixtures:

- `Venus square Uranus → mixed`;
- `Mercury square Mercury → tense`;
- `Mars conjunction Venus → supportive`;
- `Saturn quincunx Sun → mixed`;
- `Saturn square Moon → tense`.

### 7.3. Sidecar integration inputs

Exact fixture:

```yaml
owner: 1993-01-07 10:33, 41.4689, 69.5822, Asia/Tashkent
partner: 1987-09-09 08:15, 55.7558, 37.6173, Europe/Moscow
precision: exact
```

Unknown fixture:

```yaml
owner: 1993-01-07 10:33, 41.4689, 69.5822, Asia/Tashkent
partner: 1990-04-03, 58.0105, 56.2502, Asia/Yekaterinburg
precision: unknown
```

Первый реализующий commit обязан сохранить sidecar response snapshots для
этих входов и доказать unknown-time invariants. Snapshot фиксирует факты, но
не заменяет property tests формулы.

## 8. Versioning

Начальные значения:

```text
calculation_version = synastry-calc/v1
report_schema_version = synastry-report/v1
prompt_version = synastry-prompt/v1
```

Tone table, weights, orbs, sphere membership и rounding относятся к
`calculation_version`. Narrative schema/system prompt относятся к
`prompt_version`. Breaking wire shape требует нового `report_schema_version`.
