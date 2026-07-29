> **СТАТУС: diagnostic / superseded.** Старый классификатор (до fix-list v1.5: без трёхуровневой eligibility, background в группах, transitive grouping). Числа недействительны для финала; финальный отчёт — `ablation_report_v2.md` (готовится). Оставлено как история калибровки.

# W1 ablation: ландшафт порогов значимости и независимости (Today convergence rewrite)

Данные: владелец продукта (`basil_ivanov`), 81 день (2026-06-01..2026-08-20), детерминированный пайплайн TodayService без LLM (sidecar transits + activation layer, build_factor_ledger fallback — как в проде). Дамп: `factor_dump.json` (12817 факторов). Ниже — калибровочный ландшафт для слоёв «значимый импульс → независимая единица → convergence/hero». Победитель НЕ выбирался по близости к квоте 10–20% hero-дней (анти-Гудхарт); показаны колени и интерпретируемые области.

## 1. Главная сетка (θ_w × θ_o, θ_p=non_fast, независимость B, hero=rare любой член)

| config | hero/81 | conv | single | quiet | med sig | p90 sig | tense streak | top sphere (share) |
|---|---|---|---|---|---|---|---|---|
| w0.25_o0.3_nonfast_B | 48 | 0 | 33 | 0 | 51 | 60 | 81 | decisions (0.896) |
| w0.25_o0.5_nonfast_B | 52 | 1 | 28 | 0 | 63 | 72 | 81 | decisions (0.981) |
| w0.25_o0.7_nonfast_B | 52 | 1 | 28 | 0 | 81 | 89 | 81 | decisions (0.981) |
| w0.25_o1.0_nonfast_B | 55 | 0 | 26 | 0 | 101 | 113 | 81 | decisions (1.0) |
| w0.3_o0.3_nonfast_B | 47 | 0 | 34 | 0 | 49 | 58 | 81 | decisions (0.872) |
| w0.3_o0.5_nonfast_B | 51 | 1 | 29 | 0 | 61 | 70 | 81 | decisions (0.961) |
| w0.3_o0.7_nonfast_B | 51 | 1 | 29 | 0 | 77 | 85 | 81 | decisions (0.961) |
| w0.3_o1.0_nonfast_B | 54 | 0 | 27 | 0 | 97 | 108 | 81 | decisions (1.0) |
| w0.4_o0.3_nonfast_B | 36 | 0 | 45 | 0 | 43 | 51 | 81 | decisions (0.889) |
| w0.4_o0.5_nonfast_B | 38 | 0 | 43 | 0 | 52 | 61 | 81 | decisions (0.947) |
| w0.4_o0.7_nonfast_B | 38 | 2 | 41 | 0 | 62 | 70 | 81 | decisions (0.947) |
| w0.4_o1.0_nonfast_B | 43 | 2 | 36 | 0 | 78 | 88 | 81 | decisions (1.0) |
| w0.55_o0.3_nonfast_B | 32 | 0 | 49 | 0 | 40 | 46 | 81 | decisions (0.875) |
| w0.55_o0.5_nonfast_B | 35 | 0 | 46 | 0 | 47 | 54 | 81 | decisions (0.914) |
| w0.55_o0.7_nonfast_B | 35 | 1 | 45 | 0 | 55 | 60 | 81 | decisions (0.943) |
| w0.55_o1.0_nonfast_B | 40 | 0 | 41 | 0 | 68 | 74 | 81 | decisions (0.975) |
| w0.85_o0.3_nonfast_B | 26 | 0 | 55 | 0 | 39 | 44 | 81 | decisions (0.885) |
| w0.85_o0.5_nonfast_B | 27 | 0 | 54 | 0 | 44 | 51 | 81 | decisions (0.926) |
| w0.85_o0.7_nonfast_B | 28 | 1 | 52 | 0 | 51 | 57 | 81 | decisions (0.929) |
| w0.85_o1.0_nonfast_B | 33 | 0 | 48 | 0 | 62 | 68 | 81 | decisions (0.97) |

Чтение: θ_w — главный регулятор (0.30→0.40: −13..15 hero-дней; 0.55→0.85: −7..8). θ_o монотонен и слабее: основной прирост между 0.7→1.0 (широкие орбы добавляют группы). `quiet` (0 значимых импульсов) недостижим ни в одной конфигурации: не-аспектные time-lord единицы (firdar/profection/return) структурны и всегда проходят фильтр веса — это осознанный дизайн-выбор, но он означает, что «пустой день» возможен только как «нет якоря», а не как «нет единиц». `tense_streak=81` везде: в этой карте всегда есть хотя бы один значимый напряжённый юнит — метрика недискриминативна.

