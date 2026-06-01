---
id: doc-04-solarsage
status: active
wave: none
last_review: 2026-05-25
---
# 04. SolarSage, нормализация, скоринг и кэширование

> **Addendum v1.1 (2026-05-25).** Алгоритмический рерайт скоринга
> (Activation Layer + Convergence Bonus + канонизация SPHERES /
> dignities / aspect-rules) выделен в отдельную волну
> `W-SOLARSAGE-ALGO` и описан в `docs/14_SolarSage_scoring_rewrite_TZ.md`.
>
> Этот документ остаётся каноном **формы** пайплайна
> (`raw → AstroSignal[] → SemanticLayer → LLM → TodayPayload`) и
> кэширования. После выезда W-SOLARSAGE-ALGO в § 5 («Salience»)
> формула остаётся валидной, но приобретает аддитивный convergence
> bonus, считаемый из нового слоя `derived.activation_layer`. Wire
> shape (`TodayPayload`, `WhyThisHappens`, `TopFlag`) при этом не
> меняется — улучшения качества проявляются в существующих полях.

## Роль документа

Фиксирует рабочую модель v1 для расчётного слоя Today: как из максимального вывода SolarSage и дополнительных расчётов собрать нормализованные сигналы, скоринг, semantic layer, данные для LLM и TodayPayload.

## Главный принцип

**Считаем максимально много, но показываем только то, что нужно продукту.**

SolarSage output не должен напрямую попадать на фронт. Фронт получает стабильный продуктовый контракт.

## Пайплайн

```text
SolarSage raw calculations
        ↓
NatalDeepSnapshot
        ↓
PeriodSnapshot
        ↓
DailySnapshot
        ↓
Normalized AstroSignal[]
        ↓
Scoring / ranking
        ↓
SemanticLayer
        ↓
LLM interpretation
        ↓
TodayPayload
        ↓
Frontend
```

## 1. NatalDeepSnapshot

Глубокий натальный расчёт пользователя. Считается при создании профиля и пересчитывается при изменении даты, времени или места рождения.

Входит максимум:

- натальные планеты, знаки, градусы, дома, скорости, ретроградность;
- дома и углы: ASC / DSC / MC / IC;
- натальные аспекты;
- dignity score, rulership, exaltation, detriment, fall;
- sect;
- bonification / maltreatment;
- dispositors, final dispositor;
- lots;
- bounds / terms / faces;
- antiscia;
- fixed stars;
- midpoints;
- aspect patterns;
- derived natal scores.

Используется как карта чувствительных точек, качества планет, сильных сфер, натальных паттернов и управителей. Не является daily forecast сам по себе.

## 2. PeriodSnapshot

Фон периода, который объясняет, почему тема вообще сейчас живая.

Входит:

- solar return;
- annual / monthly profection;
- firdaria;
- secondary progressions;
- solar arc;
- primary / symbolic directions;
- long-term transits;
- активные дома и управители;
- основные темы периода;
- фоновые напряжения и поддержки.

Используется для объяснения, почему дневной триггер важен именно сейчас.

## 3. DailySnapshot

Расчёт конкретного дня.

Входит:

- положение, дом, знак и фаза Луны;
- Луна без курса;
- смена знака Луны;
- новолуние / полнолуние;
- затмения и дни вокруг;
- retro statuses;
- stations;
- ingress;
- daily transits;
- точные транзиты к наталу;
- транзиты к углам;
- транзиты к управителям активных домов;
- активация lots, midpoints, sensitive points;
- daily house focus.

## 4. Normalized AstroSignal[]

Все факторы из разных техник приводятся к одному формату.

```ts
export type AstroSignal = {
  id: string
  source:
    | "daily_sky"
    | "transit_to_natal"
    | "solar_return"
    | "profection"
    | "progression"
    | "direction"
    | "solar_arc"
    | "natal_baseline"
    | "lot_activation"
    | "midpoint_activation"
    | "fixed_star_activation"
    | "quality_modifier"
  role:
    | "trigger"
    | "amplifier"
    | "softener"
    | "background"
    | "constraint"
    | "opportunity"
  planets: string[]
  houses: number[]
  angles?: Array<"ASC" | "DSC" | "MC" | "IC">
  aspect?: string
  orb?: number
  applying?: boolean
  phase?: "building_up" | "exact" | "releasing"
  salience: number
  tension: number
  support: number
  expression: number
  shadowRisk: number
  timeWindow?: { startsAt?: string; endsAt?: string; peakAt?: string }
  evidence: string[]
  humanMeaning: string
}
```

### Поля

