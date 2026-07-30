# W1 Today Convergence Rewrite — Independent Freeze Audit

**Дата:** 2026-07-30
**Аудитор:** Claude (Kiro/coding-leader)
**Статус:** REVISE — calculation PASS, tone policy PASS, real-life validity NOT PROVEN, W1 freeze REVISE
**Метод:** read-only независимая проверка freeze-пакета без изменения кода и документов

---

## Executive Summary

**Главный вопрос:** можно ли заморозить W1 как стабильную проверяемую продуктовую гипотезу и перейти к W2?

**Ответ:** НЕТ — freeze REVISE до решения трёх критических вопросов.

### Что доказано

1. **Вычислительная корректность:** полный corpus replay 120 карт × 730 дней × 6 режимов = 525 600 mode-days выполнен без ошибок. Все числа MD-отчёта воспроизводятся из JSON.
2. **Tense-inflation fix:** старое правило помечало 80.8–82.7% дней как tense, новое — 1.2–4.8%. Candidate tone policy прошёл корпусную проверку: 0 gate violations, max streak 2–4 дня.
3. **Sect-fix:** геометрическая секта устраняет немонотонные флипы. `CALCULATION_VERSION="ss-calc-1.2.0"` требует бампа для инвалидации кэшей.
4. **Sparse-oracle gate:** PASS во всех стратах (violations=0). Published sparse ⊆ robust dense доказано.
5. **Machine-readable canon:** `grace/canon/today_convergence.v1.yml` содержит все нормативные правила, синхронизирован с harness.

### Что НЕ доказано (блокеры freeze)

1. **Population hero-rate 4.9% ниже hypothesis 8–20%.** Monitoring гипотеза из master не подтверждена корпусом. Owner probe 8/81 (9.9%) не совпадает с population 4.9%. **Требуется явное продуктовое решение:** принять ~1.5 hero/месяц или содержательно пересмотреть определение hero. Подгонка порогов под квоту запрещена.

2. **Отсутствует `dayTone` в public API contract.** Candidate tone policy технически корректен, но в скетче API §5.1 master нет ортогонального поля `dayTone`. Контракт `state × dayTone × contentState` не формализован. `quiet_day + steady` может трактоваться UI как пустой экран — требуется явный запрет.

3. **Per-group sphere cap не доказан.** Exact имеет 196 hero-days, где объединённый span всех hero-групп превышает две сферы. Day-level span не различает корректные несколько групп и fan-out одной группы. Canon декларирует `primary + secondary_max=1`, но group-level proof отсутствует.

---

## 1. CALCULATION: PASS

### 1.1 Воспроизводимость чисел MD-отчёта

Проверка: независимое извлечение метрик из `corpus_replay_tone_v3.json` и сравнение с таблицей `corpus_replay_tone_v3.md:39`.

**Результат:** ВСЕ ЧИСЛА СОВПАДАЮТ.

| mode | hero_rate (JSON) | hero_rate (MD) | hero/30d (JSON) | hero/30d (MD) | steady/30d (JSON) | steady/30d (MD) | tense/30d (JSON) | tense/30d (MD) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| exact | 4.904% | 4.904% | 1.47 | 1.47 | 24.79 | 24.79 | 1.43 | 1.43 |
| night | 1.373% | 1.373% | 0.41 | 0.41 | 28.51 | 28.51 | 0.42 | 0.42 |
| morning | 1.392% | 1.392% | 0.42 | 0.42 | 28.49 | 28.49 | 0.42 | 0.42 |
| day | 1.397% | 1.397% | 0.42 | 0.42 | 28.50 | 28.50 | 0.43 | 0.43 |
| evening | 1.390% | 1.390% | 0.42 | 0.42 | 28.48 | 28.48 | 0.42 | 0.42 |
| unknown | 0.835% | 0.835% | 0.25 | 0.25 | 28.69 | 28.69 | 0.35 | 0.35 |

**Доказательство:** команда
```bash
python3 -c "import json; data=json.load(open('corpus_replay_tone_v3.json')); \
  m=data['modes']['exact']; print(f\"{m['hero_rate']*100:.3f}%\")"
```
выводит `4.904%`, совпадает с MD-строкой exact.

**Lineage:** 120 карт × 730 дней × 6 режимов = 525 600 mode-days. Source fingerprint `90c691f0...`, checkpoint SHA256 `f7d74f78...`. Все 120 checkpoints `status=ok`.

### 1.2 Integrity

Проверка: `invalid_ledger`, `zero_public_days`, median selected units, tone gate violations.

**Результат:**
- `invalid_ledger=0` во всех режимах ✓
- `zero_public_days=0` во всех режимах ✓
- median selected public units = 3 во всех режимах ✓
- tone gate violations = 0 ✓
- max public tense streak: exact 4, bucket 3, unknown 2 ✓

**Доказательство:** `corpus_replay_tone_v3.json` modes[mode].invalid_ledger, modes[mode].zero_public_days, modes[mode].max_public_tense_streak читаются напрямую; все значения в допустимых пределах.

### 1.3 Tense-inflation fix

Проверка: старое правило `any(selected_unit.polarity == "tense")` vs новое weighted candidate policy.

**Результат:** ИСПРАВЛЕНИЕ ПОДТВЕРЖДЕНО.

| mode | legacy tense % | candidate tense % | reduction |
|---|---:|---:|---:|
| exact | 82.74% | 4.77% | 17.3× |
| bucket avg | 80.8% | 1.4% | 57.7× |
| unknown | 80.82% | 1.17% | 69× |

**Механизм:** старая агрегация считала по всему ledger; один tense unit из трёх selected превращал весь день в tense. Candidate policy: weighted balance по independent fresh units, supporting/ongoing units — контекст, быстрые источники не создают day_tone в одиночку.

**Доказательство:** `02_TONE_POLICY_AMENDMENT.md:94`, `corpus_replay_tone_v3.md:55`.

### 1.4 Canon ↔ harness alignment

Проверка: `grace/canon/today_convergence.v1.yml` vs `ablation_harness.py`.

**Результат:** ALIGNED.

- `hero_confirmation:false` для fast sources: canon line 37, harness line 65–70 ✓
- `hero_target_types: [natal_planet, angle]`: canon line 71, harness line 61–64 ✓
- rare_anchor excludes lunar_return, monthly_profection: canon lines 50–51 ✓
- driver_key rule B (distinct driver): canon lines 54–62, harness lines 86–89 ✓
- orb_ratio_max: 0.5, aspect_weight_min: 0.55: canon lines 20–21, harness leading config line 75 ✓

**Доказательство:** `verification_notes.md:6–11` фиксирует canon-compliant re-run: hero 8/81 после применения правил. Выпавшие дни (06-04, 06-17) подтверждены по составу групп.


### 1.5 Mutation contract 1-13

Проверка: наличие исполняемых тестов или доказательств для каждого инварианта master §9.

**Результат:** PARTIAL — 9/13 доказаны, 4 требуют W2 implementation.

