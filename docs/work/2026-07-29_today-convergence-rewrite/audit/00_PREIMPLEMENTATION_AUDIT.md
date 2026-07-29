# Pre-implementation Audit — today-convergence-rewrite

Date: 2026-07-29
Auditor: coding-leader (opencode/DeepSeek)
Scope: TZ `00_MASTER_TZ.md` vs actual codebase (`/opt/solarsage-astro`)

## Audit methodology

Каждый пункт аудита содержит:
- **TZ-требование** — цитата или ссылка на параграф TZ.
- **Текущее состояние** — что реально в коде, с указанием файла и строки.
- **Вердикт** — OK / GAP / DRIFT / RISK.
- **Рекомендация** — что нужно сделать перед/во время имплементации.

## Вердикты

| Вердикт | Значение |
|---------|----------|
| OK | Код уже соответствует TZ или не требует изменений |
| GAP | Требование TZ не реализовано в текущем коде — нужна новая имплементация |
| DRIFT | Текущий код делает обратное требованию — нужен осознанный перелом |
| RISK | Не ошибка, но потенциальный источник проблем: дублирование, нестыковка, неконтролируемое поведение |

---

## 1. Структурные GAP — инфраструктура, которой нет

### GAP-1. Snapshot persistence

**TZ §6:** Храним `published_snapshot` с полями: `snapshot_id, user_id, target_date, timezone, profile_hash, input_hash, canon_hash, formula_version, llm_prompt_version, calculated_at, published_at, state, deterministic_result, canonical_input, content_state, supersedes_snapshot_id`.

**Текущее состояние:** Ни одной модели/таблицы с этими полями не существует. Есть `TodayPayloadCache` (только cache_json) и `SemanticLayerCache` (только semantic_json) — ни один из них не является immutable snapshot. Нет понятий `published_at`, `supersedes_snapshot_id`, `canonical_input`.

**Рекомендация:** Новая таблица `day_snapshots` — часть волны W3. Не класть snapshot-поля в `TodayPayloadCache` — разделение ответственности: cache для скорости, snapshot для audit/replay.

### GAP-2. Check-in не связан с прогнозом

**TZ §7:** `forecast_snapshot_id` (nullable) + `prediction_seen_at` (nullable) + мультиселект `observed_spheres[]`.

**Текущее состояние:** `EveningCheckin` (`apps/api/app/db/models.py:603`) не имеет ни одного из этих полей. Текущий constraint: `(user_id, target_date)` уникален; поля: `mood, notes, mood_score, accuracy, energy, tags_json, note, streak`. Нет связи с forecast.

**Рекомендация:** Additive-миграция (W3): добавить nullable колонки в существующую таблицу, без нарушения текущих constraint. SQL должен однозначно соединять check-in → forecast.

### GAP-3. Formula version не хранится

**TZ §5:** `formulaVersion: "today-convergence-1"` в публичном контракте.

**Текущее состояние:** Ни в `TodayPayloadCache`, ни в `TodayPayload.meta` нет поля `formula_version`. Текущие поля meta: `calculation_version, normalization_version, scoring_version, prompt_version, content_version, payload_version, frontend_payload_version, activation_layer_version`. Ни одно из них не является `today-convergence-1`.

**Рекомендация:** Добавить `formula_version` в `TodayPayload.meta` и в `TodayPayloadCache` — W1/W3.

### GAP-4. Replay harness отсутствует

**TZ §9:** Replay-harness — постоянный инструмент в `scripts/`, синтетический корпус 100–200 натальных карт × 2–3 года, страты по широтам/timezone/DST.

**Текущее состояние:** Существуют `scripts/audit_today.py`, `scripts/audit_day_contract.py`, `scripts/prove_today_v2_real_api.py` — но это audit-скрипты для валидации текущего API, а не replay harness, способный пересчитать исторические срезы по новым формулам на корпусе.

**Рекомендация:** Новый инструмент `scripts/replay_harness.py` (W4), работающий от `canonical_input` из snapshot-таблицы.

### GAP-5. Mutation test suite отсутствует

**TZ §9:** 9 обязательных mutation-тестов (добавить дубль, убрать фактор, добавить нерелевантный, неизвестная сфера → excluded, перестановка, фон без якоря, противоположные факторы → mixed, сдвиг TZ/DST, immutable после publish).

