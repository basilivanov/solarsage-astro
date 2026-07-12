# Stage B3.W2 — architect review R1: exact canon boundary and missing proofs

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted parent HEAD/origin: `ecae4d0ff95bf29953fbb6957e48c38a7d22e198`
Parent documents: `75`, `76`, `77`, `78`
Статус: **CORRECT CURRENT W2 WIP WITHOUT COMMIT/PUSH**

## 1. Review verdict

Текущий callback `READY_STAGE_B3_W2_REVIEW` не принят.

Основная интеграционная логика собрана правильно, focused backend gate проходит
`148 passed`, а generated contract gate проходит `21 passed`. Однако найден один
реальный production-дефект публичного audit boundary и отсутствует несколько
обязательных доказательств из разделов 5, 9, 11, 12, 14 и 16 документа `78`.

Исправить только перечисленное ниже. Не расширять scope, не начинать B3.W3 или
B4, не делать commit/push.

## 2. Production blocker: scoring canon map may escape the exact nine-key boundary

### 2.1 Reproduced current behavior

В `SemanticV2Service.build_v2_block` сейчас выполняется безусловный overlay:

~~~py
canon_versions = get_canon_versions()
scoring_canons = getattr(scoring_result, "canon_versions", {}) or {}
canon_versions.update({str(k): str(v) for k, v in scoring_canons.items()})
~~~

Architect reproduction поверх текущего WIP доказал:

~~~text
input scoring canon additions:
  unknown_runtime_key = sentinel
  horizon_selection = stale-v0

public v2.audit.canonVersions result:
  contains unknown_runtime_key
  horizon_selection = stale-v0
~~~

Это нарушает одновременно два W2-инварианта:

- fresh public `v2.audit.canonVersions` должен содержать ровно девять известных
  ключей;
- четыре horizon canon version должны исходить из текущих horizon canon
  services и не могут быть подменены произвольным/stale scoring input.

### 2.2 Required correction

В `SemanticV2Service.build_v2_block` сформировать audit map так:

1. Базой является новый `get_canon_versions()` — ровно девять текущих ключей.
2. Из `scoring_result.canon_versions` разрешено переносить только известные
   core-scoring ключи, уже принадлежащие `CANON_VERSIONS`:
   - `spheres`;
   - `dignities`;
   - `aspect_rules`;
   - `activation_rules`;
   - `scoring_v2`.
3. Не дублировать этот список вручную. Получить allowlist из существующего
   канонического источника `CANON_VERSIONS` в `canon_service.py` либо из
   эквивалентного уже существующего canonical source.
4. Не принимать из scoring map четыре horizon keys:
   - `horizon_selection`;
   - `horizon_language_ru`;
   - `horizon_actions_ru`;
   - `personal_patterns_ru`.
5. Не принимать неизвестные ключи.
6. Не мутировать `scoring_result.canon_versions` и возвращаемый объект
   `get_canon_versions()` вне локального построения audit map.
7. Итоговый fresh audit map содержит ровно девять строковых ключей и строковых
   значений.

Не добавлять silent fallback на пустой audit map и не ослаблять публичную
Pydantic-схему.

### 2.3 Required regression test

Добавить тест в
`apps/api/tests/test_payload_v2_downstream_mapping.py` либо другой уже
allowlisted W2 semantic test:

1. Создать валидный typed `ScoringV2Result`.
2. Передать в его `canon_versions`:
   - хотя бы один известный core key с отличимым значением;
   - stale `horizon_selection` с отличимым значением;
   - `unknown_runtime_key=sentinel`.
3. Построить `TodayV2Block`.
4. Доказать:
   - множество ключей audit map равно exact nine-key set;
   - известный core key сохранён по принятой merge-семантике;
   - stale scoring `horizon_selection` не подменил текущий horizon canon;
   - unknown key отсутствует;
   - исходный scoring map byte-identical до/после вызова.

## 3. Missing public identity contract proofs

