> **СТАТУС: diagnostic / superseded.** Старый классификатор (`ablation_birthtime.py:85` использует `H.classify_day` до fix-list v1.5). Числа недействительны для финала; финальный пересчёт страт — `ablation_birthtime_v2.md` (готовится). Выводы по механизмам (sect-аномалия, time_sensitive killers, perf) остаются валидными.

# Birth-time strata (P0, master v1.4 §4.7): робастность фактов к неточному времени рождения

Данные: владелец (`basil_ivanov`), 81 день (2026-06-01..2026-08-20). Контрольные времена (local birth tz): buckets edges+middle (3 точки), unknown — каждые 4ч (6 точек), shifted — resample для фикстуры 9. Натальная карта пересчитывается на каждое контрольное время (sidecar get_natal + get_activation_layer per time, как прод для одного времени). Правило публичности: факт идентичен (semantic_key + polarity + сферы) на ВСЕХ контрольных временах диапазона; иначе time_sensitive → исключён. Якорь засчитывается, только если факт — якорь на всех контрольных временах (консервативно). Орб для значимости — максимум по контрольным временам. Для bucket/unknown дома/ASC/лоты (target_type ∈ {house, angle, lot}) не публичны — жёсткое правило поверх стабильности. Классификация — C1 (θ_w=0.55, θ_o=0.5, non_fast, правило B, hero = rare_anchor).

## 1. Сводная таблица по стратам

| страта | hero/81 | conv | single | no_anchor | med sig | public/день | time_sensitive/день | zero-robust дней |
|---|---|---|---|---|---|---|---|---|
| exact | 10 | 25 | 8 | 38 | 47 | 158.2 | 0.0 | 0 |
| night | 2 | 14 | 11 | 54 | 15 | 63.6 | 249.4 | 0 |
| morning | 2 | 14 | 10 | 55 | 15 | 64.7 | 253.2 | 0 |
| day | 2 | 15 | 11 | 53 | 17 | 64.5 | 257.9 | 0 |
| evening | 1 | 10 | 12 | 58 | 14 | 64.0 | 254.7 | 0 |
| unknown | 1 | 8 | 10 | 62 | 12 | 58.7 | 466.8 | 0 |

Контроль: exact-страта воспроизводит C1 baseline (hero=10/81, ожидалось 10). zero-robust — дни, где после робастности не выжил НИ ОДИН персональный факт (публичный набор пуст) — это и есть случай «общий фон дня».

Hero-дни по стратам:
- exact: ['2026-06-15', '2026-06-18', '2026-06-24', '2026-07-01', '2026-07-03', '2026-07-08', '2026-07-21', '2026-07-23', '2026-08-03', '2026-08-12']
- night: ['2026-07-02', '2026-07-21']
- morning: ['2026-07-21', '2026-07-22']
- day: ['2026-07-03', '2026-07-21']
- evening: ['2026-07-03']
- unknown: ['2026-07-21']

Чтение: робастность режет hero-частоту с 10/81 (exact) до 1–2/81; единственный день, переживший все страты, — 2026-07-21 (кластер Jupiter/Saturn с точным якорем). «Общего фона» в буквальном смысле (0 публичных фактов) нет ни в одной страте: ~59–65 фактов/день выживают даже в unknown; но состояние no_anchor растёт 38 → 62/81 — для bucket/unknown-пользователей подавляющее большинство дней становится «тихими» (значимые единицы есть, якоря нет).

## 2. Что умирает как time_sensitive (топ-8 типов на страту)

**night** (всего 20198 исключено за 81 день):
- transit / lot: 7515
- transit / angle: 4472
- transit / house: 2430
- return / natal_planet: 1717
- progression / lot: 1285

**morning** (всего 20509 исключено за 81 день):
- transit / lot: 7869
- transit / angle: 4676
- return / natal_planet: 1864
- transit / house: 1620
- progression / lot: 1425

**day** (всего 20891 исключено за 81 день):
- transit / lot: 7981
- transit / angle: 4426
- transit / house: 2430
- return / natal_planet: 1754
- progression / lot: 1409

**evening** (всего 20633 исключено за 81 день):
- transit / lot: 7537
- transit / angle: 4726
- return / natal_planet: 1816
- transit / house: 1620
- progression / lot: 1566

**unknown** (всего 37814 исключено за 81 день):
- transit / lot: 13523
- transit / angle: 7276
- transit / house: 4860
- return / natal_planet: 3162
- return / house: 2474

