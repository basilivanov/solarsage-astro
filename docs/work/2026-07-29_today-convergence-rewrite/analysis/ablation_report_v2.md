# Ablation v2 (master v1.5): исправленная пятислойная модель — ландшафт и C1

Данные: владелец (`basil_ivanov`), 81 день, `factor_dump_v2.json` (12817 факторов + скорректированные DayDelta-триггеры по семантической идентичности). Фиксы F1–F8 реализованы как флаги `FIXES` в `ablation_harness.py` (v1-функции не тронуты, v1-артефакты воспроизводимы). Точка C1: θ_w=0.55, θ_o=0.5, правило B.

## 1. Фикс-лист → before/after (кумулятивно, точка C1)

| шаг | hero/81 | conv | single | quiet_imp | quiet | med sig | p90 sig |
|---|---|---|---|---|---|---|---|
| baseline v1 (C1, rare_anchor, non_fast) | 10 | 25 | 8 | 38 | 0 | 47 | 54 |
| +F1 three-tier (fast = impulse/evidence) | 9 | 72 | 0 | 0 | 0 | 59 | 68 |
| +F2 background out of groups | 9 | 70 | 2 | 0 | 0 | 59 | 68 |
| +F3 direct star grouping | 9 | 70 | 2 | 0 | 0 | 59 | 68 |
| +F4 corrected DayDelta triggers | 9 | 72 | 0 | 0 | 0 | 59 | 68 |
| +F5 sphere no fan-out | 9 | 72 | 0 | 0 | 0 | 59 | 68 |
| +F6 event_class=whitelist_timelord | 9 | 70 | 2 | 0 | 0 | 49 | 58 |
| +F7 orb fail-closed | 9 | 70 | 2 | 0 | 0 | 44 | 53 |
| +F8 rare narrowed (all fixes) | 8 | 71 | 2 | 0 | 0 | 44 | 53 |

Замеры по шагам: F1 возвращает быстрые источники в импульсы/свидетели (med sig 47 → 59/день). F4 добавляет anchor_today: 169 апгрейдов роли за 81 день (hero 9 → 9). F7 исключает fail-closed: 459 юнитов (SOLAR/PROGRESSED вне orb-профиля). F3 (star вместо components): hero 8 → 8 (проверка ревьюера «без изменений»).

## 2. Обновлённый ландшафт (все фиксы включены)

| config | hero | conv | single | quiet_imp | med sig | p90 | tense max/med |
|---|---|---|---|---|---|---|---|
| w0.25_o0.3_fixed_B | 7 | 73 | 1 | 0 | 49 | 57 | 17/5 |
| w0.25_o0.5_fixed_B | 11 | 70 | 0 | 0 | 70 | 79 | 18/6 |
| w0.25_o0.7_fixed_B | 11 | 70 | 0 | 0 | 95 | 104 | 23/6 |
| w0.25_o1.0_fixed_B | 14 | 67 | 0 | 0 | 124 | 135 | 23/7 |
| w0.3_o0.3_fixed_B | 7 | 72 | 2 | 0 | 46 | 54 | 17/5 |
| w0.3_o0.5_fixed_B | 11 | 70 | 0 | 0 | 65 | 74 | 23/5 |
| w0.3_o0.7_fixed_B | 11 | 70 | 0 | 0 | 89 | 97 | 28/6 |
| w0.3_o1.0_fixed_B | 14 | 67 | 0 | 0 | 116 | 126 | 28/6 |
| w0.4_o0.3_fixed_B | 5 | 67 | 7 | 2 | 39 | 46 | 12/5 |
| w0.4_o0.5_fixed_B | 8 | 73 | 0 | 0 | 52 | 62 | 10/5 |
| w0.4_o0.7_fixed_B | 8 | 73 | 0 | 0 | 67 | 77 | 26/4 |
| w0.4_o1.0_fixed_B | 12 | 69 | 0 | 0 | 90 | 102 | 26/5 |
| w0.55_o0.3_fixed_B | 5 | 63 | 10 | 3 | 34 | 40 | 21/5 |
| w0.55_o0.5_fixed_B | 8 | 71 | 2 | 0 | 44 | 53 | 10/4 |
| w0.55_o0.7_fixed_B | 8 | 73 | 0 | 0 | 56 | 63 | 19/5 |
| w0.55_o1.0_fixed_B | 12 | 69 | 0 | 0 | 74 | 84 | 26/4 |
| w0.85_o0.3_fixed_B | 3 | 54 | 15 | 9 | 31 | 37 | 39/5 |
| w0.85_o0.5_fixed_B | 5 | 67 | 5 | 4 | 39 | 48 | 20/5 |
| w0.85_o0.7_fixed_B | 5 | 72 | 2 | 2 | 50 | 57 | 17/6 |
| w0.85_o1.0_fixed_B | 7 | 74 | 0 | 0 | 65 | 73 | 26/5 |

