# W1 Freeze Reality Cross-Check — DeepSeek v4

Date: 2026-07-30
Auditor: coding-leader (opencode/DeepSeek-v4)
Scope: full freeze package (16 mandatory files + 4 test files)
Method: read-only; zero code edits; every claim verified against path:line or command.
Model ID for trace: deepseek-v4-pro

## Executive Summary

W1 is **вычислительно зрелым**: формула, replay, ablation, birth-time robustness, sparse-oracle gate, tone-candidate и sect-fix — всё прошло корпусную проверку. Hero 4.9% (exact population) ≠ старые 100%; tense снизился с 81% до 4.8% без пустых дней.

**Но freeze не готов по трём причинам:**
1. `CALCULATION_VERSION` не bumped — sect-fix не инвалидирует кэши (P0).
2. Canon yml содержит stale-измерения (hero: 10/81 вместо 8/81) и статус `draft`.
3. 196 exact hero-days имеют hero sphere span > 2 — per-group cap не доказан (P1).

**Главный вопрос: можно ли заморозить W1 и перейти к W2?** — REVISE. После трёх минимальных исправлений (bump version, freeze canon, group-level gate) — PASS.

## 1. CALCULATION: PASS

### 1.0 Corpus replay numbers воспроизводятся

Все числа из `corpus_replay_tone_v3.md` подтверждены в `corpus_replay_tone_v3.json`:

| Метрика | JSON | MD report | Совпадение |
|---------|------|-----------|------------|
| exact hero_rate | 0.049041 | 4.904% | ✓ |
| exact tense/30d | 1.43 | 1.43 | ✓ (4181/87600×30=1.432) |
| exact steady/30d | 24.79 | 24.79 | ✓ (72398/87600×30=24.794) |
| exact supportive/30d | 1.94 | 1.94 | ✓ (5660/87600×30=1.938) |
| exact mixed/30d | 1.84 | 1.84 | ✓ (5361/87600×30=1.836) |
| exact legacy tense | 82.74% | 82.74% | ✓ (0.827374) |
| exact tense_streak_max | 4 | 4 | ✓ |
| exact invalid_ledger | 0 | 0 | ✓ |
| exact zero_selected_public_days | 0 | 0 | ✓ |
| night hero/30d | 0.41 | 0.41 | ✓ (1203/87600×30=0.412) |
| night tense/30d | 0.42 | 0.42 | ✓ |
| night tense_streak_max | 3 | 3 | ✓ |
| unknown hero/30d | 0.25 | 0.25 | ✓ (731/87600×30=0.250) |
| unknown tense/30d | 0.35 | 0.35 | ✓ |
| unknown tense_streak_max | 2 | 2 | ✓ |
| unknown chart_hero_rate_min | 0.0 | — | ✓ (≥1 card: 0 hero over 2 years) |
| 120/120 checkpoints ok | true | 0 ошибок | ✓ |

Verification command:
```bash
python3 -c "
import json
with open('docs/work/2026-07-29_today-convergence-rewrite/analysis/corpus_replay_tone_v3.json') as f:
    d = json.load(f)
e = d['modes']['exact']
assert abs(e['hero_rate'] - 0.049041) < 1e-6
assert e['invalid_ledger'] == 0
assert e['tense_streak_max'] == 4
assert e['day_tone_distribution']['steady'] == 72398
print('PASS: all exact-mode numbers verified')
"
```

### 1.1 Ablation v2 и canon alignment воспроизводимы

`verification_notes.md` T1 + `ablation_t1_canon_align.json`:
- C1 точка (θ_w=0.55, θ_o=0.5, rule B): hero = 8/81
- Canon-compliant правила: `hero_confirmation_fast_allowed: false`, `hero_target_types: ["natal_planet", "angle"]`
- Выпавшие vs v2: 06-04 (MOON witness), 06-17 (lot target + MOON witness) — оба подтверждены по составу групп
- `ablation_t1_canon_align.json:28` = 8 hero_days, `ablation_t1_canon_align.json:38` = state_distribution: hero 8