**Текущее состояние:** Тесты существуют (`test_today_focus_builder.py`, `test_day_valence_engine.py`, `test_scoring_v2_family_dedup.py`), но они тестируют текущие контракты, а не новый pipeline. Нет ни одного mutation-теста, проверяющего инварианты из §9.

**Рекомендация:** Создать `tests/test_today_convergence_mutations.py` — W2/W4, до приёмки pipeline.

### GAP-6. Theme registry отсутствует

**TZ §4.5:** «связь по общей натальной точке ИЛИ узкой теме из theme registry (canon)».

**Текущее состояние:** Группировка в `today_focus_builder.py:720-753` использует только `target_key` и `theme_keys` (которые берутся из `primary_act.theme_keys` — поля activation layer). Нет отдельного theme registry как источника канонических тем для связывания факторов.

**Рекомендация:** Создать `grace/canon/theme_registry.v1.yml` как часть W1 — определить узкие темы, по которым факторы могут быть связаны даже без общей натальной точки.

---

## 2. DRIFT — код делает обратное требованию TZ

### DRIFT-1. Неизвестная сфера падает в work

**TZ §2, §4.4, §12.3:** «неизвестный фактор падает в work → unmapped исключается из выбора сферы». «Может ли неизвестный фактор попасть в work? (нет — исключается)».

**Текущее состояние:** `today_focus_builder.py:271`:
```python
return tuple(ordered) if ordered else ("work",)
```
Функция `_map_to_product_spheres` при отсутствии маппинга возвращает `("work",)` — fallback. Это противоречит TZ §4.4 явно: unmapped должен быть исключён, не уходить в work.

Также в `day_valence_service.py:285-298` факторы без technical-сфер не попадают в product-сферы (что правильно), но они всё равно участвуют в global dayStatus (line 313-318) — TZ это суперсидит.

**Рекомендация:** Убрать `("work",)` fallback в W2. Unmapped фактор: считается в `audit.excluded_unmapped`, не участвует в выборе сферы.

### DRIFT-2. Convergence по числу техник на target, а не по независимым событиям сферы

**TZ §2, §4.5:** «convergence объявляется по числу техник на target, а не по независимым событиям сферы». «Convergence только если: ≥2 разных canonical-события; ≥1 с сегодняшней динамикой; связь по общей натальной точке ИЛИ узкой теме из theme registry».

**Текущее состояние:** `semantic_v2_service.py:238`:
```python
has_convergence = len(top_activated_targets) > 0 and top_activated_targets[0].family_count >= 2
```
Convergence определяется как «≥2 техники (семьи) активируют один и тот же target». Это per-target, а не per-sphere. TZ требует per-sphere группы с ≥2 независимыми событиями в одной сфере.

В `today_focus_builder.py:740` группа считается валидной при `len(distinct_ids) >= 2` — это ближе к требованию, но связь проверяется только по `target_key` и `theme_keys`, без привязки к сфере и без требования «≥1 с сегодняшней динамикой».

**Рекомендация:** Переписать convergence-логику в W2: per-sphere группы, requirement «≥1 сегодняшний якорь», проверка независимости событий (разные canonical event_id, не копии), связь через target ИЛИ theme registry.

### DRIFT-3. Выбирается одна winning group, остальные сферы выбрасываются

**TZ §2, §4.7:** «выбирается одна winning group, остальные сферы выбрасываются». «Выбор 0–3 сфер. Независимые sphere-convergence группы, детерминированное ранжирование».

**Текущее состояние:** `today_focus_builder.py:815`:
```python
winning_group = candidate_groups[0]
```
Берётся только первая группа после ранжирования. Вся дальнейшая сборка (`convergence`, `featured_spheres`) строится вокруг этой одной группы. Featured spheres (до 3) — это сферы внутри winning group, а не независимые convergence-группы.

**Рекомендация:** Переписать в W2: каждая сфера — независимый кандидат на convergence. После фильтрации — до трёх лучших по evidence ↓ → evidence_level ↓ → канонический порядок.

### DRIFT-4. Глобальный dayStatus считается по всему ledger, включая фон

**TZ §2, §4.3:** «глобальный dayStatus считается по всему ledger, включая фон → „все дни тяжёлые“». «Фон сам не создаёт convergence — только контекст уже найденной группы».