Коллапс оси θ_p (D7): hero при any/non_moon/non_fast = {'any': 8, 'non_moon': 8, 'non_fast': 8} — после F1 ось исключения источников упразднена, быстрые источники фильтруются только из rare_anchor-тира. Правило A вместо B: hero 1 (B: 8). Sanity V0 (slow+major+planet/angle) под фиксированной моделью: hero 5/81 ['2026-06-24', '2026-07-02', '2026-07-08', '2026-07-23', '2026-08-03'] (v1 давал 4/81, ревьюер ≈9/81).

## 3. C1: baseline vs fixed

| метрика | baseline v1 | fixed v2 |
|---|---|---|
| hero/81 | 10 | 8 |
| convergence | 25 | 71 |
| single_impulse | 8 | 2 |
| quiet_impulses | 38 | 0 |
| med sig | 47 | 44 |
| p90 sig | 54 | 53 |
| hero-дни | ['2026-06-15', '2026-06-18', '2026-06-24', '2026-07-01', '2026-07-03', '2026-07-08', '2026-07-21', '2026-07-23', '2026-08-03', '2026-08-12'] | ['2026-06-15', '2026-06-24', '2026-07-01', '2026-07-03', '2026-07-08', '2026-07-21', '2026-07-23', '2026-08-03'] |

## 4. F6: пороги event_class для не-аспектных юнитов (точка C1)

| режим | hero | conv | med sig | p90 sig |
|---|---|---|---|---|
| auto | 8 | 73 | 54 | 63 |
| whitelist_timelord | 8 | 71 | 44 | 53 |
| strength_0.5 | 8 | 73 | 51 | 60 |
| strength_0.7 | 7 | 74 | 41 | 50 |

## 5. Tense streaks на публичных юнитах

- baseline v1 (все единицы): tense-дней 81/81, max streak 81, медиана streak 81.
- fixed v2 (только публичные значимые): tense-дней 68/81, max streak 10, медиана streak 4, серий 14.

## 6. Распределение hero-групп по сферам: fan-out до/после

| сфера | v1 (per-sphere fan-out) | v2 (primary+secondary) |
|---|---|---|
| work | 11 | 9 |
| decisions | 14 | 0 |
| money | 7 | 5 |
| sport | 7 | 2 |
| health | 8 | 0 |
| relationships | 6 | 2 |
| communication | 2 | 2 |
| documents | 3 | 0 |
| shopping | 1 | 0 |
| travel | 1 | 0 |

Доля `decisions`: 23% → 0%. Текущая планетная карта (PLANET_TO_PRODUCT_MAP) раздаёт `decisions` шести планетам из десяти: SUN [work, decisions], MARS [work, sport, decisions], JUPITER [work, money, decisions], SATURN [work, decisions, documents], URANUS [decisions, travel], PLUTO [decisions, work] — это и есть причина catch-all.

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
