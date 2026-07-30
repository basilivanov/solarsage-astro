# W1 FREEZE — независимый cross-check реальности (внешний аудитор, нулевой контекст)

Дата аудита: 2026-07-30. Аудитор: Kimi (независимый, read-only).
Объект: волна W1 «Today Convergence Rewrite» (`docs/work/2026-07-29_today-convergence-rewrite/`).
Метод: каждое утверждение авторов проверено по файлам и командам; авторам артефактов
не доверялось ничто, что нельзя воспроизвести. Файлы проекта не изменялись (кроме
этого отчёта). Сырые дампы (123 МБ), БД и `.env` не читались.

Разделяю три разных вопроса и не смешиваю их:

1. **Вычислительная корректность и воспроизводимость** — проверяема сейчас.
2. **Правдоподобное распределение** — проверяема как внутреннее свойство модели.
3. **Эмпирическая корреляция с реальной жизнью** — корпус синтетический, жизненных
   labels нет; частоты tone/hero НЕ подтверждены реальностью и в этом отчёте
   нигде не трактуются как подтверждённые.

---

## 1. CALCULATION: **PASS**

(с двумя обязательными гигиеническими действиями до freeze — см. §8: коммит
артефактов и бамп `CALCULATION_VERSION`; сама математика и воспроизводимость
упреков не вызывают)

Что проверено независимо:

- **Секта геометрическая, а не из номера дома.** `apps/solarsage/solarsage/services/activation_builder.py:572-573` —
  `is_day = sun_altitude_deg > 0.0`; высота — истинная (без рефракции),
  `apps/solarsage/solarsage/utils/ephemeris.py:144-164` (`swe.azalt`, true altitude).
  Firdar debug несёт `sect_basis: geometric_sun_altitude` и `sect_polar_condition`
  (`activation_builder.py:1293-1295, 1335-1337`). Полярный день/ночь — явные
  (`activation_builder.py:529-550`, 49 проб по 30 мин). Тесты:
  `apps/solarsage/tests/test_geometric_sect.py` (8 тестов: флип ровно на
  восходе/закате, независимость от house system, high-lat зима без ложных флипов,
  полярные условия, регресс на нормальных широтах) — **прогнаны, зелёные**.
- **Direct==HTTP parity** расчётного ядра: `apps/solarsage/tests/test_calculation_core.py`
  (natal/transits/activation-layer byte-equal direct vs HTTP; timing_scope
  не меняет evidence) — прогнан: `14 passed` (вместе с geometric_sect).
- **Воспроизводимость lineage:** `source_fingerprint()` из
  `analysis/generate_corpus_manifest.py:105-114` пересчитан аудитором по текущему
  дереву — совпал бит-в-бит с fingerprint манифеста и отчёта:
  `90c691f0a3282f75231668a430a623dbd9bf453273608e5fcc35518740671d0e`. SHA-256
  `corpus_replay_tone_v3.json` пересчитан — совпал с заявленным в
  `corpus_replay_tone_v3.md:18` (`1ee1e062…939d1`).
- **Sparse-oracle gate зелёный:** `analysis/ablation_final_summary.json:171-183`
  (violations 0 по всем стратам, каноническая маржа 3ч/4ч), разбор резидуалов
  fixture 9 — `analysis/ablation_sect_oracle.md:68-91` (честно: резидуал (a)
  27–32/бакет принципиально не нуль при консервативной марже; принят и
  задокументирован, а не скрыт).
- **Unit-тесты replay-цепочки:** `test_tone_policy_candidate.py` (6),
  `test_birthtime_replay.py` (3), `test_aggregate_corpus_shards.py` (3),
  `test_direct_replay_pipeline.py` (2) — **14/14 passed** (команда:
  `apps/api/.venv/bin/python -m pytest` в `analysis/`).

Оговорки (не блокируют корректность, см. Findings): код sect-fix и все
W1-артефакты — незакоммиченное рабочее дерево; `CALCULATION_VERSION`
(`packages/py-contracts/solarsage_contracts/versions.py:37` = `ss-calc-1.2.0`,
запинен в `packages/py-contracts/tests/test_versions.py:90`) не бампнут, хотя
фикс меняет firdar-лордов — кэши natal/activation без бампа не инвалидируются
(зафиксировано авторами как блокер выката, `verification_notes.md:18`).