Текущие validators выглядят логически корректно, но обязательные негативные и
compatibility cases документа `78` тестами не доказаны.

### 3.1 Add current/previous Pydantic cases

В `apps/api/tests/test_today_meta_versions.py` или
`apps/api/tests/test_today_horizons_contract.py` добавить typed tests, которые
используют полный минимально валидный `TodayPayload`, а не прямой вызов только
`TodayV2Block`:

1. `today.v2.1` + frontend `3` + non-null V2 body + отсутствующий
   `v2.audit.horizonPipeline` отклоняется с structural error.
2. `today.v2.1` + frontend `2` отклоняется как contradictory current pair.
3. `today.v2` + frontend `3` отклоняется как contradictory current pair.
4. Previous `today.v2` + frontend `2` + non-null V2 body без
   `horizonPipeline` принимается.
5. Current valid pair + matching audit payload version принимается.
6. Current valid pair, где `v2.audit.payloadVersion != meta.payloadVersion`,
   отклоняется.
7. Existing V1 + null V2 compatibility остаётся зелёной.

Не пытаться доказывать cross-object Pydantic validators generated Zod-тестом:
эта граница уже зафиксирована в `78 §13.1`.

### 3.2 Reason enum parity

Публичный unavailable union вынужденно перечисляет non-selected reasons для
генерации строгого Zod union. Добавить parity test через `typing.get_args`:

~~~text
public unavailable reasons
  ==
internal HorizonSelectionReason minus {selected}
~~~

Также доказать, что built variant разрешает только `selected`. Это защищает от
тихого drift при будущем добавлении selector reason.

Если для теста нужен экспорт public alias — экспортировать существующий alias,
не создавать второй список значений.

## 4. Missing cache proofs

### 4.1 Every horizon canon must affect the hash

В `apps/api/tests/test_today_cache_v2_key.py` добавить parameterized test для
всех четырёх horizon canon keys.

Тест должен monkeypatch-ить тот lookup, который реально вызывает
`build_today_cache_key`, строить base key и key с изменённой ровно одной
horizon-version, затем доказывать разные:

- `canon_versions_hash`;
- `cache_key_hash`.

Проверить все четыре keys, не только один пример.

### 4.2 Current stale/contradictory cache rows must miss

Добавить DB-level либо isolated `_get_cached_payload` tests:

1. Current `today.v2.1/frontend=3` с non-null V2 body, но без pipeline audit —
   cache miss, исключение наружу не выходит.
2. Current payload/version mismatch (`today.v2.1/frontend=2` или
   `today.v2/frontend=3`) — cache miss, исключение наружу не выходит.
3. Previous `today.v2/frontend=2` с валидным V2 body без pipeline audit —
   остаётся parseable cache hit при совпадающем cache identity, либо отдельно
   доказывается как Pydantic-compatible input, если старый cache hash намеренно
   уже не может совпасть с current read key.

Не ослаблять current validator ради старого cache.

## 5. Missing integration-service failure/log proof

В `apps/api/tests/test_today_horizon_integration_service.py` добавить test,
который вызывает именно `TodayHorizonIntegrationService.build`, а не только
`derive_sphere_verdicts`, с malformed advice mapping.

Для missing и/или duplicate case доказать:

- exact `HorizonVerdictMappingError.code`;
- injected pipeline вызван `0` раз;
- emitted ровно один event;
- envelope: `W-DAY / M-TODAY-SERVICE / HORIZON_PIPELINE`;
- event `day.payload_built`;
- level `error`;
- fixed message без exception/input text;
- exact payload:
  `failed / verdict_mapping_invalid / 0 / [] / null`;
- `duration_ms == 0.0` для pre-pipeline mapping failure;
- raw label/text/evidence/profile/unknown-key sentinels отсутствуют во всём
  captured event.

Усилить existing built/unavailable tests assertions на:

- `level=info`;
- exact fixed message;
- numeric rounded `duration_ms`;
- отсутствие activation/fact/action IDs и human copy sentinels.