**Текущее состояние:** `day_valence_service.py:313-318`:
```python
global_candidates = [
    (factor, self._calculate_factor_raw_magnitude(factor))
    for factor in ledger.factors
]
```
Все факторы, включая background, участвуют в расчёте global dayStatus. TZ суперсидит глобальный dayStatus как продуктовый результат.

**Рекомендация:** Удалить глобальный `dayStatus` (`supportive/steady/tense`) из API-ответа в W2. Заменить на per-sphere `polarity` (`supportive/tense/mixed`) и глобальное состояние: `convergence_today | single_impulse | no_signal | unavailable`.

### DRIFT-5. Используется confidence, а не evidence_level

**TZ §3.D5:** Поле называется `evidence_level` (high/medium/low) — мера количества независимых свидетельств, а не измеренная вероятность сбывания.

**Текущее состояние:** `day_valence_service.py:216-223`:
```python
if total >= 2.00 and ind_families >= 2:
    confidence = "high"
elif total >= 0.75:
    confidence = "medium"
else:
    confidence = "low"
```
Это `confidence` на основе суммы magnitude и числа семей — не соответствует определению `evidence_level` из TZ §4.6: `high = ≥2 независимых события + сегодняшний якорь; medium = один якорь + связанный поддерживающий фактор; low = только фон или слабый одиночный сигнал`.

**Рекомендация:** Переименовать и переопределить в W2: `evidence_level` с расчётной формулой §4.6. Старая confidence — удаляется вместе с `M-DAY-VALENCE`.

---

## 3. RISK — потенциальные проблемы

### RISK-1. Два разных mapping technical→product сфер

**Текущее состояние:** Два независимых механизма маппинга:
- `today_focus_builder.py:59-89` — `TECH_SPHERE_TO_PRODUCT_MAP` (жёстко закодирован).
- `day_valence_service.py:68` — `self.tech_to_product` (из `day_valence.v1.yml` канона).

Они могут расходиться. Найден пример: `TECH_SPHERE_TO_PRODUCT_MAP` содержит `"crisis_transformation": "decisions"`, `"crisis_transformation_control": "decisions"`, `"philosophy": "decisions"`, `"technology_innovation": "work"` — нужно сверить с каноном.

**Рекомендация:** Выбрать один источник truth для W2 — либо канон, либо единый python-словарь. Указать это в W1 как часть sphere mapping.

### RISK-2. Два разных порядка 12 сфер

**Текущее состояние:**
- `day_valence_service.py:42-55` — `CANONICAL_PRODUCT_SPHERES`: `work, money, documents, relationships, sport, communication, health, decisions, travel, creativity, study, shopping`
- `today_focus_builder.py:54-57` — `CANONICAL_PRODUCT_KEYS`: тот же порядок, но в tuple.

Порядок совпадает, но он дублирован. При изменении состава сфер легко забыть обновить оба места.

**Рекомендация:** W1: единый канонический источник 12 сфер в `grace/canon/product_spheres.v1.yml` (или в `day_valence.v1.yml`). Импортировать из одного места.

### RISK-3. `strip_prefix` для Transit_/Natal_ делается непоследовательно

**TZ §4.2:** «Префиксы `Transit_`/`Natal_` стриппятся здесь».

**Текущее состояние:** `today_focus_builder.py:264` вызывает `strip_prefix` для source_key/target_key в `_map_to_product_spheres`. Но `today_service.py:966` вызывает `strip_prefix` в `_build_top_flag` — для `icon_planet` стриппится, для `PlanetInfluence` (line 1077) тоже стриппится. Однако `today_service.py:209` (известный баг №1 AGENTS.md) — `_build_top_flag` использует `signal.planet` без strip_prefix для title. Проверим:

```python
# today_service.py:966
planet = TodayService._planet_label(signal.planet)
# _planet_label вызывает strip_prefix внутри — OK
```

**Баг №1 из AGENTS.md** (Transit_ в UI): `today_service.py:973` — `title=f"{planet} {aspect} {target}"`. Здесь `planet` уже получен через `_planet_label`, которая делает strip_prefix. Но `signal.planet` на входе может иметь префикс. Проверил: `_planet_label` делает `strip_prefix(name)` — значит баг должен быть закрыт. Однако в `_build_top_flag` сигнал идёт через `scoring_result["top_signals"]`, которые приходят из normalization. Нужно точечно проверить, стриппятся ли префиксы в самом scoring layer.

