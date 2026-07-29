# Ablation v2 (master v1.5): исправленная пятислойная модель — ландшафт и C1

Данные: владелец (`basil_ivanov`), 81 день, `factor_dump_v2.json` (12817 факторов + скорректированные DayDelta-триггеры по семантической идентичности). Фиксы F1–F8 реализованы как флаги `FIXES` в `ablation_harness.py` (v1-функции не тронуты, v1-артефакты воспроизводимы). Точка C1: θ_w=0.55, θ_o=0.5, правило B.

## 1. Фикс-лист → before/after (кумулятивно, точка C1)

| шаг | hero/81 | conv | single | quiet_imp | quiet | med sig | p90 sig |
|---|---|---|---|---|---|---|---|
| baseline v1 (C1, rare_anchor, non_fast) | 10 | 25 | 8 | 38 | 0 | 47 | 54 |
| +F1 three-tier (fast = impulse/evidence) | 12 | 69 | 0 | 0 | 0 | 59 | 68 |
| +F2 background out of groups | 12 | 67 | 2 | 0 | 0 | 59 | 68 |
| +F3 direct star grouping | 12 | 67 | 2 | 0 | 0 | 59 | 68 |
| +F4 corrected DayDelta triggers | 13 | 68 | 0 | 0 | 0 | 59 | 68 |
| +F5 sphere no fan-out | 13 | 68 | 0 | 0 | 0 | 59 | 68 |
| +F6 event_class=whitelist_timelord | 11 | 68 | 2 | 0 | 0 | 49 | 58 |
| +F7 orb fail-closed | 11 | 68 | 2 | 0 | 0 | 44 | 53 |
| +F8 rare narrowed (all fixes) | 10 | 69 | 2 | 0 | 0 | 44 | 53 |

Замеры по шагам: F1 возвращает быстрые источники в импульсы/свидетели (med sig 47 → 59/день). F4 добавляет anchor_today: 169 апгрейдов роли за 81 день (hero 12 → 13). F7 исключает fail-closed: 459 юнитов (SOLAR/PROGRESSED вне orb-профиля). F3 (star вместо components): hero 10 → 10 (проверка ревьюера «без изменений»).

## 2. Обновлённый ландшафт (все фиксы включены)

| config | hero | conv | single | quiet_imp | med sig | p90 | tense max/med |
|---|---|---|---|---|---|---|---|
| w0.25_o0.3_fixed_B | 15 | 65 | 1 | 0 | 49 | 57 | 81/81 |
| w0.25_o0.5_fixed_B | 17 | 64 | 0 | 0 | 70 | 79 | 81/81 |
| w0.25_o0.7_fixed_B | 17 | 64 | 0 | 0 | 95 | 104 | 81/81 |
| w0.25_o1.0_fixed_B | 18 | 63 | 0 | 0 | 124 | 135 | 81/81 |
| w0.3_o0.3_fixed_B | 12 | 67 | 2 | 0 | 46 | 54 | 81/81 |
| w0.3_o0.5_fixed_B | 15 | 66 | 0 | 0 | 65 | 74 | 81/81 |
| w0.3_o0.7_fixed_B | 16 | 65 | 0 | 0 | 89 | 97 | 81/81 |
| w0.3_o1.0_fixed_B | 17 | 64 | 0 | 0 | 116 | 126 | 81/81 |
| w0.4_o0.3_fixed_B | 10 | 62 | 7 | 2 | 39 | 46 | 81/81 |
| w0.4_o0.5_fixed_B | 12 | 69 | 0 | 0 | 52 | 62 | 81/81 |
| w0.4_o0.7_fixed_B | 13 | 68 | 0 | 0 | 67 | 77 | 81/81 |
| w0.4_o1.0_fixed_B | 15 | 66 | 0 | 0 | 90 | 102 | 81/81 |
| w0.55_o0.3_fixed_B | 8 | 60 | 10 | 3 | 34 | 40 | 81/81 |
| w0.55_o0.5_fixed_B | 10 | 69 | 2 | 0 | 44 | 53 | 81/81 |
| w0.55_o0.7_fixed_B | 11 | 70 | 0 | 0 | 56 | 63 | 81/81 |
| w0.55_o1.0_fixed_B | 14 | 67 | 0 | 0 | 74 | 84 | 81/81 |
| w0.85_o0.3_fixed_B | 6 | 51 | 15 | 9 | 31 | 37 | 81/81 |
| w0.85_o0.5_fixed_B | 6 | 66 | 5 | 4 | 39 | 48 | 81/81 |
| w0.85_o0.7_fixed_B | 7 | 70 | 2 | 2 | 50 | 57 | 81/81 |
| w0.85_o1.0_fixed_B | 10 | 71 | 0 | 0 | 65 | 73 | 81/81 |