## 3. Фикстуры

- **(8) unknown: нет house/angle/lot факторов** — нарушений: 0 → PASS.
- **(9) инвариантность к сдвигу контрольных времён внутри диапазона** (byte-identical публичный набор):
  - night: identical 25/81, differing 56 → FAIL
    - расхождение 2026-06-01: main-only []; shifted-only ['["activation:monthly_profection__LORD_OF_MONTH__SATURN", "neutral", ["work", "money", "documents", "relationships", "sport", "health", "decisions"]]', '["aspect:PLUTO:opposition:natal_planet:MOON", "tense", ["work", "relationships", "sport", "communication", "health", "decisions"]]']
    - расхождение 2026-06-02: main-only []; shifted-only ['["activation:monthly_profection__LORD_OF_MONTH__SATURN", "neutral", ["work", "money", "documents", "relationships", "sport", "health", "decisions"]]', '["aspect:JUPITER:trine:natal_planet:MERCURY", "supportive", ["work", "money", "documents", "communication", "decisions", "study"]]']
    - расхождение 2026-06-03: main-only []; shifted-only ['["activation:monthly_profection__LORD_OF_MONTH__SATURN", "neutral", ["work", "money", "documents", "relationships", "sport", "health", "decisions"]]', '["aspect:PLUTO:opposition:natal_planet:MOON", "tense", ["work", "relationships", "sport", "communication", "health", "decisions"]]']
  - morning: identical 56/81, differing 25 → FAIL
    - расхождение 2026-06-05: main-only []; shifted-only ['["aspect:JUPITER:conjunction:natal_planet:MOON", "mixed", ["work", "money", "relationships", "sport", "communication", "health", "decisions"]]']
    - расхождение 2026-06-06: main-only []; shifted-only ['["aspect:JUPITER:conjunction:natal_planet:MOON", "mixed", ["work", "money", "relationships", "sport", "communication", "health", "decisions"]]']
    - расхождение 2026-06-07: main-only []; shifted-only ['["aspect:JUPITER:conjunction:natal_planet:MOON", "mixed", ["work", "money", "relationships", "sport", "communication", "health", "decisions"]]']
  - day: identical 0/81, differing 81 → FAIL
    - расхождение 2026-06-01: main-only ['["activation:firdar_major__PERIOD_LORD__SUN", "neutral", ["work", "sport", "decisions"]]', '["activation:firdar_minor__SUBPERIOD_LORD__SATURN", "neutral", ["work", "money", "documents", "relationships", "sport", "health", "decisions"]]']; shifted-only []
    - расхождение 2026-06-02: main-only ['["activation:firdar_major__PERIOD_LORD__SUN", "neutral", ["work", "sport", "decisions"]]', '["activation:firdar_minor__SUBPERIOD_LORD__SATURN", "neutral", ["work", "money", "documents", "relationships", "sport", "health", "decisions"]]']; shifted-only []
    - расхождение 2026-06-03: main-only ['["activation:firdar_major__PERIOD_LORD__SUN", "neutral", ["work", "sport", "decisions"]]', '["activation:firdar_minor__SUBPERIOD_LORD__SATURN", "neutral", ["work", "money", "documents", "relationships", "sport", "health", "decisions"]]']; shifted-only ['["aspect:MARS:square:natal_planet:MOON", "tense", ["work", "relationships", "sport", "communication", "health", "decisions"]]']
  - evening: identical 24/81, differing 57 → FAIL
    - расхождение 2026-06-01: main-only []; shifted-only ['["aspect:SOLAR:conjunction:natal_planet:MERCURY", "mixed", ["documents", "communication", "study"]]', '["aspect:SOLAR:semi_sextile:natal_planet:SUN", "neutral", ["work", "sport", "decisions"]]']
    - расхождение 2026-06-02: main-only []; shifted-only ['["aspect:SOLAR:conjunction:natal_planet:MERCURY", "mixed", ["documents", "communication", "study"]]', '["aspect:SOLAR:semi_sextile:natal_planet:SUN", "neutral", ["work", "sport", "decisions"]]']
    - расхождение 2026-06-03: main-only []; shifted-only ['["aspect:SOLAR:conjunction:natal_planet:MERCURY", "mixed", ["documents", "communication", "study"]]', '["aspect:SOLAR:semi_sextile:natal_planet:SUN", "neutral", ["work", "sport", "decisions"]]']