**Рекомендация:** W2: сделать canonical event_id stripping в единой точке — шаг 2 pipeline (§4.2). Написать тест, доказывающий отсутствие `Transit_`/`Natal_` в публичных полях ответа.

### RISK-4. LLM deadline разный

**TZ §2:** «bounded LLM-фаза: единый `deadline_at`, provider timeouts `min(60, remaining)`, DeepSeek provider-fallback при remaining ≥ 15s».

**Текущее состояние:** `today_service.py:153` — `LLM_PHASE_DEADLINE_SECONDS = 25`. Provider-fallback есть, но deadline другой. TZ пишет «переиспользуем» — нужно уточнить, должен ли deadline быть `min(60, remaining)` или остаётся 25s.

**Рекомендация:** Уточнить в W1. Если deadline меняется на 60s — обновить константу.

### RISK-5. Поле `confidence` в схеме `ProductSphereAssessment` используется фронтендом

**Текущее состояние:** `ProductSphereAssessment.confidence` (low/medium/high) — поле Pydantic-схемы, используемое через valence pipeline. Фронтенд `lib/contracts/today.ts:197` содержит `kind: "day_status"` в evidence, но schema `DayStatusSchema = z.enum(["supportive", "steady", "tense"])` — фронтенд пока не потребляет per-sphere confidence/evidence_level.

**Рекомендация:** При замене `confidence` на `evidence_level` проверить все потребители (W7): фронтенд, audit-скрипты, pregen.

### RISK-6. Calendar chips зависят от dayStatus

**TZ §10:** Calendar chips потребляют старый dayStatus — `calendar_service.py:233` читает `data.get("dayStatus")` из кэша.

**Текущее состояние:** `calendar_service.py:233`:
```python
status = data.get("dayStatus") or data.get("day_status")
```
И `components/calendar/calendar-screen.tsx:96` использует `day.dayStatus` для раскраски чипов. TZ суперсидит dayStatus как глобальное понятие.

**Рекомендация:** В W5/W7: календарные чипы должны показывать max(evidence_level) по всем сферам дня или специальный calendar_tone, выводимый из нового convergence-результата.

### RISK-7. Yesterday screen и check-in hint используют dayStatus

**TZ §10:** Yesterday screen; check-in forecast hint (`checkin-screen.tsx:261`).

**Текущее состояние:** `checkin-screen.tsx:261`:
```tsx
{dayStatusHint ? (
  <...>Прогноз: {dayStatusHint}</...>
) ...}
```
И `components/today/today-screen.tsx:254,356` передаёт `dayStatus={payload.dayStatus}`.

**Рекомендация:** W7: заменить `dayStatusHint` на сводку из нового convergence-результата (состояние дня + топ-сферы).

---

## 4. OK — что уже соответствует

### OK-1. Canonical events / timing classification / provenance (W4 B1/B2, W6-S1)

Переиспользуется без изменений согласно TZ §2.

### OK-2. Public event selection (27_TZ amendment, 31_TZ W6-S1)

`today_focus_builder.py:534-619` — `select_public_events` с резервированием winning anchor, ранжированием и display sorting. Переиспользуется.

### OK-3. Bounded LLM-фаза с deadline, CancelledError пробросом

`today_service.py:556-617` — asyncio.wait с deadline, cancel+await для pending. Переиспользуется.

### OK-4. Schema-валидатор матрицы state×content_state + caps + dup IDs

`today_service.py:1132-1138` (quality predicate для cache). Переиспользуется.

### OK-5. Честный cache: unavailable никогда не «тёплый»

`today_service.py:1136`: `state == unavailable -> miss`. Переиспользуется.

### OK-6. Запрет fallback-копирайтинга (21_TZ §6.6)

`today_service.py:756-758`: `focus_content_state = "unavailable"` при провале валидации или provider error. Текстовые fallback-строки в `headline`, `reading_paragraphs`, `notes_text`, `why_sections` — это legacy, но они в блоке `if not headline:` и т.д. — для старых LLM-полей, не для нового focus-блока. Для focus-блока fallback уже НЕ текстовый (content_state=unavailable без подстановки). OK.

### OK-7. Sanitized fixtures (30_TZ); локальное время в LLM evidence (фикс §3.3)

Переиспользуется.

### OK-8. LLMClaimValidator для focus_narrative