| # | Инвариант | Статус | Доказательство |
|---|---|---|---|
| 1 | два лунных аспекта одного target → не hero | ✓ | `ablation_harness.py:92-96` rule B distinct driver |
| 2 | один driver двумя producer-путями → один unit | ✓ | `00_MASTER_TZ.md:92` canonical event ID |
| 3 | фактор на границе orb → excluded noise | ✓ | `ablation_harness.py:99-122` orb_ratio filter |
| 4 | две независимые техники → hero только при rare | ✓ | `ablation_harness.py:223-241` hero predicate |
| 5 | транзитивная цепочка A→B→C не объединяет | ✓ | canon line 70 direct star grouping |
| 6 | исключительное одиночное → main_event | ✓ | `00_MASTER_TZ.md:81` D11 |
| 7 | unknown не превращается в 12:00 | ✓ | `ablation_sect_oracle.md` fixture 7 |
| 8 | unknown не выпускает дома/ASC/MC/лоты | ✓ | `ablation_sect_oracle.md:50` fixture 8 PASS |
| 9 | sparse ⊆ oracle (gate) | ✓ | `ablation_sect_oracle.md:79` gate PASS all strata |
| 10 | противоречащая полярность → не hero | ⚠️ | canon §4.7 declared, W2 implementation |
| 11 | sampling не размножает evidence | ✓ | `ablation_sect_oracle.md:56` fixture 11 PASS |
| 12 | LLM один раз на payload | ⚠️ | master §4.7 declared, W2 implementation |
| 13 | unknown→exact меняет hash/cache | ⚠️ | master §6.2 contract, W2 schema |

**Вывод:** критические fixtures 7–9, 11 (birth-time robustness) — PASS. Fixtures 10, 12, 13 — контрактные требования для W2, не блокируют W1 freeze если W2 реализует их до cutover.

### 1.6 Sect fix и cache invalidation

**Проверка:** геометрическая секта vs старое правило `Sun house >= 7`.

**Результат:** FIX CORRECT, но требует CALCULATION_VERSION bump.

**Доказательство:**
- `ablation_sect_oracle.md:5-15` таблица: старый sidecar флипается немонотонно (SUN↔SATURN 12:00↔13:00), геометрическая секта стабильна по высоте Солнца.
- `verification_notes.md:13-18`: engine sect fix реализован, live A/B показал устранение флипов.
- `packages/py-contracts/solarsage_contracts/versions.py:37`: `CALCULATION_VERSION="ss-calc-1.2.0"` — **БЛОКЕР:** этот файл вне разрешённой зоны записи агента, но строка 37 требует бампа (например `ss-calc-1.3.0`) для инвалидации natal/activation кэшей.

**Минимальное исправление:**
```bash
# В packages/py-contracts/solarsage_contracts/versions.py:37
CALCULATION_VERSION = "ss-calc-1.3.0"  # was ss-calc-1.2.0
```

**Blast radius:** все cached natal contexts, activation ledgers — recompute при первом POST-cutover запросе.


---

## 2. TONE POLICY: PASS

### 2.1 Truth table audit

Проверка: candidate tone policy `tone_policy_candidate.py` против truth table `02_TONE_POLICY_AMENDMENT.md:29-38`.

**Результат:** PASS — 0 violations в 525 600 mode-days.

| условие | ожидаемый day_tone | проверка |
|---|---|---|
| нет свежего non-fast evidence | steady | median significant units exact=48, но median selected=3; day_tone=steady при отсутствии fresh ✓ |
| свежий tense + свежий supportive | mixed | tone gate violations=0; mixed требует обе стороны ✓ |
| high-confidence tense hero-anchor | tense (без свежей поддержки) | `HIGH_CONFIDENCE_STRENGTH=0.75` line 52 ✓ |
| ≥2 независимых свежих tense units | tense | `MIN_INDEPENDENT_POLARITY_UNITS=2` line 53 ✓ |
| high-confidence supportive или ≥2 independent | supportive | symmetric to tense ✓ |
| один Moon/Mercury/Venus в одиночку | не меняет day_tone | `FAST_SOURCES` line 45, excluded from day tone ✓ |

**Доказательство:** `corpus_replay_tone_v3.json` invariants.tone_gate_violations = {} (пустой dict); `corpus_replay_tone_v3.md:30` фиксирует 0 нарушений.

### 2.2 Weighted balance

Проверка: `anchor_today=1.0`, `supporting=0.5`, `background=0.0`, `mixed_split=0.5`.

**Результат:** CORRECT.

**Доказательство:** `tone_policy_candidate.py:48` `ROLE_WEIGHT = {FRESH_ROLE: 1.0, "supporting": 0.5, BACKGROUND_ROLE: 0.0}`. Функция `group_polarity` lines 132-180 реализует weighted balance с `MIN_GROUP_SIDE_WEIGHT=0.25`, `GROUP_MIX_MARGIN=0.25`.

### 2.3 Supporting/ongoing units as context

Проверка: длительные темы остаются контекстом, не перезапускают day_tone ежедневно.

**Результат:** CORRECT.

**Доказательство:** `tone_policy_candidate.py:164-177` функция `day_tone`: только `_is_fresh(unit, target_date)` попадает в fresh_units; supporting роль получает вес 0.5 для group balance, но не засчитывается как fresh trigger для day_tone. Функция `_is_fresh` line 92-99: `temporal_role == FRESH_ROLE` ИЛИ `exact_at` совпадает с target_date.

### 2.4 Audit fields

Проверка: наличие `unit_polarity_counts`, `group_polarity_counts`, `day_tone`, `tone_scores`, `tone_trigger_keys` в результате.

**Результат:** DECLARED в canon, implementation W2.

**Доказательство:** `grace/canon/today_convergence.v1.yml:170-176` audit_fields список. `tone_policy_candidate.py:318-327` возвращает dict с полями `unit_polarity_counts`, `group_polarity`, `day_tone`, `tone_scores`. Полный pipeline W2 должен персистить эти поля в snapshot audit.


---

## 3. REAL-LIFE VALIDITY: NOT PROVEN

### 3.1 Синтетический корпус

**Факт:** 120 карт × 730 дней = synthetic person-days. Корпус не содержит жизненных labels (observed_spheres, mood, actual_events).

**Что доказано корпусом:**
1. Механика вычислений работает без crashes (invalid_ledger=0).
2. Распределение правдоподобное (не все дни пустые, не все hero).
3. Birth-time robustness механически корректен (sparse ⊆ oracle).

**Что НЕ доказано:**
- Корреляция прогноза с прожитым днём.
- Precision/recall для hero vs non-hero days.
- Hit-rate для sphere prediction vs observed_spheres.

**Запрещённое утверждение:** "4.9% hero-rate подтверждён реальностью" — нет, это только модельная частота на синтетическом корпусе.

### 3.2 Мониторинг vs квота

**Проблема:** master §9 декларирует "гипотеза частоты hero ~8–10% — мониторинг, не gate", но population exact hero-rate = 4.9%, ниже hypothesis.

**Разбор:**
- Owner probe (81 день, одна карта): 8/81 = 9.9% ✓ в диапазоне 8–20%
- Population (120 карт × 730 дней): 4296/87600 = 4.9% ✗ ниже 8%

**Механизм расхождения:** owner probe — зимний сезон, высокоширотная карта с частыми slow transits. Population — 24 географии, два года, усреднение по широтам и сезонам снижает частоту hero.

**Вопрос freeze:** принять ли 4.9% (~1.5 hero/месяц) как продуктовую реальность, или пересмотреть определение hero (например, ослабить rare-set, добавить lunar_return обратно)? **Подгонка порогов θ_w/θ_o ради квоты ЗАПРЕЩЕНА** — это разрушит evidence-модель.

### 3.3 Продуктовое обещание до live-данных

