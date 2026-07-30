# Implementation Pack Audit — Today Convergence Rewrite v1.10

Дата: 2026-07-30
Аудитор: coding-leader (DeepSeek-v4)
Scope: `00_MASTER_TZ.md` v1.10, `04_W2_W3_RUNTIME_CONTRACT_TZ.md`,
       `05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md`,
       `03_W7_FRONTEND_DESIGN_TZ.md`, `AGENTS.md` (UI contract section),
       а также cross-reference с frozen W1 canon (`grace/canon/today_convergence.v1.yml`,
       `02_TONE_POLICY_AMENDMENT.md`, `analysis/W1_FREEZE_DELTA_ATTESTATION.md`).

Verdict: **PASS — implementation pack coherent, W1 canon immutability confirmed.**

---

## 1. W1 immutability check (primary gate)

| Артефакт | Состояние | Доказательство |
|---|---|---|
| `grace/canon/today_convergence.v1.yml` | `frozen_w1`, без diff | `git diff` — 0 изменений |
| `docs/work/.../02_TONE_POLICY_AMENDMENT.md` | `frozen_w1 / owner-approved` | без diff |
| `analysis/W1_FREEZE_DELTA_ATTESTATION.md` | fingerprint `89be0b8e…`, `ss-calc-1.3.0` | без diff |
| `analysis/corpus_replay_tone_v3.md` / `.json` | source fingerprint `90c691f0…` | без diff |
| `analysis/test_convergence_canon.py` и suite | 14 + 46 passed | без diff |
| `00_MASTER_TZ.md` W1-нормативы (§4, D7/C1, T1–T5, invariants, replay §9) | неизменны с v1.8 | diff: только downstream-дополнения, см. §2 |

**Вывод**: W1 formula/canon, replay fingerprint и расчётная версия действительно не изменялись. Diff `00_MASTER_TZ.md` (v1.8 → v1.10) затронул только downstream-уточнения: явная `angles` capability, identity-constraint (добавлен `input_hash` + `calculation_version`), отделение LLM content от deterministic snapshot, кросс-ссылки на `04_W2_W3_RUNTIME_CONTRACT_TZ.md` и content-cap gate. Ни одно из этих изменений не касается расчётной истины, eligibility-правил, hero-норматива или truth tables.

---

## 2. AGENTS.md UI contract sync

`AGENTS.md` получил 26 insertions / 7 deletions в секции «UI Semantic/Test Contract»:

- **Добавлены:** новый multi-axis контракт (`data-state`, `data-screen-state`, `data-day-tone`, `data-content-state`, `data-access-state`, `data-birth-time-mode`) с полными enum-значениями.
- **Маркированы как superseded:** старый `data-status="calm|tense|favorable|neutral"`.
- **Пример контракта переписан:** с `today-summary` + `data-status` на `today-screen` с шестью атрибутами.
- **Тест-пример переписан:** `quiet_day` + `ready` + `steady` + `aria-expanded`.

**Верификация против `03_W7_FRONTEND_DESIGN_TZ.md`:**

| Элемент контракта | 03_W7 §11 | AGENTS.md | Совпадение |
|---|---|---|---|
| Root testid | `today-screen` | `today-screen` | ✅ |
| data-state | `convergence_today \| quiet_day \| unavailable` | дословно то же | ✅ |
| data-screen-state | `loading \| ready \| error` | дословно то же | ✅ |
| data-day-tone | `steady \| supportive \| mixed \| tense` | дословно то же | ✅ |
| data-content-state | `ready \| pending \| unavailable \| not_needed` | дословно то же | ✅ |
| data-access-state | `full \| preview \| locked` | дословно то же | ✅ |
| data-birth-time-mode | `exact \| bucket \| unknown` | дословно то же | ✅ |
| Старый data-status | superseded и удаляется в W7 | «superseded и не используется» | ✅ |

**Вывод**: AGENTS.md полностью синхронизирован с frontend-контрактом 03_W7. Никаких расхождений.

---

## 3. Cross-document contract consistency

Проведён trace 12 ключевых концептов через все 5 документов:

| Концепт | 00_MASTER | 04_W2_W3 | 03_W7 | 05_W5_W8 | canon.yml | Вердикт |
|---|---|---|---|---|---|---|
| state enum | `convergence_today\|quiet_day\|unavailable` | то же | то же | то же | то же | ✅ |
| dayTone | `supportive\|tense\|mixed\|steady\|null` | то же | `steady\|supportive\|mixed\|tense` (order only) | `state/dayTone` distribution | то же | ✅ |
| contentState | `ready\|pending\|unavailable\|not_needed` | то же | то же | то же | то же | ✅ |
| access state | `full\|preview\|locked` | то же | `full / preview / locked` | то же | — | ✅ |
| birthTimeMode | `exact\|bucket\|unknown` | то же | то же | — | то же | ✅ |
| formulaVersion | `today-convergence-2` | то же | — | — | то же | ✅ |
| calcVersion | `ss-calc-1.3.0` | то же | — | — | attestation: bump 1.2→1.3 | ✅ |
| snapshot immutability | неизменяем после publish | то же + supersedes | — | — | — | ✅ |
| lookahead | только frozen snapshot | только published | только если API дал | — | — | ✅ |
| previewTeaser | server-side projection | 0..3 sphere names | то же | — | — | ✅ |
| State×content matrix | 5.2 / 5.2.1 | 3.2 полная | 2 / 5.6 (implied) | — | canon §states | ✅ |
| Capabilities (angles) | `angles` добавлен явно | `angles: true/false` в wire | — | `angles_available` в LLM | canon: `angles: true\|false` per mode | ✅ |

### Cross-document consistency особого внимания:

**A. `state=unavailable` ≠ `contentState=unavailable`** — прослежено:
- 00_MASTER §5.2.1: «`state=unavailable` ... персональный snapshot отсутствует; это не то же состояние, что LLM-сбой `contentState=unavailable`»
- 04_W2_W3 §3.2: две отдельные строки в матрице; `state=unavailable` → snapshotId null, всё пусто; `contentState=unavailable` → deterministic поля сохранены
- 03_W7 §5.5 vs §5.6.1: разные UI-блоки, разное поведение
- 05_W5_W8 §3: «`contentState=unavailable` ... deterministic fields = unchanged»
✅ Последовательно.

**B. `locked` → `state=null`** — прослежено:
- 04_W2_W3 §3.1/3.2: state nullable только для locked
- 03_W7 §2: «state=null только при locked»
- 04_W2_W3 §8.8: «locked не раскрывает snapshot/event IDs»
✅ Последовательно.

**C. Cohort pregen: две стадии, 14d ↔ 7d** — прослежено:
- 00_MASTER §5.4 / D13: calculation cohort (14d) → selective LLM warm-up (7d, full access)
- 05_W5_W8 §2.1/2.2: ровно те же числа и политика
- User summary: «ночью считаем не всю базу, а активных за 14 дней; LLM греем активным за 7 дней с полным доступом»
✅ Последовательно.

**D. LLM 700-token cap** — прослежено:
- 05_W5_W8 §3: `TODAY_NARRATIVE_MAX_OUTPUT_TOKENS=700`
- 05_W5_W8 §4: content-cap gate с fixture №4 и №8 при 700 токенах
- 03_W7 §10: `summary.text ≤ 220 chars` как UI-ограничение
- Связь 700 tokens → 220 chars: implicit через валидатор (05_W5_W8 §3: «Ответ валидируется и принимается только целиком»)
⚠️ Неявная связь, но функционально не противоречит.

**E. Check-in linkage** — прослежено:
- 00_MASTER §7: `forecast_snapshot_id`, `prediction_seen_at`, `observed_spheres[]`, `prediction_seen_surface`
- 04_W2_W3 §7.3: полный wire-контракт impression + check-in
- 04_W2_W3 §8.6: «snapshot→day/lookahead impression→check-in SQL join»
- 03_W7 §5.9: lookahead impression с `surface=lookahead`
✅ Последовательно.

**F. Local date resolver** — прослежено:
- 00_MASTER §4.1: «локальный день пользователя `current_tz → birth_tz → UTC`»
- 04_W2_W3 §5: приоритет `profile.current_tz → profile.birth_tz → UTC`
- 05_W5_W8 §5.1: «Все consumer'ы используют один local-date resolver»
- 00_MASTER §10: «единый resolver ... используется day/today, calendar, drilldown, yesterday, check-in и pregen»
✅ Последовательно.

---

## 4. Обнаруженные расхождения

### 4.1 Bucket boundary: три стиля записи — эквивалентны, но разная точность (⚠️ MINOR)

| Источник | Запись night | Стиль |
|---|---|---|
| 00_MASTER_TZ §4.7 | `00:00–06:00` | полуинтервал [start, end) |
| 04_W2_W3 §4.1 | `00:00–05:59` | замкнутый справа |
| `grace/canon/today_convergence.v1.yml` | `night: [0, 6]` | целые часы, семантика не уточнена |