- **(11) сэмплинг не размножает единицы** (N точек одного факта = 1 юнит):
  - night: дубликатов идентичностей 0, средний dedup-ratio 3.5× → PASS
  - morning: дубликатов идентичностей 0, средний dedup-ratio 3.4× → PASS
  - day: дубликатов идентичностей 0, средний dedup-ratio 3.53× → PASS
  - evening: дубликатов идентичностей 0, средний dedup-ratio 3.58× → PASS
  - unknown: дубликатов идентичностей 0, средний dedup-ratio 6.23× → PASS

### Разбор FAIL фикстуры 9 — три механизма

1. **Аномалия секты/firdar (day-бакет 0/81)**: определение day/night на sidecar немонотонно по времени рождения: firdar_major=SUN в 12:00, 15:00, 17:59, но firdar_major=SATURN в 13:00, 16:00, 17:00 (проверено на 2026-06-01; unknown-страта показывает тот же флип в 16:00). Физического заката в этих точках нет (лето, широта Москвы, закат ~21:20) — похоже на баг/шум в определении секты; лоты Fortune/Spirit (их формулы зависят от секты) флипаются синхронно. Требует расследования на стороне движка; до фикса 3-точечный сэмплинг в day-бакете не определяет стабильный набор вообще.
2. **ASC-зависимые техники**: annual/monthly profection lord зависит от знака ASC (знак меняется каждые ~2ч) — внутри любого 6-часового бакета лорд профекции переключается 2–3 раза; устойчиво умирает как time_sensitive (ожидаемо).
3. **Орб-граничные лунные факты**: натальная Луна смещается ~3° за 6 часов; аспекты к натальной Луне с орбом у границы профиля (напр. JUPITER conjunction MOON) присутствуют в одних контрольных точках и отсутствуют в других — вердикт стабильности зависит от выбора точек сэмпла.
Вывод по фикстуре 9: при 3-точечном сэмплинге «стабильный набор» НЕ является функцией диапазона — он функция конкретных точек. Варианты для W1: (а) плотнее сэмплинг (напр. каждый час → 7 точек/бакет, 13/unknown) с бюджетом из §4; (б) явное правило дискретизации: стабильность считать по фиксированной канонической сетке (edges+middle как ЕДИНСТВЕННЫЙ легальный сэмпл) — тогда сдвиг неопределён, но это декларация, а не робастность; (в) для орб-фактов требовать запас (orb_fraction ≤ θ_o − margin) вместо двоичной стабильности.

## 4. Производительность (бюджет W5 pregen)

- Полный дамп: 590.8с; sidecar activation-layer вызовов: 1944 (24 контрольных времени × 81 день), natal: 24, transits: 81 (birth-независимы, кэшируются).
- Измеренная стоимость одного (control_time, day) end-to-end: ~0.30с (включая normalize/ledger/классификацию; чистый sidecar ≈ 0.2с).
- Маргинальная стоимость pregen на пользователя-день: **bucket ≈ 3×0.30 + transit ≈ 1.0с**, **unknown ≈ 6×0.30 + transit ≈ 2.0с**; для сравнения exact ≈ 0.4с. Т.е. bucket-пользователь ≈ 3×, unknown ≈ 6× от стоимости exact. Natal-контексты контрольных времён кэшируются один раз на пользователя (вне дневного бюджета; 3–6 get_natal при первом расчёте). Вариант (а) из фикстуры 9 (почасовой сэмпл) стоил бы ≈ 7×/13× соответственно.

## 5. Оговорки

- **Немонотонная секта на sidecar** (firdar major/minor лорды флипаются в 13:00/16:00/17:00 при соседних «дневных» точках) — см. разбор фикстуры 9; это доминирующий источник нестабильности day-бакета и отдельный пункт для расследования движка. Результаты day/unknown-страт загрязнены этим эффектом.
- DayDelta пропущен (доказуемо контент-нейтрален для сохраняемых полей: аннотирует только delta_kind/daily_salience/phase; триггерная ветка day_delta мертва — см. ablation_report.md §7).
- theme_keys/source берутся от первого вхождения при слиянии идентичностей; на группировку не влияет (связность почти вся по shared target_key).
- Консервативная роль (якорь только если якорь на всех точках) и max-орб — нижняя оценка публичности; majority-role/mean-orb дадут +1..2 hero-дня.
- Одна карта, один сезон; частоты — про чувствительность фактов этой карты, не про генеральную популяцию пользователей.