## 2. TONE POLICY: **REVISE**

Механика кандидата подтверждена полным корпусным replay; promotion в канон и три
авторски объявленных решения ещё не закрыты.

Подтверждено аудитором:

- **Tense-inflation устранена, пустых дней не создано.** Из
  `analysis/corpus_replay_tone_v3.json` (проверено построчно скриптом):
  legacy-tense 80.82–82.74% дней → candidate tense 1.17–4.77%; `zero_public_days=0`
  во всех 6 режимах; `zero_selected_public_days` ≤ 2/87 600; median selected
  public units = 3. Диагноз «ошибка в свёртке, не в эфемеридах»
  (`02_TONE_POLICY_AMENDMENT.md:6-15`) подтверждается данными.
- **Числа MD воспроизводятся из JSON на 100%** по проверяемым полям: объём
  (120 карт × 730 дней × 6 режимов = 87 600/режим, 525 600 mode-days),
  120/120 ok, `invalid_ledger=0`, hero (exact 4.904%, night 1.373%, morning
  1.392%, day 1.397%, evening 1.390%, unknown 0.835%), steady/supportive/mixed/
  tense на 30 дней по всем режимам, legacy tense, streaks (max 4/3/2),
  P10–P90-независимые величины (min/median/max). Внутренняя согласованность JSON
  (суммы распределений = 87 600, hero_days = convergence_today, rates =
  counts/87600, tone.tense = tense_days) — проверена скриптом, расхождений нет.
- **Tone-gate «0 нарушений» верен по построению**: единственная ветка,
  присваивающая `tense`, требует `meaningful_tense` (high-conf anchor ИЛИ ≥2
  независимых fresh tense), `analysis/tone_policy_candidate.py:277-300`;
  аналогично supportive. Отдельного аудит-скрипта нет и не нужно — инвариант
  структурный (см. P2-6, если хотят явный audit).
- **Константы кандидата совпадают с каноном**: веса 1.0/0.5/0.0, split 0.5,
  min_side 0.25, margin 0.25, high_conf 0.75, ≥2 independent
  (`tone_policy_candidate.py:44-55` ↔ `grace/canon/today_convergence.v1.yml:146-176`).

Почему REVISE, а не PASS:

- канон `tone_policy.status: candidate_pending_replay` (`today_convergence.v1.yml:147`),
  хотя replay завершён (`02_TONE_POLICY_AMENDMENT.md:77`) — статус не продвинут;
- три авторски объявленных pre-freeze решения открыты
  (`02_TONE_POLICY_AMENDMENT.md:103-110`): owner-решение по hero-rate 4.9%,
  `dayTone` в public contract, per-group sphere cap gate;
- owner-side замер 68/81→4/81 (`02_TONE_POLICY_AMENDMENT.md:73-74`) взят из
  персонального дампа, в репозитории не воспроизводим (сами авторы честно
  пометили «числа диагностические») — как доказательство не засчитывался;
  подтверждением служит только корпус.

## 3. REAL-LIFE VALIDITY: **NOT PROVEN** (на текущих артефактах — UNMEASURABLE)

Корпус — 120 синтетических карт (`generate_corpus_manifest.py:123-163`,
`synthetic_only: True`), жизненных labels нет ни в checkpoints, ни в сводке.
Ничто в проверенных артефактах не позволяет утверждать, что tone/hero
коррелируют с прожитым днём. Авторы это не утверждают (`corpus_replay_tone_v3.md:6-8`,
master §14 — метрики отложены на 60–90 дней после cutover) — расхождений с
аудитом нет. Измеримость появится только после W3 (snapshot+check-in linkage) и
W5 (API) — план в §7 этого отчёта.

## 4. W1 FREEZE: **REVISE**

Ядро (модель + калибровка + tone fix + sect fix + oracle gate) выдерживает
независимую проверку. До freeze не хватает: продвижения канона из draft,
контрактного `dayTone`, исполняемого mutation suite 1–13 (сейчас ~5 из 13),
per-group cap gate, owner-решения по частоте hero, коммита артефактов и бампа
`CALCULATION_VERSION`. Всё перечисленное — дешёвые действия без повторного
полного replay (см. §8). BLOCK не оправдан: контр-примеров модели аудит не нашёл.