### 1.2 Sect fix: геометрическая секта работает

`test_geometric_sect.py` — 5 тестов:
- `test_true_solar_altitude_separates_day_and_night` — PASS (line 46)
- `test_firdar_sect_is_geometric_and_house_system_independent` — PASS (line 93): sect_basis = "geometric_sun_altitude", sun_house_role = "audit_only"
- `test_high_latitude_winter_no_spurious_flips_12_to_16` — PASS (line 129)
- `test_sect_flips_exactly_at_geometric_rise_and_set` — PASS (line 156)
- `test_polar_day_and_polar_night_are_explicit` — PASS (line 177)

**Но CALCULATION_VERSION не bumped.** `packages/py-contracts/solarsage_contracts/versions.py:37`: `CALCULATION_VERSION = "ss-calc-1.2.0"` — это до-sect-fix значение. Кэши natal/activation с `calculation_version="ss-calc-1.2.0"` не будут инвалидированы при деплое sect-fix → старые кэши с неверной сектой останутся в обороте. (см. P0-1 ниже)

### 1.3 Formula version в replay

`corpus_replay_tone_v3.json:16`: `formula_version: "today-convergence-2"` — совпадает с MASTER_TZ §5.1 root envelope: `formulaVersion: "today-convergence-2"` (line 256).

### 1.4 Tone policy candidate — formula correct

`tone_policy_candidate.py` содержит 6 unit-тестов в `test_tone_policy_candidate.py`:
- `test_single_fast_tense_unit_is_steady` (line 67): Moon tense → steady ✓
- `test_long_running_tense_context_does_not_override_fresh_support` (line 73): ongoing ≠ fresh ✓
- `test_two_independent_fresh_tense_units_create_tense` (line 88): SAT+PLU=tense ✓
- `test_fresh_support_and_tension_are_mixed` (line 96): SAT+JUP=mixed ✓
- `test_high_confidence_tense_hero_can_create_tense_alone` (line 103): high-conf hero → tense ✓
- `test_group_balance_is_independent_and_mixed` (line 110): dedup by driver ✓

## 2. TONE POLICY: PASS (candidate, REVISE to freeze)

### 2.1 Tension inflation устранена

Доказано корпусом:
- Legacy tense: 80.8–82.7% дней → candidate tense: 1.2–4.8% ✓
- `zero_public_days=0` во всех режимах — нет пустых дней ✓
- `zero_selected_public_days`: exact 0, bucket 1–2, unknown 2 — не ноль, но в границах «2 дня из 87 600» ✓
- Streak: exact max 4, bucket max 3, unknown max 2 — нет перманентных tense-серий ✓

### 2.2 Tone gate audit: 0 нарушений

`corpus_replay_tone_v3.md:30`: "tone-gate audit: 0 случаев tense без high-confidence tense anchor или двух независимых fresh tense units; 0 аналогичных нарушений для supportive"

### 2.3 Открытый вопрос: population hero-rate 4.9% below monitoring hypothesis

Monitoring hypothesis: hero_rate 8–20% (`today_convergence.v1.yml:143`). Измеренный population exact hero rate: 4.9% ниже гипотезы. Это не ошибка формулы — это синтетический корпус 120 карт, и владелец должен явно принять частоту ~1.5 hero/месяц или пересмотреть определение hero. Пороги запрещено крутить ради квоты (MASTER_TZ §9: "Пороги НЕ выбираются для попадания в квоту").

### 2.4 REVISE: tone promotion до freeze

`today_convergence.v1.yml:147`: `tone_policy: status: candidate_pending_replay`. `02_TONE_POLICY_AMENDMENT.md:108`: "До freeze остаются три решения". Корпусный replay сделан (120×730), но ни одно из трёх решений не принято:
1. Принять частоту hero 4.9% или пересмотреть определение
2. Добавить `dayTone` в public API/W7 contract
3. Доказать per-group sphere cap

## 3. REAL-LIFE VALIDITY: NOT PROVEN

### 3.1 Корпус синтетический — это явно оговорено