Все три записи описывают один и тот же интервал ([00:00, 06:00) = 00:00–05:59 = [0, 6) часов), но inconsistency в стиле создаёт читательскую неоднозначность.

**Рекомендация**: добавить в canon.yml явный комментарий `# [start_hour, end_hour) — левый замкнут, правый открыт` и/или нормализовать 00_MASTER на `05:59` для однозначности. Не блокирует W2.

### 4.2 700-token cap и 220-char summary: связь неявная (⚠️ MINOR)

- 05_W5_W8 §3: `TODAY_NARRATIVE_MAX_OUTPUT_TOKENS=700`
- 05_W5_W8 §4 (W6 gate): фикстуры #4/#8 при 700 токенах, без уточнения per-field char limits
- 03_W7 §10: `summary.text ≤ 220 chars` как UI-ограничение

Связь между общим 700-token cap и per-field 220-char limit не прописана в 05_W5_W8 явно. Оба ограничения отдельно разумны и не противоречат друг другу, но W6 content-cap gate (§4) должен включить проверку 220-char limit как часть payload validation.

**Рекомендация**: в 05_W5_W8 §4 явно добавить проверку `summary.text ≤ 220 chars` в content-cap gate.

### 4.3 `state=unavailable` — presentation T4 vs runtime §3.2 (ℹ️ TRIVIAL, resolved)

- 00_MASTER T4: ранее v1.8 содержало «честный статус, детерминированные факты — если есть»; в v1.10 исправлено на «честный статус; персональный snapshot и частичные факты не публикуются». ✅ Исправлено.
- 04_W2_W3 §3.2: `state=unavailable` → snapshotId null, все персональные поля пусты. ✅
- 03_W7 §5.5: «Персональный snapshot и его факты не показываются». ✅

### 4.4 `verification-matrix.md` — не обновлён для W2–W9 (ℹ️ NOTE, ожидаемо)

`grace/verification-matrix.md` не имеет изменений — зарегистрирована только W1 freeze строка. Это ожидаемо: матрица обновляется каждой волной при регистрации gates, а W2 ещё не стартовала. Не является дефектом.

---

## 5. Проверка граничных утверждений пользователя

| Утверждение | Проверка | Результат |
|---|---|---|
| «зарегистрированы новые ТЗ, W1 остаётся frozen» | W1 canon и replay — 0 diff | ✅ подтверждено |
| «ночью считаем не всю базу, а активных за 14 дней» | 05_W5_W8 §2.1: `DAY_PREGEN_ACTIVE_DAYS=14` | ✅ подтверждено |
| «LLM греем активным за 7 дней с полным доступом» | 05_W5_W8 §2.2: `DAY_PREGEN_LLM_ACTIVE_DAYS=7` + access=full gate | ✅ подтверждено |
| «старые V1/V2-контракты не адаптируем и не тащим в новую модель» | 00_MASTER §2: полный boundary rewrite §, W9 manifest | ✅ подтверждено |
| «AGENTS.md — старый Today data-status заменён новым DOM-контрактом» | diff AGENTS.md: старый контракт → `superseded`, новый контракт 1:1 с 03_W7 | ✅ подтверждено |
| «W1 canon, расчётная версия и replay-артефакты не изменялись» | `grace/canon/today_convergence.v1.yml` — 0 diff; `ss-calc-1.3.0` стабилен с W1 | ✅ подтверждено |

---

## 6. Итог

| Категория | Статус |
|---|---|
| W1 canon immutability | ✅ PASS |
| AGENTS.md UI contract sync | ✅ PASS |
| Cross-document contract consistency (12 концептов × 5 док.) | ✅ PASS |
| Новые понятия: snapshot/check-in/exact-bucket-unknown/local-date/cohort-preheat/700-token-cap | ✅ PASS |
| Граничные утверждения пользователя | ✅ 6/6 подтверждено |
| Bucket boundary notation inconsistency | ⚠️ MINOR (не блокирует) |
| 700-token ↔ 220-char implicit linkage | ⚠️ MINOR (рекомендация: явная проверка) |
| W1 freeze attestation path reference | ℹ️ TRIVIAL (относительный путь корректен) |
| verification-matrix.md не обновлён | ℹ️ NOTE (ожидаемо, W2 ещё не стартовала) |

**Implementation pack готов к start W2. Критических блокирующих расхождений не обнаружено.**

Два MINOR замечания носят характер specification precision и не требуют изменений в W1 canon или повторного replay.