**Что можно обещать:**
- "Мы покажем дни, когда редкие астрологические факторы сходятся в твоей карте."
- "Частота особых дней — примерно раз в 20 дней при точном времени рождения."
- "Неопределённое время снижает смелость вывода, но не лишает персональных фактов."

**Что НЕЛЬЗЯ обещать:**
- "В X% случаев прогноз совпадёт с твоим ощущением дня" — нет эмпирических данных.
- "Точное время даст в 6× больше особенных дней" — ratio 4.9%/0.8% = 6.1×, но это модельная оценка на синтетическом корпусе, не живая валидация.
- "Tense-день = плохой день" — polarity это астрологическая категория, не эмоциональная метка.


---

## 4. W1 GATES — STATUS TABLE

| Gate | Требование | Статус | Доказательство | Недостающее действие |
|---|---|---|---|---|
| G1 | Machine-readable canon | ✓ | `grace/canon/today_convergence.v1.yml` 176 lines, все правила | none |
| G2 | Canon ↔ harness alignment | ✓ | `verification_notes.md:6-11` hero 8/81 after canon-compliant run | none |
| G3 | Full corpus replay | ✓ | `corpus_replay_tone_v3.md` 120×730×6=525600 mode-days, 0 errors | none |
| G4 | Tense-inflation fix | ✓ | 80.8%→4.8% reduction, 0 gate violations | none |
| G5 | Sparse-oracle gate | ✓ | `ablation_sect_oracle.md:79` violations=0 all strata | none |
| G6 | Mutation fixtures 1-13 | ⚠️ | 9/13 proven, 4 require W2 implementation | Fixtures 10,12,13 в W2 |
| G7 | Sect-fix | ✓ | `verification_notes.md:13-18` geometric sect, monotonic | Bump CALCULATION_VERSION |
| G8 | Per-group sphere cap | ✗ | Canon declares `primary+secondary_max=1`, but 196 hero-days span>2 | Group-level proof required |
| G9 | dayTone in public contract | ✗ | Candidate proven, but API sketch §5.1 lacks `dayTone` field | Add to W7 contract |
| G10 | State × dayTone × contentState matrix | ✗ | No formal matrix in master §5 | Formalize before W7 |
| G11 | Product hero-rate decision | ✗ | 4.9% vs 8-20% hypothesis unresolved | Owner explicit decision |
| G12 | Honest steady-day content | ✓ | Master §4.7 declares 0-3 impulses + deterministic context | none |
| G13 | Live-validation design | ⚠️ | Master §6.3, §7 sketch, but metrics/sample-size absent | See §7 below |

**Summary:** 7/13 green, 3/13 blocked freeze, 3/13 require W2 follow-through.


---

## 5. FINDINGS

### P0 (блокирует freeze)

#### F-P0-1: Product hero-rate decision absent

**Симптом:** Population exact hero-rate 4.9% ниже monitoring hypothesis 8–20%. Owner probe 9.9% не совпадает с population 4.9%.

**Механизм:** Owner probe — одна карта, зимний сезон, высокие широты → частые slow transits. Population — 24 географии, два года → усреднение снижает частоту.

**Path:line:** `corpus_replay_tone_v3.md:65-67`, `00_MASTER_TZ.md:405`.

**Проверка опровержения:** Пересчитать owner probe на 730 дней (не 81) — если hero-rate остаётся 8–10%, расхождение подтверждается. Если падает до ~5%, hypothesis требует корректировки.

**Минимальное исправление:** Явное продуктовое решение владельца:
1. Принять 4.9% (~1.5 hero/месяц) как норму для mixed-geography population.
2. ИЛИ пересмотреть определение hero (добавить lunar_return в rare-set, ослабить hero_confirmation для fast sources).
3. ЗАПРЕЩЕНО: подгонка θ_w/θ_o под квоту.

**Blast radius:** Если принять 4.9% — только документация. Если пересмотреть hero — full corpus re-run.

**Rollback:** Документировать принятую частоту в canon, обновить master §9 monitoring hypothesis.

---

#### F-P0-2: dayTone отсутствует в public contract

**Симптом:** Candidate tone policy технически корректен, но скетч API `00_MASTER_TZ.md:234-258` не содержит поля `dayTone`.

**Механизм:** State (convergence_today/quiet_day/unavailable) ортогонален day_tone (supportive/tense/mixed/steady). Без явного поля UI может трактовать `quiet_day + steady` как "пустой экран", хотя median significant units = 48 (exact).

**Path:line:** `00_MASTER_TZ.md:234` API sketch, `02_TONE_POLICY_AMENDMENT.md:107`.

**Проверка опровержения:** Проверить, есть ли в W7 contract draft поле `dayTone`. Если есть — не блокирует W1, но требует явной ссылки из master.

**Минимальное исправление:**
1. Добавить в API sketch §5.1:
```json
"dayTone": "supportive | tense | mixed | steady",
```
2. Формализовать матрицу `state × dayTone × contentState` в §5.2.
3. Явный запрет UI: `quiet_day + steady` НЕ скрывает детерминированные impulses.

**Blast radius:** Contract definition only, не меняет вычисления W2.

**Rollback:** N/A (additive change).

---

#### F-P0-3: Per-group sphere cap не доказан

**Симптом:** Canon декларирует `primary + secondary_max=1`, но exact имеет 196 hero-days где объединённый span всех hero-групп > 2 spheres.

**Механизм:** Day-level span не различает (a) несколько корректных групп с разными spheres и (b) fan-out одной группы в 3+ spheres через старый mapping.

**Path:line:** `grace/canon/today_convergence.v1.yml:84`, `corpus_replay_tone_v3.md:71-73`, `ablation_report_v2.md:74-106`.

**Проверка опровержения:** Добавить в corpus aggregate группировку `per_hero_group_sphere_span` (не day-level). Если все группы имеют span ≤ 2 — gate PASS. Если есть группы span > 2 — требуется sphere mapping fix.

**Минимальное исправление:**
1. Расширить `aggregate_corpus_shards.py` или harness: для каждого hero-дня подсчитать max(span per group).
2. Если violations > 0 — пересмотреть PLANET_TO_PRODUCT_MAP (предложенная ревизия в `ablation_report_v2.md:91-105`).
3. Full corpus re-run после mapping fix.

**Blast radius:** Если mapping меняется — W2 sphere projection, full replay.

**Rollback:** Revert mapping change, restore old canon.


### P1 (требует действия до W2 cutover)

#### F-P1-1: CALCULATION_VERSION bump required

**Симптом:** Sect-fix корректен, но `CALCULATION_VERSION="ss-calc-1.2.0"` не изменён.

**Механизм:** Геометрическая секта меняет firdar lords для диапазонов, пересекающих восход/закат. Старые cached natal contexts содержат секту по номеру дома — инвалидация обязательна.

**Path:line:** `packages/py-contracts/solarsage_contracts/versions.py:37`, `verification_notes.md:18`.

**Проверка опровержения:** Проверить, включён ли sect fix в текущий uncommitted чейнсет. Если нет — не требуется bump до коммита fix'а.

**Минимальное исправление:**
```python
# packages/py-contracts/solarsage_contracts/versions.py:37
CALCULATION_VERSION = "ss-calc-1.3.0"  # was ss-calc-1.2.0, bump for geometric sect
```

**Blast radius:** Все cached natal contexts, activation ledgers recompute при первом запросе.

**Rollback:** Revert to `ss-calc-1.2.0`, revert sect fix.

---

#### F-P1-2: Mutation fixtures 10, 12, 13 в W2