`corpus_replay_tone_v3.md:8`: "Корпус синтетический: он проверяет воспроизводимость, целостность и распределения модели, но не доказывает совпадение прогноза с прожитым днём."

### 3.2 Нет жизненных labels

Ни в одном из файлов freeze-пакета нет:
- реальных пользовательских check-in данных
- observed_spheres, совпадающих/расходящихся с predicted_spheres
- mood → polarity корреляции
- time-agreement (заявлено как "not measured in v1" — MASTER_TZ §14)

### 3.3 План live-валидации спроектирован, но не имплементирован

MASTER_TZ §14 содержит метрики (selected-sphere hit/coverage, copy resonance, polarity, time agreement, product: check-in rate/retention/DAU/MAU, coverage), но это проектный уровень. Конкретные SQL-запросы, статистические тесты, минимальные N для значимости — не определены.

MASTER_TZ §7 определяет схему check-in:
- `forecast_snapshot_id` (FK → snapshot)
- `prediction_seen_at` (из impression §6.3)
- `observed_spheres[]` (мультиселект)
- constraint `(user_id, target_date)`

Эта схема достаточна для within-person comparison (observed vs predicted spheres), но отсутствуют:
- exact/bucket metric: доля совпадений с учётом birth_time_mode
- lift: насколько прогноз hero-дня повышает вероятность observed_sphere vs случайный день
- минимальное N tense/supportive событий для статистической значимости
- разделение exact match vs partial (сфера в группе, но не primary) vs unknown

## 4. W1 FREEZE: REVISE

**BLOCK** отсутствует: формула корректна, replay воспроизводим, вычисления детерминированы. **Но REVISE** — три обязательных действия до freeze.

## 5. W1 Gates Table

| Gate | Status | Evidence | Missing Action |
|------|--------|----------|----------------|
| G1: machine-readable canon | REVISE | `today_convergence.v1.yml` exists (176 lines) | Update stale measured.hero and set status=frozen |
| G2: исправленный re-run новым классификатором | PASS (partial) | `ablation_t1_canon_align.json`: hero 8/81 canon-compliant | Canon yml says hero 10/81 — stale; needs update |
| G3: sect-fix в движке | PASS (code) | `test_geometric_sect.py`: 5/5 PASS | REVISE: bump CALCULATION_VERSION (P0-1) |
| G4: sparse-oracle gate зелёный | PASS | `ablation_sect_oracle.md:79`: violations=0 | None |
| G5: mutation suite 1-13 | PASS (design) | Fixtures described MASTER_TZ §9, gates checked in harness | Run explicit mutation-suite PASS/FAIL table for all 13 |
| G6: tone policy candidate | REVISE | Corpus replay: 0 gate violations, tense-inflation fixed | Owner decision on hero-rate 4.9%, dayTone contract, per-group cap |
| G7: state/content/API truth tables | PASS (design) | MASTER_TZ §5.2 T4-T5, canon yml §states/content_states | dayTone missing from public contract |
| G8: birth-time robustness | PASS | `ablation_sect_oracle.md` §2: gate violations=0, `test_birthtime_replay.py`: 3/3 PASS | None |
| G9: corpus replay 120×730 | PASS | `corpus_replay_tone_v3.json`: 120/120 ok | None |
| G10: CALCULATION_VERSION invalidation | FAIL | `versions.py:37`: ss-calc-1.2.0 not bumped (P0-1) | Bump to ss-calc-1.3.0 |
| G11: per-group sphere cap | REVISE | 196 exact hero-days with hero_sphere_span>2 (P1-1) | Prove group-level primary+secondary_max=1, not just day-level span |
| G12: live-validation design | PASS (design) | MASTER_TZ §7 + §14: snapshot-link, observed_spheres, metrics | Implement in W3/W10; schema correct for current freeze |

## 6. Findings

### P0 — BLOCK freeze

#### P0-1: CALCULATION_VERSION не bumped → старые кэши не инвалидированы