## 5. Таблица W1-gates

Критерий готовности W1 — master `00_MASTER_TZ.md:455` + §9 (`:352-405`) +
три решения из `02_TONE_POLICY_AMENDMENT.md:103-110`.

| # | Gate | Статус | Доказательство (проверено аудитором) | Недостающее действие |
|---|---|---|---|---|
| G1 | Machine-readable canon | **PARTIAL** | `grace/canon/today_convergence.v1.yml` существует и согласован с harness по eligibility/hero-targets/rare-set/orb/grouping/birth-time/tone-константам | статус `draft_pending_canon_compliant_rerun` (`:2-7`), measured-блок устарел (`:141-143`: exact 10 против T1 8/81), sphere limits не исполнены (F2), tone status stale (`:147`). Продвинуть + закоммитить |
| G2 | Исправленный re-run новым классификатором (дамп→sweep→C1→страты) | **DONE** | `ablation_report_v2.md` (F1–F8 кумулятивно), `ablation_t1_canon_align.json:27-42` (hero 8/81, выпавшие 06-04/06-17 объяснены), `ablation_sect_oracle.md:18-34` (страты), `corpus_replay_tone_v3.json` (120×730×6) | — |
| G3 | Sect-fix в движке до freeze | **PARTIAL** | код+тесты зелёные (см. §1), live A/B зафиксирован авторами (`verification_notes.md:17`) | коммит; бамп `CALCULATION_VERSION` + `test_versions.py:90` |
| G4 | Sparse-oracle gate зелёный | **DONE** | `ablation_final_summary.json:171-183` (0 нарушений, все страты); маржа каноническая 3ч/4ч (`birthtime_replay.py:65`) | — |
| G5 | Mutation suite 1–13 | **PARTIAL (~5/13)** | исполняемы: 8 (`ablation_sect_oracle.py:325`, `test_birthtime_replay.py:118`), 9 gate+diagnostic (`ablation_canonical_margin.py:148-152`), 11 (`ablation_sect_oracle.py:375`, `test_birthtime_replay.py:73`); по построению: 3 (`test_birthtime_replay.py:91-115`), 10 (identity включает polarity → presence fail, `birthtime_replay.py:94-100`) | изолированные фикстуры 1, 2, 4, 5, 6 — отсутствуют (rg `def test_` по `analysis/*.py`); 7 — только rg, runtime guard не реализован; 12 (W6) и 13 (W3) вне replay-scope — descope из W1-gate или реализовать позже |
| G6 | Согласованные state/content/API truth tables | **PARTIAL** | T1–T5 + матрица state×contentState (`00_MASTER_TZ.md:262-270`, canon `states`/`content_states`) | `dayTone` отсутствует в envelope (`00_MASTER_TZ.md:234-258`) и матрице; матрица state×dayTone×contentState не написана (авторы сами требуют: `corpus_replay_tone_v3.md:68-70`) |
| G7 | Tone-aware corpus replay | **DONE** | `corpus_replay_tone_v3.json/md`; fingerprint совпадает; тесты tone 6/6 | — |
| G8 | Owner-решение: hero-rate 4.9% (exact) против hypothesis 8–20% | **OPEN** | зафиксировано как открытое решение (`02_TONE_POLICY_AMENDMENT.md:105-107`, `corpus_replay_tone_v3.md:65-67`); owner probe 8/81=9.9% внутри гипотезы, population 4.9% ниже | решение владельца: принять ~1.5 hero/мес или пересмотреть определение (НЕ крутить пороги — master `00_MASTER_TZ.md:405,487`) |
| G9 | Per-group sphere cap gate (primary + ≤1 secondary) | **PARTIAL** | cap по построению: `project_group_spheres` возвращает ≤2 (`ablation_harness.py:859-862`); day-level диагностик `hero_sphere_span_gt2_days` (exact 196, `corpus_replay_tone_v3.json:277`) — НЕ доказывает per-group (`aggregate_corpus_shards.py:245-247`) | unit-test `len(g["spheres"]) ≤ 2` в classify_day_v2 + (опционально) точечный re-run с per-group записями; полный replay НЕ нужен |
| G10 | Group-level primary/secondary sphere отчёт (mapping skew work 2683 / money 1704) | **OPEN** | числа есть только в `corpus_replay_tone_v3.md:74-76`; в committed JSON per-sphere counts отсутствуют; checkpoints локально отсутствуют | точечный отчёт (exact mode или подвыборка) или задокументировать как post-freeze; НЕ полный replay |
| G11 | Full dense oracle (диагностика) | **DEFERRED авторами** | `corpus_replay_tone_v3.md:77-79` — явно вынесен за рамки tone-вывода | согласовать перенос (приемлемо: gate уже зелёный на стратифицированном oracle) |
| G12 | Коммит артефактов по §9 | **NOT MET** | `git status`: 111 M/?? записей; канон/мастер модифицированы, весь `analysis/` tone-v3 и sect-fix — untracked/uncommitted; последний коммит `a9060308` | коммит ревьюером (скрипты+MD+summary JSON+checksum+команда — всё есть на диске) |
| G13 | Регистрация W1 в verification-matrix | **NOT MET** | `grace/verification-matrix.md` не содержит строк W1/today-convergence (rg) | добавить строки волн по master `00_MASTER_TZ.md:466` |
| G14 | Один путь replay (runner vs replay) | **OPEN** | дубликат зафиксирован авторами (`verification_notes.md:24`); v3 произведён `corpus_replay.py`; `corpus_runner.py` checkpoints без schema/fingerprint/tone (`corpus_runner.py:306-332`) | пометить `corpus_runner.py` superseded или удалить |

