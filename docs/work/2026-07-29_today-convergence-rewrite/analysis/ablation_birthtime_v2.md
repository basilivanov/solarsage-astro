# Birth-time strata v2 (master v1.5): фиксированная модель + orb-margin

Модель: все фиксы F1–F8 включены; стабильность — ORB-MARGIN (аспект публичен, если присутствует на всех точках сетки И orb_ratio ≤ θ_o на КАЖДОЙ точке; fail-closed для источников вне orb-профиля канона). DayDelta-триггеры применяются по скорректированному контракту на каждом контрольном времени. Жёсткое правило bucket/unknown (без house/angle/lot) сохранено. Точка C1: θ_w=0.55, θ_o=0.5, правило B, hero = rare_anchor.

## 1. Сводная таблица (v2) и сравнение с v1

| страта | hero v2 | conv | single | quiet_imp | med sig | public/день | ts/день | zero-robust | hero v1 |
|---|---|---|---|---|---|---|---|---|---|
| exact | 8 | 71 | 2 | 0 | 44 | 158.2 | 0.0 | 0 | 10 |
| night | 2 | 74 | 3 | 2 | 17 | 27.3 | 285.7 | 0 | 2 |
| morning | 2 | 74 | 4 | 1 | 17 | 26.7 | 291.2 | 0 | 2 |
| day | 2 | 71 | 6 | 2 | 19 | 28.8 | 293.6 | 0 | 2 |
| evening | 1 | 71 | 6 | 3 | 17 | 26.7 | 292.1 | 0 | 1 |
| unknown | 1 | 70 | 7 | 3 | 14 | 22.7 | 502.8 | 0 | 1 |

- exact hero-дни: ['2026-06-15', '2026-06-24', '2026-07-01', '2026-07-03', '2026-07-08', '2026-07-21', '2026-07-23', '2026-08-03']
- night hero-дни: ['2026-07-02', '2026-07-21']
- morning hero-дни: ['2026-07-21', '2026-07-22']
- day hero-дни: ['2026-07-03', '2026-07-21']
- evening hero-дни: ['2026-07-03']
- unknown hero-дни: ['2026-07-21']

## 2. time_sensitive жертвы (топ-6 на страту)

**night** (всего 23138): transit/lot: 7515; transit/angle: 4472; transit/natal_planet: 3008; transit/house: 2430; return/natal_planet: 1717; progression/lot: 1285
**morning** (всего 23589): transit/lot: 7869; transit/angle: 4676; transit/natal_planet: 3015; return/natal_planet: 1864; transit/house: 1620; progression/lot: 1425
**day** (всего 23780): transit/lot: 7981; transit/angle: 4426; transit/natal_planet: 2900; transit/house: 2430; return/natal_planet: 1754; progression/lot: 1409
**evening** (всего 23662): transit/lot: 7537; transit/angle: 4726; transit/natal_planet: 3115; return/natal_planet: 1816; transit/house: 1620; progression/lot: 1566
**unknown** (всего 40729): transit/lot: 13523; transit/angle: 7276; transit/house: 4860; transit/natal_planet: 3506; return/natal_planet: 3162; return/house: 2474

## 3. Фикстуры

- (8) unknown без house/angle/lot: нарушений 0 → PASS.
- (9) инвариантность к сдвигу сэмпла (orb-margin правило):
  - night: identical 34/81, differing 47 → FAIL
  - morning: identical 45/81, differing 36 → FAIL
  - day: identical 0/81, differing 81 → FAIL
  - evening: identical 60/81, differing 21 → FAIL
- (11) сэмплинг не размножает юниты:
  - night: дубликатов 0, dedup-ratio 8.2× → PASS
  - morning: дубликатов 0, dedup-ratio 8.3× → PASS
  - day: дубликатов 0, dedup-ratio 7.96× → PASS
  - evening: дубликатов 0, dedup-ratio 8.69× → PASS
  - unknown: дубликатов 0, dedup-ratio 16.27× → PASS

Примечание к фикстуре 9: orb-margin устраняет расхождения класса «орб-граничный аспект к натальной Луне» (пункт 3 разбора v1), но НЕ расхождения от секты/firdar (немонотонный day/night на sidecar — engine-баг из v1-отчёта) и ASC-зависимых профекций: они остаются сэмпл-зависимыми при 3-точечной сетке.

## 4. Производительность

- Дамп v2: 598.9с, 1944 act-layer вызовов, ~0.31с на (время, день). Pregen: bucket ≈ 1.0с/польз-день, unknown ≈ 2.0с (exact ≈ 0.4с).

## 5. Оговорки

- Те же, что в v1-стратах (секта sidecar, консервативная роль/max-орб, одна карта), плюс: orb-margin делает публичность зависимой от θ_o — смена порога значимости меняет и стабильный набор (задокументировать в каноне).
- DayDelta вчерашних сигналов считается по тому же контрольному времени — контракт «вчера/сегодня» согласован внутри каждой точки сетки.