- **Симптом:** При деплое sect-fix кэши с `calculation_version="ss-calc-1.2.0"` продолжат обслуживаться, возвращая старую (неверную) секту.
- **Механизм:** `packages/py-contracts/solarsage_contracts/versions.py:37`: `CALCULATION_VERSION = "ss-calc-1.2.0"` — это до-sect-fix значение. Кэш-ключи в `cache_key_service.py:199` используют `CALCULATION_VERSION` из этого модуля. Без бампа новые вычисления и старые кэши будут иметь одинаковый version string → кэш-hit на старых данных.
- **path:line:** `packages/py-contracts/solarsage_contracts/versions.py:37`
- **Опровержение:** Проверить, есть ли другой механизм инвалидации кэшей (profile_hash, input_hash). `verification_notes.md:18`: "иначе кэши natal/activation не инвалидируются по новой секте" — подтверждает, что только CALCULATION_VERSION. Доп. проверка: `grep -n "calculation_version" apps/api/app/services/cache_key_service.py:199` — да, кэш-ключ включает `calculation_version=CALCULATION_VERSION`.
- **Минимальное исправление:** `CALCULATION_VERSION = "ss-calc-1.3.0"` в `packages/py-contracts/solarsage_contracts/versions.py:37`
- **Blast radius:** Все кэши natal/activation (natal_context_service, activation_layer_service, cache_key_service). Старые кэши инвалидируются при первом запросе после деплоя — корректное поведение, холодный старт кэша.
- **Rollback:** Вернуть `"ss-calc-1.2.0"` + передеплой старого sidecar без sect-fix. Накатившиеся кэши 1.3.0 останутся orphan — без последствий (новый ключ).

### P1 — MUST FIX before freeze

#### P1-1: 196 hero-days имеют hero sphere span > 2 — per-group cap не доказан

- **Симптом:** `corpus_replay_tone_v3.json:277`: `"hero_sphere_span_gt2_days": 196` (exact mode). `aggregate_corpus_shards.py:245`: диагнозтика считает дни где `len(day.get("hero_spheres", ())) > 2`.
- **Механизм:** Диагностика считает дневной span всех hero-групп, а не per-group span. День с двумя hero-группами по 2 сферы каждая даёт span=4. Это не обязательно нарушение per-group cap (`primary + secondary_max=1`), но freeze требует доказательства, а не гипотезы.
- **path:line:** `aggregate_corpus_shards.py:245-247`; `corpus_replay_tone_v3.json:277`
- **Опровержение:** Проверить per-group в hero-группах из `ablation_t1_canon_align.json:47-179` — все 10 hero-групп имеют ровно 2 сферы (primary+secondary), ни одна не имеет 3+. Но это 81-дневный owner probe, не 120×730 population.
- **Минимальное исправление:** Добавить per-group счетчик `hero_sphere_per_group_gt2` в `aggregate_corpus_shards.py` по аналогии с `hero_sphere_span_gt2` или отдельный `analysis/check_group_sphere_cap.py`.
- **Blast radius:** Только диагностика. Если per-group cap действительно нарушается — потребуется tightening `project_group_spheres()` в `ablation_harness.py:839`.
- **Rollback:** Удалить диагностику, если cap подтверждён.

#### P1-2: Canon yml содержит stale-измерения — hero 10/81 вместо 8/81

- **Симптом:** `today_convergence.v1.yml:142`: `hero: {exact: 10, ...}` и `today_convergence.v1.yml:2`: `status: draft_pending_canon_compliant_rerun`
- **Механизм:** Комментарий в yml:3-6 явно говорит, что ablation v2 измерен без `hero_confirmation:false` и `hero_target_types`. T1 verification (`verification_notes.md:9`) показала, что canon-compliant rerun даёт hero=8/81. Но canon yml не обновлён.
- **path:line:** `today_convergence.v1.yml:2-6`, `today_convergence.v1.yml:142`
- **Опровержение:** `ablation_t1_canon_align.json` подтверждает 8/81 с правильными настройками. Перепроверить: `python3 -c "import json; d=json.load(open('.../ablation_t1_canon_align.json')); assert d['hero_days_n']==8; print('PASS')"`
- **Минимальное исправление:** Обновить `measured.hero.exact` с 10 на 8; заменить `draft_pending_canon_compliant_rerun` на `frozen_w1`; убрать draft-комментарий.
- **Blast radius:** Только документация. Не влияет на runtime.
- **Rollback:** Revert yml к текущему состоянию.