## 6. Findings

P0 — **нет**. Ни одного факта, опровергающего модель или зануляющего доверие к
числам, аудит не нашёл; все проверяемые числа MD воспроизводятся.

### P1-1. Канон — draft с устаревшим measured-блоком

- Симптом: `grace/canon/today_convergence.v1.yml:2` `status: draft_pending_canon_compliant_rerun`;
  `:141-143` measured hero exact=10, тогда как T1-артефакт того же репозитория
  фиксирует 8/81 (`analysis/ablation_t1_canon_align.json:27-42`, выпавшие дни
  объяснены: lot-target и MOON-witness), а population corpus — 4.9%.
- Механизм: T1 re-run и full replay произошли после написания канона; канон не
  продвинут. Master запрещает W2 до утверждения канона (`00_MASTER_TZ.md:5`).
- Проверка, способная опровергнуть: если draft-статус — осознанная фиксация
  pre-T1 baseline, это честно; но тогда gate G1 формально не выполнен.
- Минимальное исправление: обновить measured (T1 8/81 + корпусные частоты по
  режимам), `status → approved/frozen`, убрать устаревший DRAFT-комментарий.
- Blast radius: только документ/норматив. Rollback: git revert.

### P1-2. Канон sphere mapping не совпадает с измеренной реализацией

- Симптом: канон `planet_sphere_limits: max 2/планету, decisions: [SATURN, PLUTO]`
  (`today_convergence.v1.yml:86-88`), но replay использовал СТАРУЮ карту
  `PLANET_TO_PRODUCT_MAP` (`apps/api/app/services/today_focus_builder.py:91-102`:
  MARS/JUPITER/SATURN — по 3 сферы, decisions у 6 планет) через
  `analysis/direct_replay_pipeline.py:205` (`strict_product_spheres`).
- Механизм: пересмотренная карта — кандидат из `ablation_report_v2.md:91-106`,
  в код не перенесена; v3-числа по сферам измерены на старой карте.
- Проверка, способная опровергнуть: hero/tone частоты от карты НЕ зависят —
  группировка идёт по target/theme (`ablation_harness.py:125-149, 823-836`),
  сферы проецируются ПОСЛЕ группировки (`:977-1004`). Опровержение подтвердилось:
  расхождение бьёт только по sphere-атрибуции и fan-out статистикам, не по
  hero/tone. Поэтому P1, а не P0.