## 2. Ось редкости hero (главное колено ландшафта)

Hero-предикаты: `any` — редкий юнит где-либо в группе; `rare_nonbg` — редкий юнит не background; `rare_anchor` — редкий юнит и есть якорь дня.

| θ_w | θ_o | hero_any | rare_nonbg | rare_anchor |
|---|---|---|---|---|
| 0.25 | 0.3 | 48 | 41 | 15 |
| 0.25 | 0.5 | 52 | 50 | 18 |
| 0.25 | 0.7 | 52 | 51 | 18 |
| 0.25 | 1.0 | 55 | 55 | 18 |
| 0.3 | 0.3 | 47 | 40 | 13 |
| 0.3 | 0.5 | 51 | 49 | 16 |
| 0.3 | 0.7 | 51 | 50 | 17 |
| 0.3 | 1.0 | 54 | 54 | 17 |
| 0.4 | 0.3 | 36 | 31 | 11 |
| 0.4 | 0.5 | 38 | 35 | 12 |
| 0.4 | 0.7 | 38 | 35 | 13 |
| 0.4 | 1.0 | 43 | 41 | 13 |
| 0.55 | 0.3 | 32 | 26 | 9 |
| 0.55 | 0.5 | 35 | 30 | 10 |
| 0.55 | 0.7 | 35 | 31 | 11 |
| 0.55 | 1.0 | 40 | 37 | 12 |
| 0.85 | 0.3 | 26 | 22 | 6 |
| 0.85 | 0.5 | 27 | 24 | 7 |
| 0.85 | 0.7 | 28 | 25 | 7 |
| 0.85 | 1.0 | 33 | 31 | 8 |

Вывод: пока редкость засчитывается по background time-lord юнитам (profection, solar/lunar return — они есть каждый день), hero не падает ниже ~26/81. Перенос редкости в якорь («структурный/медленный фактор точен именно сегодня И подтверждён независимой единицей») переводит ландшафт в зону 6–18/81 — это a priori защитимое определение hero-дня, а не подгонка под квоту. Именно этот предикат согласует модель с оценкой ревьюера (см. §4).

## 3. Чувствительность к θ_p и правилу независимости

| config | hero/81 | conv | single | med sig |
|---|---|---|---|---|
| w0.4_o0.5_any_B | 80 | 1 | 0 | 68 |
| w0.4_o0.5_non_moon_B | 56 | 7 | 18 | 61 |
| w0.4_o0.5_nonfast_B | 38 | 0 | 43 | 52 |
| w0.55_o0.5_any_B | 79 | 2 | 0 | 59 |
| w0.55_o0.5_non_moon_B | 53 | 2 | 26 | 54 |
| w0.55_o0.5_nonfast_B | 35 | 0 | 46 | 47 |
| w0.4_o0.5_nonfast_A | 31 | 0 | 50 | 52 |
| w0.55_o0.5_nonfast_A | 29 | 0 | 52 | 47 |
| w0.4_o1.0_any_B | 81 | 0 | 0 | 105 |
| w0.4_o1.0_non_moon_B | 64 | 3 | 14 | 95 |
| w0.4_o1.0_nonfast_B | 43 | 2 | 36 | 78 |
| w0.55_o1.0_any_B | 81 | 0 | 0 | 89 |
| w0.55_o1.0_non_moon_B | 58 | 2 | 21 | 81 |
| w0.55_o1.0_nonfast_B | 40 | 0 | 41 | 68 |

θ_p — самый сильный рычаг: `any` возвращает лунный шум (hero 79–81/81), `non_moon` снижает до 53–64/81, `non_fast` — до 35–38/81 (по hero_any). 76% всех якорей — лунные аспекты (Луна даёт точный аспект почти каждый день). Правило A (distinct technique_family) строже B (distinct driver): −5..7 hero-дней, т.к. несколько медленных транзитов разных планет схлопываются в одну семью «transit». B интерпретируемее («разные физические драйверы»).

## 4. Sanity check: «slow + major + planet/angle» ревьюера (ожидание ≈9/81)

- V0, точная спека (источник JUPITER..PLUTO, вес ≥0.85, цель планета/угол, orb ≤ профиля): **4/81** ['2026-06-24', '2026-07-08', '2026-07-23', '2026-08-03']
- V1_allow_lot_targets: **4/81**
- V2_sextile_counts_as_major: **7/81**
- V3_Mars_counts_as_slow_negative_control: **78/81**
- V5_slow_major_aspect_OR_timelord_member: **7/81**