- `source` — откуда сигнал.
- `role` — как он работает: trigger, amplifier, softener, background, constraint, opportunity.
- `salience` — важность.
- `tension` — трение/напряжение.
- `support` — поддержка/ресурс.
- `expression` — внешняя проявленность.
- `shadowRisk` — риск перекоса.
- `phase` — building_up / exact / releasing.

## 5. Salience

```ts
salience =
  layerWeight
  * objectWeight
  * aspectWeight
  * orbWeight
  * applyingWeight
  * houseWeight
  * personalRelevanceWeight
  * periodActivationWeight
```

Примерные веса:

- daily sky: `1.0`
- transit to natal: `2.0`
- transit to angle: `2.5`
- profection ruler activated: `2.2`
- solar return theme: `1.6`
- progression / direction: `2.0`
- natal baseline: `0.5`
- lots / midpoints / fixed stars: `0.8–1.5`, только при точной активации.

Повышают вес:

- точный орб;
- applying;
- exact today;
- касание угла;
- касание Солнца / Луны / ASC ruler;
- касание управителя года / месяца;
- связь с активным домом периода;
- повтор темы через несколько техник;
- попадание в 1 / 4 / 7 / 10 дома.

## 6. Tension / support

Нельзя считать «квадрат = плохо, трин = хорошо». Учитываем:

- природу планет;
- качество планет;
- dignity;
- sect;
- bonification / maltreatment;
- дом;
- фазу;
- связь с периодом.

Примеры:

- квадрат от Юпитера может давать рост, но с перегибом;
- трин от Сатурна может быть стабилизирующим;
- Марс на угле может давать силу и конфликт;
- сильный Меркурий может помочь собрать хаос в структуру.

## 7. Скоринг дня

```ts
supportScore = sum(signal.salience * signal.support)
frictionScore = sum(signal.salience * signal.tension)
intensityScore = supportScore + frictionScore
netScore = supportScore - frictionScore
shadowRisk = sum(signal.salience * signal.shadowRisk)
totalSalience = sum(signal.salience)
```

## 8. Ловушка среднего значения

Нельзя определять день только через `netScore`.

Если support +10 и friction +10, `netScore = 0`, но день не ровный. Это день высокой интенсивности / контраста.

Поэтому всегда учитываем `intensityScore`.

Внутренние типы:

- `high_contrast`;
- `intense`;
- `peak`;
- `transformational`.

Для 7-дневной ленты такие дни можно маппить в **напряжённый**, но в тексте объяснять, что это сильный и контрастный день.

## 9. Fallback для тихих дней

Если `totalSalience` ниже порога, нельзя натягивать слабый аспект на главную тему.

Тогда main theme строится вокруг:

- Луны;
- знака Луны;
- дома Луны;
- фазы Луны;
- базового дневного фона;
- мягкого period background.

```ts
if (totalSalience < threshold) {
  dayQuality = "quiet"
  mainThemeSource = "daily_sky"
}
```

## 10. Качество дня

Внутренние качества:

- `supportive`
- `steady`
- `quiet`
- `tense`
- `high_contrast`
- `intense`
- `peak`
- `releasing`

Пример правил:

```ts
if totalSalience < threshold:
  quality = "quiet"
else if intensityScore high and abs(netScore) low:
  quality = "high_contrast"
else if frictionScore > supportScore:
  quality = "tense"
else if supportScore > frictionScore:
  quality = "supportive"
else:
  quality = "steady"
```

## 11. Маппинг в 7-дневную ленту

В UI показываем только 3 статуса:

- **поддерживающий**
- **ровный**
- **напряжённый**

```ts
supportive -> поддерживающий
steady -> ровный
quiet -> ровный
tense -> напряжённый
high_contrast -> напряжённый
intense -> напряжённый
peak -> напряжённый
releasing -> ровный или напряжённый, по frictionScore
```

## 12. Main theme

Backend агрегирует сигналы по темам:

```ts
themes = {
  mind_communication: number,
  work_status: number,
  relationships: number,
  money_security: number,
  body_energy: number,
  home_family: number,
  inner_background: number,
  crisis_control: number,
  meaning_vector: number
}
```

Связи:

- Mercury + 3 house + retro → `mind_communication`;
- MC / 10 house / Saturn / Mars → `work_status`;
- Venus + 5 / 7 house → `relationships`;
- 2 house + Venus / Jupiter / Saturn → `money_security`;
- 1 / 6 house + Mars / Saturn / Moon → `body_energy`;
- 4 house / Moon → `home_family`;
- 8 house / Pluto / Mars / Saturn → `crisis_control`;
- 9 house / Jupiter / Neptune → `meaning_vector`;
- 12 house / Neptune / Saturn / Moon → `inner_background`.

Формула:

```text
main_theme = topTheme + topHouseAxis + topPlanetaryLayer
```