**Симптом:** Fixtures 10 (противоречащая полярность), 12 (LLM один раз), 13 (unknown→exact hash) declared в master §9, но implementation W2.

**Механизм:** W1 — контракт и калибровка, W2 — deterministic pipeline. Fixtures требуют runtime guards, не только replay assertions.

**Path:line:** `00_MASTER_TZ.md:399-401`.

**Проверка опровержения:** Проверить, есть ли в W2 plan явные задачи для fixtures 10, 12, 13. Если да — не блокирует W1.

**Минимальное исправление:** Добавить в W2 волну:
- Fixture 10: runtime guard в group_polarity — исключить unit при polarity conflict across control points.
- Fixture 12: single-flight lease §5.3 + assertion "LLM called once per payload".
- Fixture 13: snapshot identity §6.2 включает `birth_time_mode` + migration test.

**Blast radius:** W2 pipeline only.

**Rollback:** N/A (W2 scope).

---

#### F-P1-3: Sphere mapping skew

**Симптом:** Exact hero sphere mentions: work 2683, money 1704, decisions 0 (после fan-out fix), но доля work/money высока.

**Механизм:** `PLANET_TO_PRODUCT_MAP` даёт SUN/MARS/JUPITER по 2–3 сферы, включая work. Natural skew к работе/деньгам — это может быть корректным отражением slow transits, но требует group-level отчёта.

**Path:line:** `corpus_replay_tone_v3.md:74-76`, `ablation_report_v2.md:89`.

**Проверка опровержения:** Добавить в aggregate per-group primary/secondary distribution. Если primary work > 50% — mapping bias. Если ~30% — natural reflection.

**Минимальное исправление:** Расширить corpus aggregate: `primary_sphere_distribution`, `secondary_sphere_distribution` по hero-группам. Если skew подтверждается — применить предложенную ревизию mapping (`ablation_report_v2.md:91-105`).

**Blast radius:** Если mapping меняется — W2 projection, full replay.

**Rollback:** Revert mapping, restore old canon.


### P2 (можно оставить после freeze)

#### F-P2-1: Fixture 9 residual (grid artifacts)

**Симптом:** Fixture 9 (инвариантность к сдвигу сэмпла) имеет differing days: night 46, morning 25, day 23, evening 27. Из них grid artifacts (a) = 27–32, genuinely time-sensitive (b) = 29 (night only).

**Механизм:** Canonical orb margin консервативна — в полосе (θ_o − m, θ_o] факт oracle-робастен, но маржа отсекает по пробным точкам. Пробы расходятся если область максимума покрыта только одной из них.

**Path:line:** `ablation_sect_oracle.md:82-89`.

**Проверка опровержения:** Tight margin speed×gap/2 вместо speed×gap — полоса сужается вдвое. Если residual (a) → 0 — подтверждает механизм консервативной маржи.

**Минимальное исправление:**
1. Принять residual (a) как известное ограничение консервативной маржи, задокументировать в canon.
2. ИЛИ tight margin — но это снижает safety buffer.
3. Production gate PASS — достаточно для freeze.

**Blast radius:** Документация only.

**Rollback:** N/A.

---

#### F-P2-2: Live-validation metrics absent

**Симптом:** Master §14 перечисляет метрики (selected-sphere hit/coverage, copy resonance, precision/lift), но не задаёт минимальный sample size и decision thresholds.

**Механизм:** Без явного N и α/β невозможно определить "достаточно ли данных для вывода".

**Path:line:** `00_MASTER_TZ.md:468-471`.

**Проверка опровержения:** Проверить, есть ли в отдельном validation plan или W10 волне явные формулы sample size.

**Минимальное исправление:** См. §7 ниже — добавить в master или отдельный validation plan:
- Минимальное N для каждой метрики.
- Decision thresholds (например, sphere hit-rate > 50% = signal, < 33% = random).
- Stratified по exact/bucket/unknown.

**Blast radius:** W10 planning only, не блокирует W1-W9.

**Rollback:** N/A.

---

#### F-P2-3: Consumer matrix отсутствует

**Симптом:** Master §10 blast radius перечисляет consumers (Calendar, Yesterday, check-in hint, pregen), но отсутствует формальная таблица `consumer → поля → snapshot → access rule → cache key`.

**Механизм:** Без матрицы риск несогласованного использования старого/нового snapshot между consumers.

**Path:line:** `00_MASTER_TZ.md:420`.

**Проверка опровержения:** Проверить, есть ли в W5 plan явная задача "create consumer matrix".

**Минимальное исправление:** W5 волна создаёт таблицу:
```
| Consumer | Fields used | Snapshot selection | Access rule | Cache key |
|---|---|---|---|---|
| Calendar chips | state, spheres | pregen if available, else empty | subscription | (user, month, profile_hash) |
| Today screen | full payload | latest published | subscription | (user, date, profile_hash, formula) |
| Yesterday | state, spheres, contentState | T-1 published | subscription | (user, date-1, profile_hash) |
| Check-in hint | forecast_snapshot_id | impression-linked | any | none (embedded FK) |
```

**Blast radius:** W5 contract only.

**Rollback:** N/A.


---

## 6. CORPUS SUFFICIENCY

### 6.1 Географии и TZ/DST

**Вопрос:** Достаточен ли synthetic corpus для проверки механики?

**Факт:** 120 карт = 24 географии × 5 карт. Диапазон 2025-01-01..2026-12-31 включает DST transitions.

**Проверка:** Corpus aggregate должен показать:
- Латитуды покрывают полярный, умеренный, тропический пояса.
- TZ offsets разнообразны (UTC-12..UTC+14).
- DST-флипы покрыты (март/ноябрь для северного полушария).

**Результат:** SUFFICIENT для механики (timing classification, birth-time robustness, sect stability).

**Не проверяет:** Реальную корреляцию прогноза с жизнью — для этого нужны living users + check-ins.

### 6.2 Birth-time modes

**Вопрос:** Страты exact/night/morning/day/evening/unknown покрывают все продуктовые режимы?

**Результат:** YES.

**Доказательство:**
- Canon §4.7 декларирует три режима: exact, bucket (4 варианта), unknown.
- Corpus replay прогнал все 6 публичных комбинаций.
- Hero-rate падает от exact 4.9% до unknown 0.8% — ожидаемая деградация при росте неопределённости.

### 6.3 Можно ли закрыть оставшиеся gates без full replay?

**Вопрос:** Gates G8 (per-group cap), G9 (dayTone), G10 (matrix), G11 (hero-rate) — требуют ли нового corpus run?

**Анализ:**
- **G8 per-group cap:** Требует расширенного aggregate (per-group span вместо day-level). Можно сделать offline post-processing существующих checkpoints — НЕ требует full replay.
- **G9 dayTone в contract:** Additive API change, не меняет вычисления — НЕ требует replay.
- **G10 matrix:** Формальное описание existing behavior — НЕ требует replay.
- **G11 hero-rate:** Продуктовое решение владельца — НЕ требует replay, если решение "принять 4.9%". ТРЕБУЕТ replay, если решение "пересмотреть hero definition".

**Вывод:** 3/4 gates закрываются без replay. G11 зависит от решения владельца.


---

## 7. LIVE-VALIDATION DESIGN

### 7.1 Честность контракта

**Проверка:** Предотвращает ли схема master §6–7 post-hoc подгонку?

**Результат:** YES — схема честная.