- Минимальное исправление: либо (а) перенести ревизию карты в общий модуль +
  точечная sphere-переоценка (без полного replay), либо (б) явно пометить
  mapping в каноне как candidate и заморозить только правило проекции
  (`group_to_spheres`, `secondary_max: 1` — оно исполнено).
- Blast radius: метки сфер W2+ и sphere-диагностики v3. Rollback: старая карта
  за флагом.

### P1-3. Mutation contract 1–13 исполнен частично

- Симптом/механизм: изолированных фикстур 1 (два лунных аспекта → не hero),
  2 (producer parity → один unit), 4 (две независимые техники → hero только с
  rare), 5 (транзитивная цепочка), 6 (одиночное событие → main_event) в
  `analysis/` нет (rg `def test_`, `fixture`, `mutation`); fixture 7 — только
  rg-проверка, runtime guard отсутствует; 12/13 относятся к W6/W3. Master
  требует полный suite в критерии W1 (`00_MASTER_TZ.md:384-401, 455`).
- Опровержение: семантика 1/4 покрыта корпусом статистически (быстрые источники
  не rare_anchor по коду, `ablation_harness.py:730-744`; hero только с rare
  якорем, `:898-918`), 3/10/11 — unit-тестами и построением. Т.е. поведение
  правильное, но контракт «явные изолированные фикстуры» не выполнен буквально.
  Отдельно: `main_event` (D11) в классификаторе/replay не моделируется вообще —
  fixture 6 нечем исполнять до W2.
- Минимальное исправление: `test_mutation_fixtures.py` на `classify_day_v2`
  (синтетические списки units, без эфемерид — дёшево) для 1,2,4,5; для 7 —
  assert/guard в новом пайплайне; 12/13 — явный descope из W1-gate в тексте
  мастера. Старые noon-fallback'и (`today_service.py:334`, `calendar_service.py:316`)
  — legacy-пути под суперсединг W2/W8, дефектом W1 не считаются.
- Blast radius: тесты. Rollback: n/a.

### P1-4. `dayTone` отсутствует в public contract

- Симптом: envelope `00_MASTER_TZ.md:234-258` и матрица `:262-270` не содержат
  `dayTone`; канон `states`/`content_states` — тоже. При этом корпус считает
  `day_tone` для каждого дня (`corpus_replay.py:172-173`).
- Механизм: осознанно отложено (`02_TONE_POLICY_AMENDMENT.md:107-109`,
  `corpus_replay_tone_v3.md:68-70`), но это pre-freeze решение по авторскому же
  списку. Без контракта UI сможет трактовать `quiet_day + steady` как пустой
  экран — именно то, чего rewrite избегает (вопрос 12 ТЗ).
- Минимальное исправление: добавить `dayTone` (nullable, enum 4 значения) в
  envelope + строки матрицы state×dayTone×contentState + норматив «quiet+steady
  показывает импульсы/контекст». Поле аддитивно, replay не нужен — day_tone уже
  посчитан для всех 525 600 mode-days.
- Blast radius: W5 API schema, W7 frontend. Rollback: nullable-поле, обратно
  совместимо.

### P1-5. Артефакты freeze не закоммичены

- Симптом: 111 изменённых/untracked записей (`git status`), включая канон,
  мастер, весь tone-v3 набор, sect-fix и его тесты; lineage-fingerprint
  `90c691f0…` покрывает файлы рабочего дерева — потеря/загрязнение дерева рвёт
  воспроизводимость.
- Механизм: коммит/пуш — прерогатива ревьюера (master `:8`), ещё не выполнено.
- Минимальное исправление: один коммит-сет по §9 (`00_MASTER_TZ.md:364-366`);
  сырые дампы уже gitignored (`analysis/.gitignore`).
- Blast radius: нет. Rollback: n/a.

### P1-6. Owner-решение по частоте hero не принято

- Симптом: population exact 4.9% (1.47/30д) ниже monitoring-гипотезы 8–20%
  (`corpus_replay_tone_v3.json:276`; гипотеза `today_convergence.v1.yml:143`);
  owner probe 8/81=9.9% — внутри гипотезы (`ablation_t1_canon_align.json:27`).
  Расхождение «одна карта vs population» — ожидаемое (owner карта небелая
  выборка: chart hero rate min–max 2.05–8.2%), но продуктовую частоту должен
  принять владелец, а не статистика.