Отклонение от ≈9/81: −5 по точной спеке (V0=4), −2 по ближайшим переинтерпретациям (V2 «секстиль считать мажором» = 7; V5 «медленный мажор ИЛИ time-lord как член группы» = 7, даты почти совпадают с V0). Негативный контроль V3 (Марс считать медленным) даёт 78/81 — подтверждает чувствительность спеки к границе «slow». Итог: порядок величины совпадает, расхождение объясняется выбором множества аспектов и членства time-lord'ов; rare_anchor-предикат на общей сетке (§2) даёт ту же зону (6–13/81) без специальных ограничений.

## 5. Кандидатные конфигурации (ландшафт, не квота)

| кандидат | θ_w | θ_o | θ_p | независимость | hero-предикат | hero/81 | rationale |
|---|---|---|---|---|---|---|---|
| **C1 (leading)** | 0.55 | 0.5 | non_fast | B | rare_anchor | 10/81 (12%) | колено по весу (sextile+, без quincunx-шума), полу-орб a priori защитим, hero = структурный якорь дня |
| C2 (strict) | 0.85 | 0.5 | non_fast | B | rare_anchor | 7/81 (9%) | только мажорные аспекты; самый чистый сигнал, но отсекает секстили медленных планет |
| C3 (loose) | 0.40 | 0.5 | non_fast | B | rare_anchor | 12/81 (15%) | quincunx+; больше покрытие, но quincunx — спорный «значимый» аспект по канону (вес 0.40) |

Трейдоффы: C1 сохраняет секстили медленных планет (в карте владельца это рабочая лошадка hero-дней — 4 из 10), C2 консервативнее и ближе к sanity-прокси ревьюера, C3 расширяет сигнал ценой шума. Все три — в дефенсибельной области (orb_fraction ≤ 0.5, без быстрых источников, структурный якорь); выбор между ними — продуктовый, не статистический.

## 6. Ведущий кандидат C1 — детально

Распределение состояний за 81 день: hero 10, convergence 25, single_impulse 8, no_anchor 38 (тихие дни: значимые единицы есть, якоря нет). Импульсов/день: min 40, медиана 47, p90 54, max 57.

### Hero-дни (дата — сфера — драйверы)

- **2026-06-15** — decisions (4 гр.): `aspect:SATURN:trine:natal_planet:MARS` [anchor_today, orb_f=0.00]; `activation:annual_profection__LORD_OF_YEAR__MARS` [background, orb_f=—]; `activation:solar_return__ANGULAR_PLANET__MARS__HOUSE_7` [background, orb_f=—]; `activation:lunar_return__ANGULAR_PLANET__MARS__HOUSE_7` [supporting, orb_f=—]; `activation:monthly_profection__LORD_OF_MONTH__MARS` [background, orb_f=—]
- **2026-06-18** — decisions (9 гр.): `activation:lunar_return__ANGLE_MC__NATAL_HOUSE_8` [anchor_today, orb_f=—]; `house:PLUTO:8` [supporting, orb_f=—]
- **2026-06-24** — decisions (4 гр.): `aspect:JUPITER:conjunction:angle:ASC` [anchor_today, orb_f=0.01]; `aspect:MARS:sextile:angle:ASC` [supporting, orb_f=0.34]
- **2026-07-01** — decisions (5 гр.): `aspect:JUPITER:sextile:natal_planet:VENUS` [anchor_today, orb_f=0.01]; `aspect:MARS:trine:natal_planet:VENUS` [supporting, orb_f=0.25]
- **2026-07-03** — communication (4 гр.): `aspect:JUPITER:sextile:natal_planet:JUPITER` [anchor_today, orb_f=0.01]; `activation:monthly_profection__LORD_OF_MONTH__JUPITER` [background, orb_f=—]; `aspect:MARS:trine:natal_planet:JUPITER` [supporting, orb_f=0.43]
- **2026-07-08** — decisions (7 гр.): `aspect:PLUTO:trine:natal_planet:SATURN` [anchor_today, orb_f=0.00]; `activation:firdar_minor__SUBPERIOD_LORD__SATURN` [background, orb_f=—]; `aspect:NEPTUNE:opposition:natal_planet:SATURN` [supporting, orb_f=0.06]; `aspect:URANUS:trine:natal_planet:SATURN` [supporting, orb_f=0.13]; `aspect:MARS:trine:natal_planet:SATURN` [supporting, orb_f=0.34]
- **2026-07-21** — decisions (7 гр.): `aspect:JUPITER:sextile:natal_planet:SATURN` [anchor_today, orb_f=0.01]; `activation:firdar_minor__SUBPERIOD_LORD__SATURN` [background, orb_f=—]; `aspect:NEPTUNE:opposition:natal_planet:SATURN` [supporting, orb_f=0.07]; `aspect:URANUS:trine:natal_planet:SATURN` [supporting, orb_f=0.02]; `aspect:PLUTO:trine:natal_planet:SATURN` [supporting, orb_f=0.06]
- **2026-07-23** — decisions (7 гр.): `aspect:URANUS:trine:natal_planet:SATURN` [anchor_today, orb_f=0.00]; `activation:firdar_minor__SUBPERIOD_LORD__SATURN` [background, orb_f=—]; `aspect:NEPTUNE:opposition:natal_planet:SATURN` [supporting, orb_f=0.07]; `aspect:PLUTO:trine:natal_planet:SATURN` [supporting, orb_f=0.07]; `aspect:JUPITER:sextile:natal_planet:SATURN` [supporting, orb_f=0.05]
- **2026-08-03** — communication (9 гр.): `aspect:JUPITER:conjunction:natal_planet:MOON` [anchor_today, orb_f=0.01]; `aspect:SUN:conjunction:natal_planet:MOON` [supporting, orb_f=0.44]; `aspect:SOLAR:opposition:natal_planet:MOON` [background, orb_f=0.09]; `aspect:SOLAR:trine:natal_planet:MOON` [background, orb_f=0.16]; `aspect:URANUS:sextile:natal_planet:MOON` [supporting, orb_f=0.49]
- **2026-08-12** — decisions (4 гр.): `activation:lunar_return__ANGLE_MC__NATAL_HOUSE_8` [anchor_today, orb_f=—]; `house:PLUTO:8` [supporting, orb_f=—]