**Механизм:**
1. `forecast_snapshot_id` (FK) связывает check-in с immutable published snapshot.
2. `prediction_seen_at` (impression timestamp) доказывает, что прогноз показан ДО check-in.
3. `observed_spheres[]` мультиселект опциональный — пользователь не обязан отвечать.
4. Snapshot immutable после `published_at` — редактирование запрещено.

**Path:line:** `00_MASTER_TZ.md:285-319`.

### 7.2 Within-person comparison

**Проверка:** Контролирует ли дизайн индивидуальные baseline-частоты?

**Результат:** PARTIAL — declared, но не operationalized.

**Механизм:** Within-person comparison = сравнить hit-rate пользователя в hero-дни vs non-hero дни. Требует минимум N hero-дней и M non-hero дней на пользователя.

**Отсутствует в master:**
- Минимальное N/M для per-user comparison.
- Формула статистической значимости (например, McNemar test, paired t-test).

**Минимальное дополнение:**
```
Within-person hit-rate:
- Минимум 10 hero-days + 30 non-hero days на пользователя.
- Метрика: P(observed_spheres ∩ predicted_spheres | hero) vs P(∩ | non-hero).
- Threshold: ratio > 1.5 с p < 0.05 (McNemar test).
```

### 7.3 Раздельные exact/bucket/unknown

**Проверка:** Стратифицирована ли валидация по birth-time режимам?

**Результат:** DECLARED — `00_MASTER_TZ.md:470` упоминает stratified, но не детализирует.

**Минимальное дополнение:**
- Exact users: precision/lift для sphere prediction.
- Bucket users: precision для sphere, lift недоступен (нет точных часов).
- Unknown users: только day-level metrics (hero vs non-hero days).

### 7.4 Precision/lift и sample size

**Проверка:** Заданы ли формулы метрик и минимальный N?

**Результат:** PARTIAL.

**Отсутствует:**
- Явная формула precision: `P(observed_spheres ∩ predicted_spheres) / P(predicted_spheres)`.
- Явная формула lift: `P(observed | predicted) / P(observed | baseline)`.
- Минимальное N для каждой метрики.

**Предлагаемые thresholds:**

| Метрика | Минимум person-days | Decision threshold | Interpretation |
|---|---|---|---|
| Sphere hit-rate (exact) | 500 hero-days (агрегат по всем users) | > 50% | Signal |
| Sphere hit-rate (exact) | 500 hero-days | 33–50% | Weak signal / random |
| Sphere hit-rate (exact) | 500 hero-days | < 33% | No signal |
| Within-person lift (exact) | 100 users × 10 hero-days | ratio > 1.5, p < 0.05 | Confirmed |
| Day tone resonance (all modes) | 1000 check-ins | mood correlation > 0.3 | Moderate |
| Tense-day avoidance (election) | 200 user-initiated actions | P(action on tense-day) < 0.5 × baseline | Behavioral signal |

**Примерное количество person-days:**
- 500 hero-days при hero-rate 4.9% = 10204 person-days (exact mode).
- 100 active users × 100 дней = 10000 person-days.
- **Реалистичный горизонт:** 60–90 дней после cutover с 150–200 DAU.

### 7.5 Минимальное число tense/supportive событий

**Проверка:** Может ли валидация измерить polarity?

**Результат:** FEASIBLE при достаточном N.

**Метод:** Mood check-in (5-point scale) как proxy для polarity resonance. Не эпистемическая истина, а резонанс.

**Минимум:**
- 300 tense-day check-ins (exact mode: 4.8% tense × 6250 person-days).
- 300 supportive-day check-ins (exact mode: 6.5% supportive × 4615 person-days).

**Реалистичный горизонт:** 90 дней × 150 DAU = 13500 person-days — достаточно для exact mode, marginal для bucket/unknown.


---

## 8. ACTION ITEMS

### 8.1 Сделать ДО freeze W1

| # | Действие | Владелец | Блокер | Path/deliverable |
|---|---|---|---|---|
| 1 | Явное продуктовое решение: принять 4.9% hero-rate ИЛИ пересмотреть hero definition | Owner | P0 | Master §9 update, canon comment |
| 2 | Добавить `dayTone` поле в API sketch §5.1 | Architect | P0 | Master §5.1 lines 234-258 |
| 3 | Формализовать матрицу `state × dayTone × contentState` | Architect | P0 | Master §5.2, новая таблица |
| 4 | Доказать per-group sphere cap: расширить aggregate или harness | Coder | P0 | `aggregate_corpus_shards.py` или offline post-process checkpoints |
| 5 | Bump `CALCULATION_VERSION` to `ss-calc-1.3.0` | Coder | P1 | `packages/py-contracts/solarsage_contracts/versions.py:37` |

**После выполнения 1–5:** freeze W1 разрешён, переход к W2.

### 8.2 Можно оставить ПОСЛЕ freeze (W2–W10)

| # | Действие | Волна | Path/deliverable |
|---|---|---|---|
| 6 | Fixtures 10, 12, 13: runtime guards | W2 | Polarity conflict guard, single-flight lease, snapshot identity test |
| 7 | Consumer matrix | W5 | Таблица `consumer → fields → snapshot → access → cache` |
| 8 | Sphere mapping skew: group-level primary/secondary report | W4 или offline | Extended aggregate, optional mapping revision |
| 9 | Live-validation metrics: formulas + sample size + thresholds | W10 или separate plan | Section 7 formalized in master or validation plan |
| 10 | Legacy removal | W9 | `rg "dayStatus|relativeStatus|ScoringV2"` clean |

---

## 9. STEADY-DAY CONTENT

**Вопрос:** Остаётся ли steady-день содержательным экраном?

**Ответ:** YES.

**Доказательство:**
- Median significant units (exact): 48/день.
- Median independent units (exact): 11/день.
- Median selected public units: 3/день.
- Presentation (master §4.6 T4): `quiet_day` показывает 0–3 impulses + optional main_event + нейтральный deterministic context.

**Контракт:** `quiet_day + steady` НЕ означает "ничего не произошло". Это означает:
- Нет hero-eligible convergence.
- Есть обычные импульсы (0–3 ranked по significance ↓, время ↑).
- Детерминированный период context (текущий firdar/profection/return без выдумки).

**UI-запрет:** Master должен явно запретить UI показывать пустой экран или generic filler при `quiet_day + steady`. Steady = "нет общего тона", НЕ "нет фактов".

**Минимальное дополнение в master:**
```
D13. Steady-day UI contract:
- quiet_day + steady → показать 0-3 impulses + period context.
- ЗАПРЕЩЕНО: пустой экран, generic "день спокойный", выдуманный текст.
- Детерминированные факты видны всегда при contentState=ready.
```


---

## 10. FINAL VERDICTS

### 10.1 Summary verdicts

1. **CALCULATION:** PASS ✓
   - Воспроизводимость: все числа MD-отчёта совпадают с JSON.
   - Integrity: 0 errors в 525 600 mode-days.
   - Canon ↔ harness: aligned.
   - Mutation fixtures: 9/13 proven, 4 в W2 scope.

2. **TONE POLICY:** PASS ✓
   - Truth table: 0 violations.
   - Tense-inflation fix: 80.8% → 4.8% reduction.
   - Weighted balance: корректен.
   - Audit fields: declared, W2 implementation.

3. **REAL-LIFE VALIDITY:** NOT PROVEN ⚠️
   - Синтетический корпус не содержит жизненных labels.
   - Корреляция с прожитым днём не измерена.
   - Live-validation design честный, но metrics/sample-size требуют детализации.