- Механизм: авторы корректно запретили подгонку (`00_MASTER_TZ.md:405, 487`;
  `corpus_replay_tone_v3.md:66-67`). Аудит подтверждает: в коде и отчётах следов
  подгонки под квоту нет (пороги 0.55/0.5 зафиксированы до full replay —
  `ablation_report_v2.md`, landscape опубликован целиком).
- Минимальное исправление: решение владельца, записанное в канон/мастер.

### P1-7. Per-group sphere cap: доказательства как gate нет

- Симптом: cap существует только по построению
  (`ablation_harness.py:859-862`: primary + secondary при ≥2 голосах); ни теста,
  ни агрегированного gate в committed артефактах. `hero_sphere_span_gt2_days`
  — day-level union всех групп (`aggregate_corpus_shards.py:245-247`) и по
  построению не отличает легитимные 2+ группы от fan-out одной (authors:
  `corpus_replay_tone_v3.md:71-73`).
- Опровержение: поскольку cap — тотальное свойство кода (tuple длиной ≤2),
  контр-пример возможен только при обходе `project_group_spheres`; такой путь в
  `classify_day_v2` отсутствует (`:977-1004`). Значит риск — отсутствие
  регрессионной защиты, а не текущее нарушение.
- Минимальное исправление: unit-test + assert в классификаторе; исторический
  per-group отчёт — точечный re-run (не полный).

### P2 (не блокируют freeze; список сокращён до существенного)

- **P2-1.** P10–P90 и hero sphere counts (work 2683/money 1704) не воспроизводимы
  из committed JSON (только min/median/max; per-sphere counts отсутствуют);
  checkpoint-набор на этом хосте отсутствует (`/var/tmp/solarsage-replay-*` не
  найден); 14-day local/server parity pilot (`corpus_replay_tone_v3.md:29`) —
  тоже вне committed артефактов. Fix: коммитить компактный per-chart quantile
  JSON или durable-ссылку на архив checkpoints.
- **P2-2.** Дублирующие runner'ы (`corpus_runner.py` vs `corpus_replay.py`),
  авторы сами требуют выбрать один (`verification_notes.md:24`).
- **P2-3.** `_is_fresh` продвигает supporting-юнит с `exact_at` сегодня в fresh
  (`tone_policy_candidate.py:92-99`) — в каноне/амендменте fresh = только
  `anchor_today` (`today_convergence.v1.yml:163`). Семантически разумно, но
  недокументировано; corpus измерен именно с этим правилом.
- **P2-4.** `ablation_final_summary.json:18` пишет «apparent altitude», код
  использует true unrefracted (`ephemeris.py:156-164`; конвенция зафиксирована в
  `test_geometric_sect.py:146-153`). Косметика.
- **P2-5.** `CALCULATION_VERSION` не бампнут (см. §1). Реальный дедлайн — первый
  деплой, несущий sect-fix (кэши), но дешевле сделать с коммитом G12.
- **P2-6.** Явного tone-gate audit-скрипта нет — инвариант структурный
  (`tone_policy_candidate.py:293-300`), но одна страница кода над daily rows
  сделала бы claim проверяемым третьей стороной без чтения реализации.
- **P2-7.** Fixture 12 (LLM once) и 13 (unknown→exact hash) включены в W1-gate
  текста мастера, но относятся к W6/W3 — внутреннее противоречие критерия;
  descope явно.
- **P2-8.** Корпус: дни рождения только 10–20 числа (`generate_corpus_manifest.py:132`),
  все карты PLACIDUS-запрос (high-lat fallback при этом покрыт широтами ≥60).
  Для проверки механики достаточно; расширение seed-диапазона — опционально.

## 7. План live-валидации (после W3/W5, горизонт 60–90 дней по master §14)

Предпосылки, уже спроектированные в мастере и подтверждённые аудитом как
непротиворечивые: `forecast_snapshot_id` + FK owner/date validation
(`00_MASTER_TZ.md:313`), `prediction_seen_at` через server-side impression, а
не через строку check-in (`:303-305`), `observed_spheres[]` мультиселект (`:314`),
immutability published snapshot (`:298-299`). В API сейчас этих полей нет
(rg по `apps/api` — пусто; ожидаемо, это W3).

