# Stage A1 Acceptance — shared activation models accepted

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Reviewed HEAD/origin: `524812fd9764770e247029651924a731addab4af`
Implementation TZ: `46_STAGE_A1_SHARED_MODELS_IMPLEMENTATION_TZ.md`
Статус: **ACCEPTED FOR SCOPED COMMIT/PUSH**.

## 1. Принятый результат

Stage A1 создаёт один канонический Python source для activation-layer
контракта:

```text
packages/py-contracts/solarsage_contracts
  -> sidecar facade: snake_case
  -> API facade: camelCase
  -> прежний public OpenAPI/TypeScript/Zod wire без изменений
```

Архитектурное review подтверждает:

- поля, их порядок, requiredness, defaults, factories и constraints определены
  только в shared package;
- `ActivationTargetType`, `ActivationPolarity` и `ActivationPhase` имеют один
  источник;
- index-reference validator находится только в shared layer model;
- API wrappers остаются subclasses `CamelModel` и shared contracts;
- nested API evidence имеет runtime type API wrapper;
- sidecar wrappers не имеют alias generator, принимают snake_case и отклоняют
  camel-only input;
- обе границы используют `extra="forbid"`;
- wire versions определены только в `solarsage_contracts.versions`, а API и
  sidecar сохраняют прежние локальные import surfaces через re-export;
- shared package не импортирует `app`, `apps` или `solarsage`;
- package установлен editable в оба существующих venv и разрешается из
  `packages/py-contracts/solarsage_contracts`;
- Stage A2 tooling/CI/Docker и Stage B product paths не затронуты.

## 2. Независимые architect gates

### 2.1 Shared package и boundary behavior

```text
API venv shared tests:     44 passed
sidecar venv shared tests: 44 passed
pip check API:             PASS
pip check sidecar:         PASS
API MRO/aliases/config:    PASS
sidecar snake/config:      PASS
AST thin-wrapper guards:   PASS
shared import scan:        PASS
```

Оба editable imports указывают на:

```text
/opt/solarsage-astro/packages/py-contracts/solarsage_contracts/__init__.py
```

### 2.2 Exact real-wire parity

Повторён representative Basil build из implementation TZ:

```text
activations: 144
activation layer: al-1.1
calculation: ss-calc-1.2.0

snake bytes: 150762
snake SHA-256:
3c9b7038d3c01972ceb418160c918d40d4fa14d3542864ffa881a700f4437a5d
snake byte-for-byte baseline equality: PASS

camel bytes: 149166
camel SHA-256:
0405c10915a8b327fc1d6dffc71963830132caeca61cb8c2bee5c7c49359267b
camel byte-for-byte baseline equality: PASS
```

### 2.3 Sidecar и API

```text
sidecar full: 201 passed, 1 warning
API full:     6 failed, 830 passed, 5 skipped, 1 warning
```

API failure set и traceback-причины совпадают с зафиксированным clean-base
baseline:

```text
test_calendar_status_cache_duplicate_rereads_winning_row
test_semantic_v2_service_no_convergence
test_semantic_v2_service_with_convergence
test_audit_canon_versions_only_contains_strings
test_techniques_list_is_sorted
test_today_payload_v2_block_included_when_flag_enabled
```

Для A1 принят differential gate `BASELINE_RED_IDENTICAL`. Перед release в
`main` эти шесть failures остаются обязательной отдельной stabilization wave;
финальный gate `all tests green` не ослабляется.

### 2.4 Generated contracts и static gates

```text
pnpm contracts:check: PASS
contract Vitest:      132 passed
TypeScript typecheck: PASS
compileall:           PASS
git diff --check:     PASS
trailing whitespace: no matches
index:                EMPTY
```

Generated artifacts byte-identical исходному состоянию:

```text
openapi.json:
bc4c9f93cee4c45e67cc568ea35c13716079ac818bbd2a558b1d23f7859e98ff

_generated.ts:
8027ad45c4077318b2c5eafc4b0f1ec1cb61fc9dd319cd106195a03a21d2163f

_generated.zod.ts:
bed54dd3c09adfe502538747a8c18fd8b059855a43a98783dd385755fb8b33f6
```

OpenAPI содержит только прежние public components `ActivationEvidence` и
`ActivationLayer`; shared/generic component names отсутствуют.

## 3. Review conclusions

Blocking findings не обнаружены. Multiple-inheritance boundary pattern
сохраняет прежний публичный контракт и одновременно устраняет дублирование
моделей и версий. Реальные payloads, generated contracts и validation behavior
не изменились.

## 4. Разрешение и ограничения следующего шага

Разрешён только scoped commit/push по
`48_STAGE_A1_COMMIT_PUSH_TZ.md`.

До завершения push запрещено:

- начинать Stage A2 или Stage B;
- исправлять baseline API failures;
- менять runtime/systemd/nginx/Docker/CI;
- включать unrelated untracked paths;
- делать merge/rebase/squash/amend/force-push.

Acceptance не является разрешением на merge в `main` или production deploy.

## 5. Unrelated paths вне commit

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```