Production integration service менять не нужно, если новые tests подтверждают
его текущее поведение.

## 6. TodayService exact request-local identity proof

Документ `78` требует доказать exact reuse всех четырёх already-computed
objects. Текущий TodayService test проверяет exact scoring/natal/advice, но для
activation проверяет только version/non-null.

В одном existing V2-selected TodayService test:

1. Подменить `ActivationLayerService.build` так, чтобы он вернул заранее
   созданный typed sentinel `ActivationLayer`.
2. Доказать, что integration spy получил:
   - `activation_layer is sentinel_activation_layer`;
   - `scoring_result is v2_result`;
   - `natal_context is fake_natal`;
   - `concrete_advice is payload.concrete_advice`.
3. Доказать один вызов integration service.
4. Не добавлять второй activation/scoring/natal computation.

## 7. Audit-tool current identity coverage

Production logic двух audit scripts выглядит совместимой с previous/current
identity, но tests по-прежнему моделируют fresh live output как
`today.v2/frontend=2`.

Исправить tests, не расширяя production scripts:

1. Хотя бы один live-production audit test должен моделировать fresh response
   как `today.v2.1/frontend=3` и ожидать эти значения в artifact source.
2. Missing-V2-body test должен доказать current identity recognition.
3. Отдельный маленький pure test сохраняет recognition предыдущей пары
   `today.v2/frontend=2`.
4. Synthetic downstream audit test должен assert, что сгенерированная fresh
   meta identity равна `today.v2.1/frontend=3`.

Не переписывать legacy audit scripts и не добавлять в них horizons synthesis.

## 8. GRACE corrections for changed public boundaries

Не устранять весь существующий legacy GRACE debt. Исправить только contracts,
которые стали неточными или отсутствуют на изменённых W2 boundaries:

1. `TodayPayload.validate_v2_identity_requires_body` — добавить paired
   `START_FUNCTION_CONTRACT/END_FUNCTION_CONTRACT` с current/previous pair,
   pipeline audit и error policy.
2. Existing `TodayV2Block.validate_optional_horizons` contract — обновить
   purpose/error text так, чтобы он описывал audit-to-horizons invariant, а не
   только activation cross-reference.
3. `SemanticV2Service.build_v2_block` — paired function contract, включая
   exact-nine canon filtering и direct horizons/audit pass-through.
4. `TodayCacheKey.cache_key_hash`, `build_today_cache_key`,
   `expected_cache_identity` — paired contracts, описывающие content/frontend
   и nine-canon hash identity.
5. `get_canon_versions` — paired contract с exact nine-key result.
6. `apps/api/app/core/versions.py` — актуализировать existing module contract
   outputs/invariants и добавить небольшой `START_MODULE_MAP`, чтобы новые
   compatibility/content constants были частью архитектурного контракта.
7. `today_service.py` existing module contract/map — добавить horizon
   integration dependency, request-local reuse invariant и semantic block.

Не оборачивать contracts вокруг generated files и не проводить broad GRACE
cleanup legacy audit scripts.

## 9. Minor consistency cleanup

В defensive TodayService messages не писать, что current payload
`today.v2.1` «declares today.v2». Использовать fixed structural wording:

~~~text
current V2 payload identity requires v2 block
current frontend V2 identity requires v2 block
~~~

Не включать payload values, user/profile/date или exception text.

## 10. Allowed paths for R1

Production/docs metadata:

~~~text
apps/api/app/core/versions.py
apps/api/app/schemas/today.py
apps/api/app/services/cache_key_service.py
apps/api/app/services/canon_service.py
apps/api/app/services/semantic_v2_service.py
apps/api/app/services/today_service.py
~~~

Production integration service may change only if a new test exposes an actual
failure; otherwise leave it byte-identical:

~~~text
apps/api/app/services/today_horizon_integration_service.py
~~~

Tests:

~~~text
apps/api/tests/test_today_horizon_integration_service.py
apps/api/tests/test_today_horizons_contract.py
apps/api/tests/test_today_meta_versions.py
apps/api/tests/test_today_cache_v2_key.py
apps/api/tests/test_payload_v2_downstream_mapping.py
apps/api/tests/test_downstream_v2_audit.py
apps/api/tests/test_audit_today_modes.py
~~~

No generated wire shape change is expected. Therefore these files should stay
byte-identical after `pnpm contracts:sync`:

~~~text
packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
~~~

If generation changes any of them, stop and report the exact reason instead of
normalizing an unexpected contract drift.

Architect-owned document; coder must read but not edit:

~~~text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/79_STAGE_B3_W2_ARCH_REVIEW_R1_TZ.md
~~~

All current W2 allowlisted modifications remain in place. Preserve and never
stage unrelated paths:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

## 11. Mandatory gates after correction

Run the full `78 §17` gate matrix again, including:

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_horizon_integration_service.py \
  apps/api/tests/test_today_horizons_contract.py \
  apps/api/tests/test_today_meta_versions.py \
  apps/api/tests/test_today_cache_v2_key.py \
  apps/api/tests/test_horizon_canon_service.py \
  apps/api/tests/test_horizon_content_canon_service.py \
  apps/api/tests/test_payload_v2_downstream_mapping.py \
  apps/api/tests/test_downstream_v2_audit.py \
  apps/api/tests/test_audit_today_modes.py \
  apps/api/tests/test_day_endpoints.py -q
~~~

Also rerun:

- complete horizon regression from `78`;
- request reuse regression from `78`;
- `pnpm contracts:sync` and prove generated/fixture hashes unchanged;
- `pnpm contracts:fixture:check`;
- focused two-file contract Vitest;
- real compatibility checker with `breakingChanges=0` and
  `overrideUsed=false`;
- `npx tsc --noEmit`;
- Python compileall for changed backend modules;
- full API suite with only the exact six frozen W2 baseline failures;
- `git diff --check` including untracked files;
- exact changed-path allowlist and index-empty proof;
- local/origin HEAD still exact accepted W1 SHA.

Run targeted GRACE for the existing mandatory three files and additionally
prove via source assertions or focused lint output that every function named in
section 8 now contains a paired function contract. Do not claim the legacy
files are globally GRACE-clean when they still have unrelated baseline debt.

## 12. Forbidden actions

- no `git add`;
- no commit;
- no push;
- no branch switch;
- no B3.W3;
- no frontend/B4;
- no port 3003 changes;
- no main/deploy/systemd/nginx;
- no fixture/demo runtime path;
- no handwritten generated-contract edits;
- no broad formatting/refactor;
- no subagents/delegation.

## 13. Exact callback

~~~text
READY_STAGE_B3_W2_R1_REVIEW
accepted_w1_sha: ecae4d0ff95bf29953fbb6957e48c38a7d22e198 local/origin unchanged
canon_boundary: PASS exact 9; unknown dropped; horizon keys current; core overlay only
public_identity_matrix: PASS current/previous/mismatch/missing-audit
reason_parity: PASS internal minus selected equals public unavailable
cache_horizon_invalidation: PASS 4/4 keys alter both hashes
cache_invalid_current_rows: PASS miss without exception
mapping_failure_log: PASS exact sanitized event and pipeline calls=0
runtime_wiring_exact_reuse: PASS activation/scoring/natal/advice identities once
audit_identity_coverage: PASS current fresh + previous compatible
grace_changed_boundaries: PASS named contracts present
generated_contract_hashes: UNCHANGED
fixture_hash: UNCHANGED normalized
focused_backend: <count> PASS
horizon_regression: <count> PASS
request_reuse: <count> PASS
contract_vitest: <count> PASS
contract_compat: breakingChanges=0 overrideUsed=false
full_api: <passed> passed, <skipped> skipped, exact 6 frozen failures only
git_diff_check: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback.