Метрики (все — раздельно по `birth_time_mode` exact/bucket/unknown; bucket'ы при
малом n объединять, unknown отдельно):

- **M1 sphere-hit precision:** P(≥1 `observed_spheres` ∈ выбранных сфер |
  impression дня с выбранными сферами). Базовая линия — маргинальная частота
  репорта тех же сфер у того же пользователя; **lift = precision / personal
  baseline** (не population baseline — иначе популярные сферы симулируют skill).
- **M2 coverage/recall:** P(сфера предсказана | сфера наблюдалась).
- **M3 tone-precision (weak label):** среди увиденных tense-дней — доля check-in
  с негативной комбинацией тегов/низким mood; symmetric для supportive. Mood —
  резонанс дня, не полярность сферы (`00_MASTER_TZ.md:316`) — трактовать как
  weak label, не ground truth.
- **M4 copy resonance:** «попал/частично/мимо» — метрика резонанса, не истины
  (master §14).
- **M5 within-person:** тот же пользователь, дни hero/convergence vs согласованные
  quiet-дни (тот же weekday, ±2 недели): разница M1/M3. Контролирует личные
  эффекты без рандомизации.
- **M6 product:** check-in rate, retention (мастер §14, ориентиры a16z уже
  записаны).

Оценка объёма (из корпусных частот exact: hero 4.9%, tense 4.8%, supportive
6.5%; bucket≈1.4%, unknown≈0.8–1.2%; допущения: check-in rate r=0.3, доля
impression-linked q=0.8; цель — ≥100 событий на метрику, 95% CI ≈ ±10 п.п.):

- exact: 100/(0.049·0.24) ≈ **8 500 person-days** на hero/tense; ≈6 400 на
  supportive → **100 пользователей × 85–90 дней** или 150 × 60 дней.
- unknown/bucket по отдельности: 100/(0.012·0.24) ≈ **35 000 person-days** —
  недостижимо в v1; для них в v1 только M4/M6 и pooled impulse-level M1, честные
  выводы по tone отложить.
- Минимальный порог для любых выводов: ≥80–100 событий на метрику/страту; ниже —
  только описательная статистика, без verdict'ов.

Итоговая оценка: **6 000 person-days (100×60)** — go/no-go с CI ±12 п.п.;
**13 500–18 000 (150–200 × 90)** — ±8 п.п. и грубый exact/bucket сплит.

## 8. Финальные списки

**Сделать до freeze (всё — без повторного полного corpus replay):**

1. Продвинуть канон: measured → T1 8/81 + корпусные частоты, status → approved,
   тон-блок status → replay-verified (P1-1, P2-3 заодно).
2. Закрыть расхождение sphere mapping: вариант (а) ревизия карты + точечная
   sphere-переоценка, или (б) canon mapping → candidate (P1-2).
3. `dayTone` в envelope + матрица state×dayTone×contentState + норматив
   «quiet+steady ≠ пустой экран» (P1-4).
4. Owner-решение по hero-rate 4.9% (P1-6).
5. `test_mutation_fixtures.py` для 1,2,4,5 (+descope 12/13, guard для 7) (P1-3).
6. Per-group cap unit-test/assert (P1-7).
7. Коммит всех W1-артефактов (P1-5) + бамп `CALCULATION_VERSION` с правкой
   `test_versions.py` (P2-5).
8. Регистрация W1 в `grace/verification-matrix.md` (G13); пометить
   `corpus_runner.py` superseded (G14).

**Можно оставить после freeze:**

1. Full dense oracle (G11) — дорогая диагностика, gate уже зелёный.
2. Group-level primary/secondary sphere отчёт и P10–P90 в committed артефактах
   (G10, P2-1) — как durable-архив checkpoints.
3. Runtime guard fixture 7 против legacy-путей — реально закрывается в W2/W8.
4. Live-валидация (§7) — после W3/W5, горизонт 60–90 дней.
5. Per-strata (bucket/unknown) tone precision — после накопления ≥35k person-days
   или объединения страт.