### Три тихих дня (минимум значимых импульсов, не hero)

- **2026-07-12**: 40 значимых единиц, 0 якорей (нет якорей) → состояние no_anchor.
- **2026-07-13**: 41 значимых единиц, 0 якорей (нет якорей) → состояние no_anchor.
- **2026-07-14**: 41 значимых единиц, 1 якорей (`aspect:SUN:square:natal_planet:PLUTO`) → состояние convergence.

Пример трактовки hero-дня: 2026-07-08 — точный `PLUTO trine natal SATURN` (orb_f=0.00) плюс независимые подтверждения того же таргета: `NEPTUNE opposition SATURN`, `URANUS trine SATURN`, firdar sub-period SATURN. 2026-07-12 (тишина): 40 значимых единиц, все supporting/background, ни одного якоря — день без повода для акцента.

## 7. Аномалии и оговорки

- **Orb-покрытие**: 100.0% аспектных факторов имеют orb (activation: 10135, day_signal: 423); все 2259 факторов без orb — не-аспектные (house-ингрессии, time-lord'ы), для них орб-тест неприменим by design (пропускаются, учтены отдельно).
- Источники вне orb-профиля канона: SOLAR (1014) и PROGRESSED (307) — прогрессии; использован знаменатель 6.0°, их orb и так 0.5–1.3° (orb_f 0.08–0.2), искажения нет.
- Доля лунных якорей: 76% всех anchor_today — структурная причина 100% convergence в первом прогоне.
- **Мёртвый delta-trigger**: `classify_temporal_role` сравнивает `day_delta_dict` (голые имена планет вида «Moon») с полными factor_id/activation_id — совпадение невозможно, ветка `is_delta_trigger` не срабатывает никогда (прод-поведение, воспроизведено честно; кандидат на отдельный фикс).
- `is_rare` считает структурными ВСЕ time-lord семьи, включая ежемесячные lunar_return/monthly_profection — 2 из 10 hero-дней C1 (2026-06-18, 2026-08-12) обязаны именно lunar-return якорю; при желании «редкость = редкость» их можно исключить из rare-сета (−2 hero-дня).
- Доминирование сферы `decisions` (share 0.79–1.0) — артефакт планетных карт (SUN/MARS/SATURN/PLUTO/JUPITER все проецируются в decisions); маппинг сфер — отдельная тема калибровки.
- Группировка — connected components (транзитивное замыкание), а не якорные «звёзды» старого билдера; на решение «есть ли группа» влияет слабо, на состав — укрупняет.
- Горизонт одной карты и одного сезона (лето 2026, Pluto □ Sun и Neptune opp Saturn — перманентный фон); tense_streak=81 показывает, что фон этой карты всегда «tense» — калибровку валентности это не покрывает.
- Слой presentation (LLM) не моделировался (запрещён ограничениями задачи).