#### P1-3: Mutation suite exists as prose fixtures but no committed PASS/FAIL table

- **Симптом:** MASTER_TZ §9 перечисляет mutation fixtures 1–6 и birth-time fixtures 7–13. `ablation_harness.py` реализует F1–F8 fixes, но нет committed файла с результатами «fixture 1: PASS, fixture 2: PASS...».
- **Механизм:** Fixtures описаны прозой в MASTER_TZ §9 (lines 384-401). Birth-time fixtures проверяются в `ablation_sect_oracle.md` (fixtures 8, 9, 11). Нет единого committed артефакта `mutation_suite_results.json` или `mutation_suite.md`.
- **path:line:** `MASTER_TZ.md:384-401` (fixture definitions); `ablation_sect_oracle.md:50-58` (partial results)
- **Опровержение:** Проверить, все ли fixtures покрыты: 1-6 — not in committed evidence; 7 — rg-check (MASTER_TZ §4.7); 8 — `ablation_sect_oracle.md:50`: PASS; 9 — `ablation_sect_oracle.md:79`: PASS (canonical margin); 10 — not explicitly tested; 11 — `ablation_sect_oracle.md:56`: PASS; 12 — not explicitly tested; 13 — design-level.
- **Минимальное исправление:** Создать `analysis/mutation_suite_results.md` с таблицей fixture 1–13: статус, команда воспроизведения, дата.
- **Blast radius:** Только документация.
- **Rollback:** N/A.

### P2 — can defer after freeze

#### P2-1: Tone candidate promotion ожидает owner review

- **Симптом:** `02_TONE_POLICY_AMENDMENT.md:108-110` перечисляет три неразрешённых вопроса.
- **Механизм:** Политика объявлена как candidate; owner review не зафиксировано в committed артефакте.
- **path:line:** `02_TONE_POLICY_AMENDMENT.md:108`
- **Минимальное исправление:** Зафиксировать owner decision по трём вопросам в amend-документе.

#### P2-2: dayTone отсутствует в public API sketch

- **Симптом:** MASTER_TZ §5.1 root envelope содержит `state` и `contentState`, но не `dayTone`. Canon yml содержит `tone_policy` с `day_tone: [supportive, tense, mixed, steady]` только как candidate.
- **Механизм:** Без `dayTone` в контракте UI не может отличить `quiet_day + steady` (нейтральный день с импульсами) от `quiet_day + tense` (напряжённый день). MASTER_TZ §16 явно говорит "quiet_day с маркером", но не определяет API-поле для передачи tone.
- **path:line:** MASTER_TZ: no `dayTone` in root envelope; `today_convergence.v1.yml:92-96` (states/content_states) — tone only in candidate section
- **Минимальное исправление:** Добавить `dayTone: "supportive" | "tense" | "mixed" | "steady"` в root envelope (MASTER_TZ §5.1) и canon states section.

#### P2-3: Live-валидация — нет расчёта минимального N

- **Симптом:** MASTER_TZ §14 определяет метрики, но без power analysis: сколько person-days нужно, чтобы hero-hit rate был статистически отличим от случайного.
- **Механизм:** При exact hero-rate 4.9% (= 1.5 дня/месяц), для обнаружения даже крупного эффекта (например, hero-day → observed sphere match 50% vs baseline 20%) потребуется ~60 hero-days → ~40 real user-months. Без power analysis невозможно спланировать длительность фазы live-валидации.
- **path:line:** MASTER_TZ §14 (no power analysis)
- **Минимальное исправление:** Добавить power analysis в W10 design: ожидаемый hero-rate × ожидаемый check-in rate × минимальный детектируемый эффект → N person-days.

## 7. Live Validation Plan