6. Расширение корпуса (дни 1–9/21–31, не-PLACIDUS запросы) (P2-8).
7. Явный tone-gate audit-скрипт (P2-6), косметика «apparent» (P2-4).

## 9. Что можно и нельзя обещать пользователю до live-данных

**Можно** (подтверждено вычислительно): детерминизм и воспроизводимость; честные
режимы неопределённого времени (только устойчивые факты; без подстановки 12:00;
без домов/ASC/лотов при bucket/unknown); «сошлось» — редкое событие по явному
замороженному правилу; внутренние частоты модели как свойство модели
(«сколько раз модель говорит X»), поданные как модельные, не жизненные.

**Нельзя** (не подтверждено): любые hit-rate/accuracy-обещания («прогноз
сбывается»); «точное время даёт в N раз больше особенных дней» (уже non-goal,
`00_MASTER_TZ.md:488`); трактовку `evidence_level` как confidence до живой
валидации (D5); частоты tone как статистику реальной жизни.

## 10. Steady-день как экран (вопрос 12 ТЗ)

Остаётся содержательным — по контракту, не по надежде: quiet_day несёт 0–3
импульса (median selected = 3 во всех режимах, `corpus_replay_tone_v3.json`),
детерминированный period context, статический навигатор со страницами сфер
(D8/D10, `00_MASTER_TZ.md:78-80`), main_event (D11). Дней с 0 выбранных units —
≤2/87 600 на режим; для них D2 честно оставляет только нейтральный контекст.
Единственное узкое место — отсутствие `dayTone` в контракте (P1-4): без него
фронт сможет сплющить quiet+steady в «пустышку». После добавления поля и
норматива риск закрыт. Текущий старый frontend дефектом W1 не считается —
будущий контракт (T4/T5 + §16 + D8) его замену описывает однозначно.

---

### Приложение A. Команды, которыми проверял аудитор

```bash
# числа MD против JSON + внутренняя согласованность (все assert'ы зелёные)
python3 -  # сверка modes/*: суммы=87600, hero_days=convergence_today, rates, tone
sha256sum corpus_replay_tone_v3.json            # == 1ee1e062…939d1 (как в MD)
python3 -c "from generate_corpus_manifest import source_fingerprint; print(source_fingerprint())"
# == 90c691f0…71d0e == manifest == v3 json
cd analysis && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  test_tone_policy_candidate.py test_birthtime_replay.py test_aggregate_corpus_shards.py -q   # 12 passed
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest test_direct_replay_pipeline.py -q    # 2 passed
cd apps/solarsage && venv/bin/python -m pytest tests/test_geometric_sect.py tests/test_calculation_core.py -q  # 14 passed
git status --short   # 111 M/?? — артефакты W1 не закоммичены (последний коммит a9060308)
```

### Приложение B. Проверка чисел MD → JSON (выборка)

| MD (`corpus_replay_tone_v3.md`) | JSON | Итог |
|---|---|---|
| 87 600/режим, 525 600 total | `days: 87600` × 6 режимов | OK |
| exact: hero 4.904%, tense 4.77%, legacy 82.74%, streak 4, 1.47/30d | `0.049041 / 0.047728 / 0.827374 / max 4 / ×30=1.471` | OK |
| bucket: legacy 80.83–80.93%, tense 1.40–1.42%, streak 3, 0.41–0.42/30d | night/morning/day/evening пересчитаны поштучно | OK |
| unknown: 0.835%, tense 1.17%, streak 2, 0.25/30d | `0.008345 / 0.011655 / 2 / 0.250` | OK |
| steady/supportive/mixed/tense на 30д (все режимы) | пересчёт counts×30/87600 — совпало до сотых | OK |
| zero_public_days=0; дней без selected: exact 0, bucket 1–2, unknown 2 | `zero_public_days`, `zero_selected_public_days` | OK |
| exact non-steady ≈5.2/30д | (5660+5361+4181)×30/87600 = 5.21 | OK |
| hero_sphere_span_gt2 exact = 196 | `:277` | OK |
| P10–P90; work 2683 / money 1704 | в JSON отсутствуют | НЕ воспроизводимо из committed (P2-1) |
| min одной unknown-карты = 0 hero/2 года | `chart_hero_rate_min: 0.0` | OK |
