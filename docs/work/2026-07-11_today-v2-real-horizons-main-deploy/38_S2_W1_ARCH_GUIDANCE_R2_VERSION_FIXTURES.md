# S2.W1 Architecture Guidance R2 — classify version tests, preserve old fixtures

Дата: 2026-07-11  
Статус: обязательное дополнение к `36_*` после первого API suite run.

## Правило

Обновлять literal до `al-1.1` / `ss-calc-1.2.0` только если test проверяет:

- schema default;
- current local fallback, построенный canonical service;
- current live runtime identity;
- current expected cache identity;
- sidecar endpoint этой ветки.

Не обновлять explicit old input fixture, если test проверяет backward
compatibility или поведение, не связанное с текущей версией.

## Точные failing-test решения

### Обновить до текущих versions

1. `test_activation_contracts.py::test_activation_layer_minimal`
   - это schema default;
   - expected `al-1.1`.
2. `test_activation_layer_contract.py::test_activation_layer_service_builds_minimal`
   - local fallback использует canonical constants;
   - expected `al-1.1`.
3. `test_activation_layer_contract.py::test_activation_layer_service_accepts_sidecar_layer`
   - input создаётся в этом же test через current local `built.model_dump()`;
   - expected `al-1.1`.
4. `test_today_cache_v2_key.py::test_expected_cache_identity_has_non_none_al_version`
   - current expected identity;
   - expected `al-1.1`.
5. `test_today_meta_versions.py::test_activation_layer_version_is_al_1_0_in_live_payload`
   - переименовать test/docstring на `al_1_1`;
   - expected `al-1.1`.
6. `test_today_meta_versions.py::test_today_service_fresh_payload_activation_layer_wiring`
   - этот flow строит current local layer;
   - captured layer и payload meta expected `al-1.1`;
   - scoring V1 assertions не менять.

### Не менять старые explicit fixture literals

1. `test_today_v2_payload.py::test_today_payload_v2_block_included_when_flag_enabled`
   содержит явный mocked sidecar response:

   ```text
   activation_layer_version = al-1.0
   calculation_version = 1
   ```

   Этот test проверяет наличие V2 payload block, а не current sidecar identity.
   Старый input обязан оставаться валидным. Если test падает, исследовать реальную
   причину; не «лечить» заменой fixture version.
2. Аналогичный explicit old mock в disabled/V1 test оставить старым.
3. Cache-key tests, которые специально сравнивают `None`, `al-1.0`, `al-2.0`,
   оставить без изменений: они доказывают, что разные version strings меняют hash.
4. Existing W3.1/W3.2/W3.3/W3.4 API fixtures с explicit `al-1.0` оставить как
   compatibility inputs, если test не моделирует новый live sidecar.
5. Audit/downstream golden JSON не переписывать массово.

## Новый timing parity proof

Создать отдельный explicit `al-1.1` / `ss-calc-1.2.0` timed sidecar dict с:

```text
id
active_from
exact_at
active_until
```

и проверить byte-for-byte preservation через `ActivationLayerService.build`.
Не превращать старый compatibility fixture в новый только ради этого proof.

## Generated defaults

OpenAPI/generated TS/Zod default должен стать `al-1.1`; это не означает, что
runtime validator должен отвергать explicit `al-1.0` string.

После применения продолжить полный API suite и основной callback. Commit/push
по-прежнему запрещены.