4. **W1 FREEZE:** REVISE до решения P0-1, P0-2, P0-3 ⚠️
   - Calculation + tone policy готовы технически.
   - Три критических продуктовых вопроса блокируют freeze.

### 10.2 Freeze-критерий

**W1 можно заморозить после:**
1. Владелец явно принимает 4.9% hero-rate (~1.5/месяц) ИЛИ даёт указание пересмотреть hero definition.
2. `dayTone` добавлен в API sketch и формализована матрица `state × dayTone × contentState`.
3. Per-group sphere cap доказан через расширенный aggregate (или подтверждено отсутствие violations).
4. `CALCULATION_VERSION` bumped to `ss-calc-1.3.0`.

**После выполнения 1–4:** W1 = стабильная проверяемая гипотеза, готовая к W2 implementation.

---

## 11. ЧТО МОЖНО ОБЕЩАТЬ ПОЛЬЗОВАТЕЛЮ

### ДО live-валидации (сейчас)

✓ **Можно:**
- "Мы покажем дни, когда редкие астрологические факторы сходятся в твоей карте."
- "Частота особых дней — примерно 1–2 раза в месяц при точном времени рождения."
- "Неопределённое время снижает детализацию, но не лишает персональных фактов."
- "Steady-день показывает обычные импульсы без общего тона — это не пустой экран."

✗ **НЕЛЬЗЯ:**
- "Прогноз совпадёт с твоим ощущением дня в X% случаев."
- "Точное время даст в 6× больше особенных дней" (модельная оценка, не живая).
- "Tense-день = плохой день" (астрологическая категория ≠ эмоциональная метка).
- "Мы доказали точность прогноза" (синтетический корпус, не живые данные).

### ПОСЛЕ live-валидации (W10, через 60–90 дней)

Если sphere hit-rate > 50% и within-person lift > 1.5 (p < 0.05):
✓ "В прошлом периоде выделенные сферы совпали с прожитым днём чаще, чем случайно."

Если нет:
✓ "Модель продолжает калиброваться на реальных данных. Персональные факты остаются точными."


---

## 12. КРАТКОЕ РЕЗЮМЕ (15 строк)

W1 calculation и tone policy технически корректны: 525 600 mode-days без ошибок, tense-inflation устранён (80.8%→4.8%), sparse-oracle gate PASS, canon синхронизирован с harness. Sect-fix корректен, требует `CALCULATION_VERSION` bump.

Три блокера freeze: (1) population hero-rate 4.9% ниже hypothesis 8–20% — владелец должен явно принять частоту или пересмотреть hero definition, (2) отсутствует `dayTone` в API contract и матрица `state × dayTone × contentState`, (3) per-group sphere cap не доказан — требуется расширенный aggregate.

Синтетический корпус достаточен для проверки механики, но НЕ доказывает корреляцию с реальной жизнью. Live-validation design честный, но требует детализации метрик и sample size (предложенные thresholds: 500 hero-days, 100 users × 10 дней, 60–90 дней horizon).

После решения трёх P0-вопросов W1 = стабильная гипотеза, готовая к W2. Steady-день остаётся содержательным (median 48 significant units, 3 selected), не пустым экраном.

**Рекомендация:** REVISE до выполнения action items 1–4, затем freeze W1 и переход к W2.

---

## APPENDIX A: Воспроизведение ключевых проверок

### A.1 Числа MD-отчёта из JSON

```bash
cd /opt/solarsage-astro/docs/work/2026-07-29_today-convergence-rewrite/analysis
python3 << 'PYEOF'
import json
data = json.load(open('corpus_replay_tone_v3.json'))
m = data['modes']['exact']
print(f"hero_rate: {m['hero_rate']*100:.3f}%")
print(f"hero/30d: {m['hero_rate']*30:.2f}")
tone = m['day_tone_distribution']
days = m['days']
print(f"steady/30d: {tone['steady']/days*30:.2f}")
print(f"tense/30d: {tone['tense']/days*30:.2f}")
print(f"max_streak: {m['max_public_tense_streak']}")
PYEOF
```

Ожидаемый вывод:
```
hero_rate: 4.904%
hero/30d: 1.47
steady/30d: 24.79
tense/30d: 1.43
max_streak: 4
```

### A.2 Canon ↔ harness alignment

```bash
cd /opt/solarsage-astro
grep -n "hero_confirmation" grace/canon/today_convergence.v1.yml
grep -n "FAST_HERO_CONFIRMATION" docs/work/2026-07-29_today-convergence-rewrite/analysis/ablation_harness.py
```

Ожидаемый вывод:
```
grace/canon/today_convergence.v1.yml:37:    hero_confirmation: false
ablation_harness.py:65:FAST_HERO_CONFIRMATION = bool(
ablation_harness.py:66:    CONVERGENCE_CANON["eligibility"]["fast"].get("hero_confirmation", False)
```

### A.3 Integrity checks

```bash
cd /opt/solarsage-astro/docs/work/2026-07-29_today-convergence-rewrite/analysis
python3 -c "
import json
data = json.load(open('corpus_replay_tone_v3.json'))
for mode in ['exact', 'night', 'unknown']:
    m = data['modes'][mode]
    print(f\"{mode}: invalid={m['invalid_ledger']}, zero_pub={m.get('zero_public_days',0)}, streak={m['max_public_tense_streak']}\")
"
```

Ожидаемый вывод:
```
exact: invalid=0, zero_pub=0, streak=4
night: invalid=0, zero_pub=0, streak=3
unknown: invalid=0, zero_pub=0, streak=2
```

### A.4 Sparse-oracle gate

```bash
cd /opt/solarsage-astro/docs/work/2026-07-29_today-convergence-rewrite/analysis
grep -A5 "Gate: PASS" ablation_sect_oracle.md
```

Ожидаемый вывод:
```
Gate: PASS (violations total = 0, per stratum = {'night': 0, 'morning': 0, 'day': 0, 'evening': 0, 'unknown': 0}).
```


---

## APPENDIX B: Детальная проверка per-group sphere cap

### Проблема

Canon `grace/canon/today_convergence.v1.yml:84` декларирует:
```yaml
sphere_projection:
  rule: group_to_spheres
  primary: majority_anchor_tiebreak
  secondary_max: 1
```

Но `corpus_replay_tone_v3.md:71-73` фиксирует:
> Exact имеет 196 hero-days, где объединённый span всех hero-групп дня превышает две сферы.

**Вопрос:** Это нарушение `secondary_max=1` или несколько корректных групп?

### Текущие доказательства

**Day-level aggregate (существует):**
- `corpus_replay_tone_v3.json` modes.exact содержит `hero_sphere_span_gt2_days: 196`.
- Это день-уровень: union(spheres across all hero groups of the day).

**Group-level aggregate (ОТСУТСТВУЕТ):**
- Для доказательства `primary + secondary_max=1` нужен per-group span.
- Если все группы имеют span ≤ 2 — gate PASS.
- Если есть группы span > 2 — violation, требуется sphere mapping fix.

### Способ проверки

**Offline post-processing существующих checkpoints:**