## 13. Верхние флаги

Кандидаты:

- Луна без курса;
- ретроградный Меркурий / Венера / Марс;
- station;
- затмение ±3 дня;
- новолуние / полнолуние;
- смена знака Луны;
- ingress медленной планеты;
- точный личный транзит;
- активный дом, если это practically важно.

Правила:

- максимум 4;
- лучше 3;
- флаг понятный;
- у каждого есть hint;
- флаг не превращается в весь why-блок.

## 14. SemanticLayer

```ts
export type SemanticLayer = {
  date: string
  dayQuality: string
  dayStatus: "supportive" | "steady" | "tense"
  mainTheme: { title: string; houses: number[]; planets: string[]; summary: string }
  topFlags: TopFlag[]
  dailyTriggers: AstroSignal[]
  personalActivations: AstroSignal[]
  periodBackground: AstroSignal[]
  amplifiers: AstroSignal[]
  softeners: AstroSignal[]
  manifestationZones: Array<{ house?: number; theme: string; description: string }>
  practicalDirection: string[]
}
```

## 15. Что отдаём в LLM

LLM не получает весь raw JSON.

Она получает structured context из 5 секций:

```
=== НАТАЛЬНАЯ КАРТА ===
- Солнце: Рак, 10 дом (120.5°)
- Луна: Дева, 1 дом (172.3°)
... (все планеты с домами, знаками, градусами)

=== ТОП-ТРАНЗИТЫ (по силе) ===
1. [сила 0.91] Солнце в 4 доме
2. [сила 0.78] Луна секстиль Венера (орб 1.2°)
... (топ-5, отсортированы по силе)

=== ГРУППИРОВКА ===
Планеты в домах: Солнце(4 дом), Меркурий(3 дом)
Аспекты: Луна-Венера (секстиль), Марс-Сатурн (квадрат)

=== СФЕРЫ ПО ВЛИЯНИЮ ===
- семья: сильное (балл 4)
- карьера: среднее (балл 2)

=== СЕМАНТИКА ===
Тема дня: День поддержки и гармонии
Ключевые слова: баланс, поток
```

LLM сама генерирует 9 структурированных секций WhyThisHappens:

| # | layer | Секция |
|---|-------|--------|
| 01 | `main_theme` | Главная тема дня |
| 02 | `daily_layer` | Быстрый слой дня |
| 03 | `personal_activation` | Почему задевает именно тебя |
| 04 | `period_background` | Фон периода |
| 05 | `amplifiers` | Что усиливает |
| 06 | `softeners` | Что смягчает |
| 07 | `manifestation_zones` | Через какие сферы (bullets) |
| 08 | `astrological_meaning` | Астрологический смысл |
| 09 | `practical_meaning` | Что значит практически (bullets) |

Промты: «ты»-форма, русские названия (Солнце, Луна, Меркурий...), запрет англицизмов.

**Fallback при падении LLM:**
OpenRouter → DeepSeek Flash → placeholder «Данные временно недоступны».
Все блоки остаются видимыми (не скрываются) — фронт всегда показывает заглушку вместо пустоты.

Нельзя наружу:

- supportScore;
- frictionScore;
- salience;
- shadowRisk;
- raw JSON;
- raw internal ranking.

## 16. Кэширование

Кэшируем по слоям:

1. **NatalDeepSnapshot** — пересчитывается при изменении рождения.
2. **PeriodSnapshot** — пересчитывается при изменении города дня рождения, соляра, периода, версии расчёта.
3. **DailySnapshot** — считается при первом открытии дня или заранее для недели.
4. **SemanticLayer** — normalized signals, scoring, main theme, flags, amplifiers, softeners.
5. **TodayPayload / LLM output** — кэшируется отдельно, чтобы не платить повторно.

## 17. Инвалидация

NatalDeepSnapshot инвалидируется при изменении даты/времени/места рождения.

PeriodSnapshot — при изменении города дня рождения, года соляра, версии расчёта периода.

DailySnapshot / SemanticLayer / TodayPayload — при изменении calculation/interpretation/prompt version, профиля, PeriodSnapshot или NatalDeepSnapshot.

## 18. Versioning

```ts
meta: {
  calculationVersion: string
  normalizationVersion: string
  scoringVersion: string
  interpretationVersion: string
  promptVersion: string
  contractVersion: string
}
```

Главный принцип: расчётные версии могут меняться, contractVersion должен быть максимально стабильным.

## Итоговая формула

```text
Day v1 = DailySky + PersonalActivations + PeriodBackground + NatalSensitivity + QualityModifiers
```

Расчётную модель можно менять, если сохраняется путь:

```text
Raw calculations → AstroSignal[] → SemanticLayer → LLM → TodayPayload
```