Коллапс оси θ_p (D7): hero при any/non_moon/non_fast = {'any': 10, 'non_moon': 10, 'non_fast': 10} — после F1 ось исключения источников упразднена, быстрые источники фильтруются только из rare_anchor-тира. Правило A вместо B: hero 1 (B: 10). Sanity V0 (slow+major+planet/angle) под фиксированной моделью: hero 5/81 ['2026-06-24', '2026-07-02', '2026-07-08', '2026-07-23', '2026-08-03'] (v1 давал 4/81, ревьюер ≈9/81).

## 3. C1: baseline vs fixed

| метрика | baseline v1 | fixed v2 |
|---|---|---|
| hero/81 | 10 | 10 |
| convergence | 25 | 69 |
| single_impulse | 8 | 2 |
| quiet_impulses | 38 | 0 |
| med sig | 47 | 44 |
| p90 sig | 54 | 53 |
| hero-дни | ['2026-06-15', '2026-06-18', '2026-06-24', '2026-07-01', '2026-07-03', '2026-07-08', '2026-07-21', '2026-07-23', '2026-08-03', '2026-08-12'] | ['2026-06-04', '2026-06-15', '2026-06-17', '2026-06-24', '2026-07-01', '2026-07-03', '2026-07-08', '2026-07-21', '2026-07-23', '2026-08-03'] |

## 4. F6: пороги event_class для не-аспектных юнитов (точка C1)

| режим | hero | conv | med sig | p90 sig |
|---|---|---|---|---|
| auto | 11 | 70 | 54 | 63 |
| whitelist_timelord | 10 | 69 | 44 | 53 |
| strength_0.5 | 11 | 70 | 51 | 60 |
| strength_0.7 | 10 | 71 | 41 | 50 |

## 5. Tense streaks на публичных юнитах

- baseline v1 (все единицы): tense-дней 81/81, max streak 81, медиана streak 81.
- fixed v2 (только публичные значимые): tense-дней 81/81, max streak 81, медиана streak 81, серий 1.

## 6. Распределение hero-групп по сферам: fan-out до/после

| сфера | v1 (per-sphere fan-out) | v2 (primary+secondary) |
|---|---|---|
| work | 11 | 9 |
| decisions | 14 | 1 |
| money | 7 | 5 |
| sport | 7 | 2 |
| relationships | 6 | 2 |
| health | 8 | 0 |
| communication | 2 | 5 |
| documents | 3 | 0 |
| shopping | 1 | 0 |
| travel | 1 | 0 |

Доля `decisions`: 23% → 4%. Текущая планетная карта (PLANET_TO_PRODUCT_MAP) раздаёт `decisions` шести планетам из десяти: SUN [work, decisions], MARS [work, sport, decisions], JUPITER [work, money, decisions], SATURN [work, decisions, documents], URANUS [decisions, travel], PLUTO [decisions, work] — это и есть причина catch-all.

Предлагаемая ревизия карты (кандидат в канон W1, ≤2 сферы на планету, decisions только для «планет суждения»):

| планета | сейчас | предложение |
|---|---|---|
| SUN | work, decisions | work |
| MARS | work, sport, decisions | sport, work |
| VENUS | money, relationships, shopping | без изменений |
| MERCURY | documents, communication, study | без изменений |
| JUPITER | work, money, decisions | money, work |
| SATURN | work, decisions, documents | decisions, documents |
| MOON | relationships, health | без изменений |
| URANUS | decisions, travel | travel, creativity |
| NEPTUNE | creativity, health | без изменений |
| PLUTO | decisions, work | decisions |

При такой карте decisions получают только SATURN и PLUTO; остальные сферы распределяются по профильным планетам. Числа выше (после F5) уже не fan-out'ятся по 3–4 сферам, но доля decisions останется высокой, пока карта не пересмотрена.

## 7. Оговорки

- F4 симулирует исправленный контракт DayDelta (sem-identity); прод-фикс — W2. Апгрейд роли возможен только для фактов, чей semantic_key формата aspect:*; time-lord активации триггерами не покрываются (их sem_key не signal-формата).
- F5 проецирует группу по большинству голосов членов; при равенстве — сфера якоря (канонический порядок), затем канонический порядок. Secondary требует ≥2 голосов.
- Консервативности: orb = max по контрольным временам (страты), anchor только если якорь везде — как в v1-стратах.
- Одна карта, один сезон.