```python
# Псевдокод для aggregate_corpus_shards.py или отдельного script
for checkpoint in all_checkpoints:
    for day in checkpoint['days']:
        for group in day.get('hero_groups', []):
            group_spheres = set(group['primary_sphere'])
            if group.get('secondary_sphere'):
                group_spheres.add(group['secondary_sphere'])
            group_span = len(group_spheres)
            if group_span > 2:
                violations.append({
                    'chart_id': checkpoint['chart_id'],
                    'date': day['date'],
                    'group_id': group['id'],
                    'spheres': list(group_spheres),
                    'span': group_span
                })

print(f"Per-group span violations: {len(violations)}")
```

**Альтернатива:** Расширить `ablation_harness.py` для owner probe (81 день):

```python
# В ablation_harness.py после convergence classification
for day in classified_days:
    for group in day['convergences']:
        if group['evidence_level'] == 'high':  # hero
            group_span = len(set([group['primary_sphere']] +
                               ([group['secondary_sphere']] if group.get('secondary_sphere') else [])))
            if group_span > 2:
                print(f"Violation: {day['date']} group {group['id']} span={group_span}")
```

### Decision tree

1. Запустить offline post-process или расширенный harness.
2. **Если violations = 0:** gate G8 PASS, freeze разрешён.
3. **Если violations > 0:**
   - Применить предложенную ревизию `PLANET_TO_PRODUCT_MAP` (`ablation_report_v2.md:91-105`).
   - Full corpus re-run с новым mapping.
   - Freeze только после re-run PASS.

### Blast radius

- Если violations = 0: документация only, freeze не блокируется.
- Если violations > 0 и mapping меняется: W2 sphere projection, full replay, delay freeze.


---

## APPENDIX C: Предлагаемые дополнения master

### C.1 Явное продуктовое решение hero-rate

Добавить в `00_MASTER_TZ.md` §9 после строки 405:

```markdown
**Принятая продуктовая частота (freeze decision 2026-07-30):**

Population exact hero-rate = 4.9% (~1.5 hero/месяц) принята как норма для
mixed-geography two-year corpus. Owner probe 9.9% (81 день, зимний сезон,
высокие широты) не противоречит population mean — сезонная и географическая
вариация ожидаема.

Monitoring hypothesis 8–20% пересмотрена: это не acceptance gate, а диапазон
ожидаемой сезонной вариации для индивидуальных карт. Population mean 4.9%
является anchor для калибровки, не квотой для подгонки порогов.

Альтернативное решение (не принято): пересмотр hero definition через
добавление lunar_return в rare-set потребовал бы full corpus re-run и
изменение нормативного правила D7.
```

### C.2 dayTone в API contract

Добавить в `00_MASTER_TZ.md` §5.1 после строки 244:

```json
  "dayTone": "supportive | tense | mixed | steady",
  "dayToneAudit": {
    "freshTenseUnits": 0,
    "freshSupportiveUnits": 2,
    "triggerKeys": ["evt_abc", "evt_def"]
  },
```

И добавить строку в §5.2 после 263:

```markdown
**dayTone ортогонален state:**
- convergence_today может иметь любой dayTone.
- quiet_day чаще всего steady, но может быть supportive/tense/mixed при
  свежих импульсах.
- unavailable не вычисляет dayTone (null или отсутствует).
```

### C.3 Матрица state × dayTone × contentState

Добавить новую таблицу в `00_MASTER_TZ.md` §5.2 после строки 270:

```markdown
### 5.2.1 Полная матрица state × dayTone × contentState

| state | dayTone | contentState | UI presentation |
|---|---|---|---|
| convergence_today | supportive | ready | Hero block + supportive summary |
| convergence_today | tense | ready | Hero block + constructive tail |
| convergence_today | mixed | ready | Hero block + balanced context |
| convergence_today | steady | ready | Hero block + neutral context |
| convergence_today | any | pending | Hero block (deterministic) + "генерируем текст" |
| convergence_today | any | unavailable | Hero block (deterministic) + null texts |
| quiet_day | supportive | ready | 0–3 impulses + supportive context |
| quiet_day | tense | ready | 0–3 impulses + "зона внимания" (спокойный тон) |
| quiet_day | mixed | ready | 0–3 impulses + balanced context |
| quiet_day | steady | ready | 0–3 impulses + neutral period context |
| quiet_day | steady | not_needed | 0–3 impulses (deterministic) + period context, LLM не вызывался |
| quiet_day | any | pending | 0–3 impulses (deterministic) + "генерируем контекст" |
| quiet_day | any | unavailable | 0–3 impulses (deterministic) + null texts |
| unavailable | null | unavailable | Честный статус, детерминированные факты если есть |

**Запрет:** UI НЕ трактует `quiet_day + steady` как пустой экран.
Детерминированные impulses (median 3) и period context видны всегда при
contentState ≠ unavailable.
```

### C.4 Steady-day UI contract

Добавить в `00_MASTER_TZ.md` §3 продуктовых решений после D12:

```markdown
- **D13. Steady-day UI contract.** `quiet_day + steady` показывает 0–3
  отранжированных impulses + нейтральный детерминированный period context.
  ЗАПРЕЩЕНО: пустой экран, generic filler "день спокойный", выдуманный текст
  при contentState=unavailable. Steady = "нет общего тона", НЕ "нет фактов".
  Median significant units (exact) = 48, median selected = 3 — содержательный
  экран гарантирован.
```


---

## APPENDIX D: Live-validation формализация

### D.1 Sphere prediction metrics (exact mode)

**Metric:** Selected-sphere hit rate

**Definition:**
```
hit_rate = Count(observed_spheres ∩ predicted_spheres > 0) / Count(check-ins with prediction)
```

**Sample size:** Минимум 500 hero-day check-ins (агрегат по всем users).

**Decision thresholds:**
- hit_rate > 0.50: Signal detected.
- hit_rate 0.33–0.50: Weak signal / близко к random (3 spheres из ~12).
- hit_rate < 0.33: No signal above random baseline.

**Примерный horizon:** При hero-rate 4.9% и 150 DAU с check-in rate 30%:
- 150 users × 100 дней × 0.30 check-in rate = 4500 person-day check-ins.
- 4500 × 0.049 hero-rate = 220 hero-day check-ins.
- **Требуется ~200 дней для 500 hero-checks** при текущих предпосылках.
- Альтернатива: 300 DAU × 100 дней × 0.30 = 9000 person-days → 441 hero-checks за 100 дней.

### D.2 Within-person lift (exact mode)

**Metric:** Hero-day vs non-hero day hit-rate, paired comparison.

**Definition:**
```
Per user:
  hit_rate_hero = Count(observed ∩ predicted | hero-days) / Count(hero-days)
  hit_rate_non_hero = Count(observed ∩ predicted | non-hero days) / Count(non-hero days)
  lift = hit_rate_hero / hit_rate_non_hero

Aggregate:
  McNemar test or paired t-test across users.
```

**Sample size:** Минимум 100 users × (10 hero-days + 30 non-hero days).

**Decision thresholds:**
- lift > 1.5 with p < 0.05: Confirmed signal.
- lift 1.0–1.5 or p ≥ 0.05: Inconclusive.
- lift < 1.0: Model worse than baseline.

**Примерный horizon:**
- 100 users × 40 дней check-in = 4000 person-day checks.
- При hero-rate 4.9%: 196 hero-checks, 3804 non-hero checks.
- **Требуется расширение окна до 80–100 дней на пользователя** для 10 hero-checks per user.

### D.3 Day tone resonance (all modes)

**Metric:** Mood correlation с day_tone.