`today_service.py:739-754` — существует `LLMClaimValidator` с `check_focus_narrative_safety`. Нужно расширить для нового копирайт-канона (§8), но базовая инфраструктура есть.

---

## 5. Blast radius — верификация TZ §10

TZ утверждает следующий blast radius. Проверяем актуальность:

| Потребитель | TZ-локация | Фактический код | Статус |
|---|---|---|---|
| Calendar chips | `calendar_service.py:156-263` | `calendar_service.py:233` читает `dayStatus`, `calendar-screen.tsx:96` рендерит чипы | ✓ актуально |
| Yesterday screen | упомянут | `today_service.py:300` — DayDelta вычисляется, но yesterday screen как отдельный endpoint? Не нашёл. Возможно в планах | ? требует уточнения |
| Check-in forecast hint | `checkin-screen.tsx:261` | `checkin-screen.tsx:261` — `Прогноз: {dayStatusHint}` | ✓ актуально |
| DaySummaryCard / DayChart / WeekStrip | упомянуты | `day-summary-card.tsx:63` — `dayStatus`, `day-chart.tsx:153` — `dayStatus`, `WeekStrip.tsx:91-93` — `day.dayStatus` | ✓ актуально |
| audit-скрипты | `audit_today.py`, `audit_day_contract.py`, `prove_today_v2_real_api.py` | Все три существуют в `scripts/` | ✓ актуально |
| semantic cache | `SemanticLayerCache` | `models.py:395` — содержит `semantic_json` с day_status | ✓ актуально |
| score history | `DayScoreHistory` | `models.py:1548` — support_score/tension_score для relative status | ✓ актуально |
| pregen | `day_pregen.py:113` | `day_pregen.py:113` — вызывает `TodayService.get_today_payload` | ✓ актуально |

**Новые потребители, не упомянутые в TZ §10:**
- `components/grace/ReadingCard.tsx:55` — `entry.dayStatus`
- `components/today/day-zone-indicator.tsx:33` — `relativeStatus`
- `lib/contracts/today.ts:312,326` — `DayStatusSchema`, `relativeStatus`

Все они должны быть обновлены в W7.

---

## 6. Итоговая сводка по волнам

| Волна | Статус до начала | Критические GAP/DRIFT |
|-------|-----------------|----------------------|
| W0 | ✓ Закрыта TZ | — |
| W1 (контракт + canon) | Требует theme registry, единого mapping-источника, копирайт-канона | RISK-1, RISK-2, GAP-6 |
| W2 (pipeline) | Текущий pipeline делает обратное: одна группа, work-fallback, confidence не evidence_level | DRIFT-1…5 |
| W3 (persistence) | Нет snapshot-таблицы, check-in не связан с forecast | GAP-1, GAP-2, GAP-3 |
| W4 (replay + mutation) | Нет replay harness, нет mutation suite | GAP-4, GAP-5 |
| W5 (API + pregen) | pregen вызывает TodayService, нужна доработка typed outcomes | OK (базовый вызов) |
| W6 (LLM) | LLMClaimValidator есть, но не полный копирайт-канон | На базе OK-8 |
| W7 (frontend) | Множество потребителей dayStatus/relativeStatus | RISK-6, RISK-7 |
| W8 (cutover) | Механизм orchestrator есть | OK |
| W9 (legacy removal) | gate `rg` описан в TZ | По факту W7 |
| W10 (валидация) | Будет после накопления данных | N/A |

## 7. Рекомендуемый порядок действий

1. **Перед W1:** Закрыть RISK-1 (единый mapping), RISK-2 (единый список сфер), GAP-6 (theme registry). Это — prerequisite для pipeline.
2. **W1:** Закрепить все каноны письменно: evidence-коэффициенты, пороги, копирайт-блэклист, few-shot эталоны. Без этого W2 не на чем строить.
3. **W2:** Полный rewrite pipeline. Не пытаться чинить старый — строить новый параллельно. Старый код НЕ удалять до W9.
4. **W3:** Additive-миграции БД. Новые колонки nullable, не ломать существующие constraint.
5. **Параллельно W2-W3:** W4 — replay harness на синтетическом корпусе ДО того, как новый pipeline пойдёт в прод. Это страховка от повторения valence-drift.
6. **W5-W7:** Подключать потребителей по одному, с e2e-тестами на каждом шаге.
7. **W8:** Cutover только после зелёного mutation suite + replay-отчёта без патологий.