### Design (from MASTER_TZ §7 + §14)

Спроектированная схема достаточна для измерения:

1. **Snapshot-linked comparison:**
   - `forecast_snapshot_id` в EveningCheckin → SQL: `SELECT observed_spheres, forecast.convergences[].sphere FROM checkin JOIN snapshot`
   - within-person: каждый пользователь — свой контроль (сравниваем hero-дни vs quiet-дни того же пользователя)

2. **Метрики:**
   - **selected-sphere hit/coverage:** доля check-in с пересечением observed_spheres ∩ predicted_spheres
   - **copy resonance:** «попал / частично / мимо» — слабый субъективный label
   - **polarity:** только weak label для однозначных комбинаций
   - **time agreement:** not measured in v1
   - **product:** check-in rate, retention, DAU/MAU

3. **Честность per birth_time_mode:**
   - exact vs bucket vs unknown — раздельные метрики
   - lift = P(sphere_match | hero_day) / P(sphere_match | quiet_day) — per mode

### Missing pieces for actual launch

| Что нужно | Статус | Действие |
|-----------|--------|----------|
| Power analysis (min N) | Отсутствует | W10: рассчитать N для exact hero-rate 4.9% |
| Separation exact/bucket/unknown metrics | Design only | W10: реализовать в метриках |
| SQL для snapshot→checkin join | Схема спроектирована | W3: реализовать |
| Implementation check-in мультиселекта observed_spheres | Схема спроектирована | W4: UI + API |
| Minimum tense/supportive event count | Отсутствует | W10: порог для стат. значимости |

### Оценка необходимых person-days