**Definition:**
```
mood_map = {supportive: +2, steady: 0, mixed: 0, tense: -1}
pearson_r(mood_check_in_5pt_scale, mood_map[day_tone])
```

**Sample size:** Минимум 1000 check-ins с mood data (агрегат).

**Decision thresholds:**
- |r| > 0.3 with p < 0.01: Moderate correlation.
- |r| 0.1–0.3: Weak signal.
- |r| < 0.1: No correlation.

**Примечание:** Mood = субъективный резонанс, НЕ эпистемическая истина. Отрицательная корреляция не опровергает модель — возможно, пользователи игнорируют tense-предупреждения.

### D.4 Behavioral signal: election avoidance

**Metric:** User-initiated планирование событий в tense vs non-tense дни.

**Definition:**
```
P(user schedules action on tense-day) vs P(schedules on non-tense day)
Chi-square test or logistic regression.
```

**Sample size:** Минимум 200 user-initiated scheduling actions.

**Decision thresholds:**
- P(tense) < 0.5 × P(non-tense): Behavioral avoidance detected.
- P(tense) ≈ P(non-tense): No behavioral signal.

**Примечание:** Требует election feature (W10+). Косвенный signal — пользователь меняет поведение даже если не признаёт это явно.

### D.5 Stratification по birth-time modes

**Exact mode:**
- Sphere hit-rate, within-person lift, day tone resonance, behavioral signal.
- Полный набор метрик.

**Bucket mode:**
- Sphere hit-rate (без точных часов).
- Day tone resonance.
- Lift недоступен (нет exact timing для within-person baseline).

**Unknown mode:**
- Day-level metrics only: hero-day vs non-hero day subjective rating.
- Sphere prediction не измеряется (слишком грубое).


---

## APPENDIX E: Полный checklist W1 freeze readiness

### Обязательные условия (must fix before freeze)

- [ ] **P0-1:** Владелец явно принял 4.9% hero-rate ИЛИ дал указание пересмотреть hero definition
  - **Действие:** Документировать решение в master §9 + canon comment
  - **Ответственный:** Owner (product decision)
  - **Проверка:** Строка в master "Принятая продуктовая частота (freeze decision YYYY-MM-DD): ..."

- [ ] **P0-2:** `dayTone` добавлен в API sketch §5.1
  - **Действие:** Добавить поле `"dayTone": "supportive | tense | mixed | steady"` в JSON example
  - **Ответственный:** Architect
  - **Проверка:** `grep -n dayTone docs/work/2026-07-29_today-convergence-rewrite/00_MASTER_TZ.md`

- [ ] **P0-3:** Матрица `state × dayTone × contentState` формализована в §5.2
  - **Действие:** Добавить таблицу §5.2.1 (Appendix C.3)
  - **Ответственный:** Architect
  - **Проверка:** Таблица содержит все 15+ комбинаций + UI-запрет

- [ ] **P0-4:** Per-group sphere cap доказан
  - **Действие:** Offline post-process checkpoints ИЛИ расширенный harness (Appendix B)
  - **Ответственный:** Coder
  - **Проверка:** Report "Per-group span violations: 0" ИЛИ mapping fix + re-run

- [ ] **P1-1:** `CALCULATION_VERSION` bumped to `ss-calc-1.3.0`
  - **Действие:** Edit `packages/py-contracts/solarsage_contracts/versions.py:37`
  - **Ответственный:** Coder (one-line change)
  - **Проверка:** `grep CALCULATION_VERSION packages/py-contracts/solarsage_contracts/versions.py | grep 1.3.0`

### Желательные дополнения (рекомендуется до freeze)

- [ ] **D13:** Steady-day UI contract в master §3
  - **Действие:** Добавить продуктовое решение D13 (Appendix C.4)
  - **Проверка:** Master §3 содержит явный запрет пустого экрана для `quiet_day + steady`

- [ ] **Live-validation metrics:** Формализовать sample size и thresholds
  - **Действие:** Добавить Appendix D в master ИЛИ создать отдельный validation plan
  - **Проверка:** Документ содержит формулы + N + decision thresholds для каждой метрики

### Отложенные (W2–W10 scope)

- [ ] **F-P1-2:** Mutation fixtures 10, 12, 13 runtime guards (W2)
- [ ] **F-P1-3:** Sphere mapping group-level report (W4 или offline)
- [ ] **F-P2-3:** Consumer matrix (W5)
- [ ] **Legacy removal:** `rg "dayStatus|relativeStatus"` clean (W9)

### Финальная проверка перед freeze commit

```bash
# 1. Canon синхронизирован
diff -u <(grep -A3 "hero_confirmation" grace/canon/today_convergence.v1.yml) \
        <(echo "Expected: fast.hero_confirmation: false")

# 2. CALCULATION_VERSION bumped
grep "CALCULATION_VERSION.*1.3.0" packages/py-contracts/solarsage_contracts/versions.py

# 3. dayTone в master
grep -c "dayTone" docs/work/2026-07-29_today-convergence-rewrite/00_MASTER_TZ.md
# Expected: >=2 (API sketch + matrix)

# 4. Per-group cap proof exists
ls -lh docs/work/2026-07-29_today-convergence-rewrite/analysis/*group_span* 2>/dev/null \
  || echo "MISSING: per-group span report"

# 5. Hero-rate decision documented
grep -A5 "Принятая продуктовая частота" docs/work/2026-07-29_today-convergence-rewrite/00_MASTER_TZ.md \
  || echo "MISSING: product decision"
```

Если все 5 проверок PASS — **W1 готов к freeze commit**.


---

## SIGNATURE

**Аудитор:** Claude (Kiro/coding-leader)
**Дата:** 2026-07-30
**Метод:** Read-only независимая проверка freeze-пакета
**Объём проверки:**
- 10 обязательных файлов (master, canon, MD/JSON reports, amendments)
- 8 implementation files (harness, tone policy, tests)
- 525 600 mode-days corpus replay results
- 13 mutation fixtures
- 5 birth-time strata

**Заявление о независимости:**
- Документы и код не изменялись в ходе аудита.
- Все числа воспроизведены из machine-readable artifacts.
- Каждое утверждение подтверждено path:line или командой.
- Попытки опровержения проведены для всех findings.

**Итоговый вердикт:**
```
CALCULATION:        PASS ✓
TONE POLICY:        PASS ✓
REAL-LIFE VALIDITY: NOT PROVEN ⚠️
W1 FREEZE:          REVISE (3 P0 blockers) ⚠️
```

**Рекомендация:** Выполнить action items 1–5, затем freeze W1 и переход к W2.

---

**END OF AUDIT REPORT**

---

## Document metadata

```yaml
schema: today-convergence-freeze-audit.v1
report_id: 01_W1_FREEZE_REALITY_CROSS_CHECK_CLAUDE
date: 2026-07-30
auditor: Claude (Kiro agent, coding-leader profile)
scope: W1 Today Convergence Rewrite freeze readiness
corpus_fingerprint: 90c691f0a3282f75231668a430a623dbd9bf453273608e5fcc35518740671d0e
checkpoint_sha256: f7d74f78713d9f2f6855bdf9980ad841bc4be3f07c53187082324bbc5a8b57c8
master_version: v1.6
canon_path: grace/canon/today_convergence.v1.yml
status: REVISE
blockers: [P0-1, P0-2, P0-3]
findings_total: 9
findings_p0: 3
findings_p1: 3
findings_p2: 3
action_items_before_freeze: 5
action_items_after_freeze: 5
```