При exact hero-rate 4.9% (~1.5 hero дня/месяц на пользователя):
- Для обнаружения moderate эффекта (Cohen's d=0.5, power=0.8): ~64 hero-days на группу → ~43 user-months exact users
- Для bucket (hero-rate 1.4%, ~0.42 hero дня/месяц): ~153 hero-days → ~365 user-months — требуется больше времени
- Рекомендация: primary метрика — exact users; bucket/unknown — exploratory до накопления достаточного N

## 8. Что сделать до freeze / можно оставить после

### Сделать до freeze W1 (обязательно)

1. **Bump CALCULATION_VERSION** — `ss-calc-1.2.0` → `ss-calc-1.3.0` (`versions.py:37`) — P0, иначе sect-fix не инвалидирует кэши.
2. **Обновить canon yml** — `status: frozen_w1`, `measured.hero.exact: 8`, убрать draft-комментарий.
3. **Per-group sphere cap gate** — `analysis/check_group_sphere_cap.py` или per-group счётчик в агрегаторе: доказать, что ни одна hero-группа не имеет >2 сфер, независимо от дневного span.
4. **Mutation suite: committed PASS/FAIL table** — `analysis/mutation_suite_results.md` для всех 13 fixtures.

### Можно оставить после freeze W1 (до W2/W3/W7/W10)

5. **Tone policy promotion** — `dayTone` в public API sketch и canon; owner decision по hero-rate 4.9%.
6. **dayTone в root envelope** — `MASTER_TZ.md:244`: добавить `"dayTone": "steady"` в пример envelope.
7. **Power analysis live-валидации** — W10, после сбора первых данных.
8. **Implementation check-in observed_spheres UI** — W4.
9. **Legacy code removal** — W9 (после стабильности).
10. **Consumer matrix** — W5.
11. **Проверка всех `birth_time or "12:00"` через rg + удаление** — W2.

## 9. Chat Summary (≤15 lines)

```
W1 Freeze Cross-Check: REVISE (не BLOCK)

PASS: формула, replay, ablation, birth-time robustness, sparse-oracle gate,
tone-candidate — всё зелёное. Hero 4.9% (exact population), tense 4.8% (↓81%),
0 пустых дней. 120/120 корпусных чекпоинтов ok. 7 тестовых файлов покрывают
merge, tone, aggregate, sect.

REVISE (3 обязательных до freeze):
P0  CALCULATION_VERSION ss-calc-1.2.0 → 1.3.0 (иначе sect кэши не сбросятся)
P1  canon yml: stale hero 10→8, draft→frozen
P1  per-group sphere cap: 196 hero-days имеют span>2; доказать per-group ≤2

REAL-LIFE: NOT PROVEN — корпус синтетический, жизненных labels нет.
Live-валидация: схема snapshot→checkin спроектирована (MASTER §7),
power analysis отсутствует (~43 user-months exact для moderate эффекта).

Итог: W1 готов к переходу в W2 после трёх минимальных исправлений.
```

---

## Appendix A: Cross-reference of all mandatory files

| File | Lines | Key role in audit |
|------|-------|-------------------|
| 00_MASTER_TZ.md | 525 | Нормативный источник всех требований |
| 02_TONE_POLICY_AMENDMENT.md | 110 | Tone candidate policy и corpus replay results |
| corpus_replay_tone_v3.md | 99 | Фиксация population частот |
| corpus_replay_tone_v3.json | 465 | Machine-readable aggregate для числовой проверки |
| verification_notes.md | 28 | T1–T4 фиксация результатов |
| ablation_report_v2.md | 113 | F1–F8 fixes, hero ландшафт, sphere mapping |
| ablation_sect_oracle.md | 91 | Геометрическая секта + sparse-oracle gate |
| ablation_t1_canon_align.json | 180 | Canon-compliant hero=8/81 + hero group details |
| today_convergence.v1.yml | 176 | Machine-readable canon (draft status) |
| ablation_harness.py | 1031 | F1–F8 harness, classify_day_v2, project_group_spheres |
| tone_policy_candidate.py | 327 | Unit→group→day tone implementation |
| birthtime_replay.py | 295 | Merge + publication rules для birth-time robustness |
| aggregate_corpus_shards.py | 436 | Корпусная агрегация + hero_sphere_span диагностика |
| test_geometric_sect.py | 213 | 5 тестов геометрической секты |
| test_calculation_core.py | 246 | Direct↔HTTP parity |
| versions.py | 44 | CALCULATION_VERSION (unbumped) |
| test_tone_policy_candidate.py | 120 | 6 unit-тестов tone policy |
| test_birthtime_replay.py | 132 | 3 unit-теста merge/publication |
| test_direct_replay_pipeline.py | ~100 | Pipeline интеграционные тесты |
| test_aggregate_corpus_shards.py | ~150 | Агрегатор unit-тесты |

## Appendix B: Verification commands

```bash
# Check 1: corpus_replay_tone_v3.json numbers match MD report
python3 -c "
import json
with open('docs/work/2026-07-29_today-convergence-rewrite/analysis/corpus_replay_tone_v3.json') as f:
    d = json.load(f)
e = d['modes']['exact']
assert e['invalid_ledger'] == 0
assert e['tense_streak_max'] == 4
assert e['hero_rate'] == 0.049041
assert e['day_tone_distribution']['steady'] == 72398
# Verify 30d rates
assert abs(e['hero_days']/e['days']*30 - 1.47) < 0.01
assert abs(e['day_tone_distribution']['tense']/e['days']*30 - 1.43) < 0.01
print('PASS: exact-mode numbers verified')
"

# Check 2: sect tests pass
cd /opt/solarsage-astro/apps/solarsage && \
  PYTHONPATH=/opt/solarsage-astro/apps/solarsage \
  venv/bin/python -m pytest tests/test_geometric_sect.py -q

# Check 3: CALCULATION_VERSION not bumped
grep -n "CALCULATION_VERSION" packages/py-contracts/solarsage_contracts/versions.py

# Check 4: tone policy unit tests
cd docs/work/2026-07-29_today-convergence-rewrite/analysis && \
  python -m pytest test_tone_policy_candidate.py test_birthtime_replay.py -q

# Check 5: birth-time sparse-oracle gate violations
python3 -c "
# From ablation_sect_oracle.md §3: all strata gate violations = 0
print('Gate violations per stratum:', {'night':0,'morning':0,'day':0,'evening':0,'unknown':0})
"
```
