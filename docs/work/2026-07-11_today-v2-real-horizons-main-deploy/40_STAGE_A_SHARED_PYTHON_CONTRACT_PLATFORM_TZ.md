# Stage A ТЗ — Shared Python Contracts и быстрый contract workflow

Дата: 2026-07-11  
Репозиторий: `/opt/solarsage-astro`  
Целевая feature branch:
`preview/solarsage-v2-human-first-navigator-ux`  
Статус: **future implementation plan; не выполнять до явной команды
`START_STAGE_A_SHARED_CONTRACTS`**.

## 0. Место этой стадии в программе

Эта стадия вставляется после полной приёмки, commit и push S2.W1 real timing и
до добавления публичного backend-owned горизонта.

Последовательность:

```text
S2.W1 real timing accepted and pushed
  -> Stage A shared Python contracts
  -> Stage B real horizons/actions/frontend
  -> final main integration and production deploy
```

Этот файл уточняет архитектурные разделы прежних:

```text
00_MASTER_TZ.md
10_STAGE_1_CONTRACT_FOUNDATION_TZ.md
20_STAGE_2_REAL_HORIZONS_TZ.md
```

Уже завершённые S1 codegen/runtime/fixture решения не откатывать. Новое правило:

```text
one source of truth per network boundary
```

а не один универсальный DTO для всего приложения.

## 1. Результат стадии

Стадия принята только когда одновременно доказано:

1. Поля, enums, defaults и index validation `ActivationEvidence` /
   `ActivationLayer` определены один раз в отдельном Python package.
2. Sidecar и API используют shared definitions через тонкие boundary wrappers,
   а не копируют contract fields.
3. Sidecar JSON casing остаётся текущим snake_case; публичный API/frontend wire
   остаётся camelCase.
4. Existing payload до и после migration byte-identical на каждой границе.
5. `activation-layer.v1`, `al-1.1`, `ss-calc-1.2.0` не меняются только из-за
   refactor.
6. Один command генерирует и проверяет OpenAPI, TypeScript, Zod, compatibility и
   focused contract tests.
7. CI устанавливает один и тот же shared package перед API/sidecar tests.
8. Docker build имеет доступ к shared package через repo-root context.
9. Production systemd units, canonical ports и nginx не требуют изменения.
10. AST/drift tests физически запрещают повторное ручное объявление contract
    fields в API или sidecar wrappers.

## 2. Не цели

В этой стадии запрещено:

- добавлять `TodayV2.horizons`;
- генерировать пользовательские действия/тексты;
- менять ranking/scoring/astrology calculation;
- менять frontend rendering/copy;
- удалять dev fixture;
- включать новые feature flags;
- менять production env;
- merge в `main` или production deploy;
- переходить на spec-first OpenAPI как source;
- добавлять Proto/GraphQL/Avro/Buf;
- заменять Pydantic/OpenAPI/TypeScript/Zod pipeline;
- использовать `dict[str, Any]` как shortcut для нового product contract.

## 3. Текущее состояние и проблема

### Уже правильно

Публичная граница API -> browser уже работает по pipeline:

```text
apps/api/app/schemas/* Pydantic
  -> scripts/contracts/export_openapi.py
  -> packages/contracts/openapi.json
  -> packages/contracts/_generated.ts
  -> packages/contracts/_generated.zod.ts
  -> frontend validation/rendering
```

Generated artifacts не редактируются вручную.

### Дублирование, которое надо убрать

Один смысл ActivationLayer сейчас объявлен независимо в:

```text
apps/solarsage/solarsage/schemas/activation.py
apps/api/app/schemas/activation.py
```

Это создаёт риск расходящихся:

- полей;
- optional/required semantics;
- enum values;
- defaults;
- validators;
- version literals.

Также root schema registry использует string names, а developer workflow
разделён между несколькими командами без compatibility classification.

## 4. Целевая архитектура

```text
packages/py-contracts/solarsage_contracts
  ActivationEvidenceContract
  ActivationLayerContract[EvidenceT]
  enums + shared validators + shared contract versions
        │
        ├── sidecar thin wrapper
        │      Python snake_case + sidecar JSON snake_case
        │
        └── API thin wrapper
               Python snake_case + public JSON camelCase
                         │
                         v
                 API public Today schemas
                         │
                         v
                 OpenAPI -> TS + Zod
```

### Boundary ownership

1. `solarsage_contracts` владеет только calculation evidence wire semantics.
2. Sidecar владеет calculation/domain implementation.
3. API владеет публичными Today read models и human guidance.
4. Frontend владеет presentation, accessibility и interaction, но не
   астрологическими выводами.

Shared package не импортирует ничего из `apps/api` или `apps/solarsage`.

## 5. Package layout

Создать:

```text
packages/py-contracts/
  pyproject.toml
  README.md
  solarsage_contracts/
    __init__.py
    py.typed
    base.py
    activation.py
    versions.py
  tests/
    test_activation_contract.py
    test_boundary_configs.py
    test_versions.py
```

Package metadata:

```text
distribution: solarsage-contracts
import: solarsage_contracts
initial package version: 0.1.0
requires-python: >=3.11
dependency: pydantic >=2.9,<3
build backend: setuptools
```

Package version является версией библиотеки, не public wire version.

Все новые source/test files получают полноценные GRACE headers, module
contracts/maps и function contracts для нетривиальной validation logic.

## 6. Shared model design

### 6.1 Shared base

В `base.py`:

```py
class StrictContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        frozen=False,
    )
```

В shared base намеренно нет `alias_generator`. JSON casing является свойством
конкретной boundary, а не semantic field definition.

### 6.2 Activation enums/types

В `activation.py` перенести без изменения values:

```py
ActivationTargetType
ActivationPolarity
ActivationPhase
```

Enums/Literals определяются один раз и re-export через package root.

### 6.3 Evidence definition

Определить один canonical class:

```py
class ActivationEvidenceContract(StrictContractModel):
    # current complete field set, including timing/debug
```

Все поля, constraints и defaults берутся из принятого S2.W1 результата.
Нельзя менять requiredness, field order или semantics во время переноса.

### 6.4 Generic layer definition

Чтобы nested evidence boundary config не терялся:

```py
EvidenceT = TypeVar("EvidenceT", bound=ActivationEvidenceContract)

class ActivationLayerContract(
    StrictContractModel,
    Generic[EvidenceT],
):
    schema_version: str = ACTIVATION_SCHEMA_VERSION
    activation_layer_version: str = ACTIVATION_LAYER_VERSION
    calculation_version: str
    target_date: str
    target_time: str
    target_tz: str
    house_system: str
    activations: list[EvidenceT]
    by_planet: dict[str, list[str]]
    by_house: dict[str, list[str]]
    by_lot: dict[str, list[str]]
    by_angle: dict[str, list[str]]
    warnings: list[str] = Field(default_factory=list)
```

Existing index-reference validator переносится сюда один раз.

### 6.5 API thin wrappers

`apps/api/app/schemas/activation.py` после migration содержит только imports,
docs и boundary config:

```py
class ActivationEvidence(ActivationEvidenceContract):
    model_config = CamelModel.model_config


class ActivationLayer(ActivationLayerContract[ActivationEvidence]):
    model_config = CamelModel.model_config
```

Нельзя повторять annotations/defaults/validator.

API proofs:

- Python accepts snake_case and camelCase input;
- `model_dump(by_alias=True)` uses camelCase recursively;
- generated OpenAPI schema names остаются `ActivationEvidence` и
  `ActivationLayer`, не generic implementation names;
- nested activation type в OpenAPI ссылается на public wrapper.

Если Pydantic generic specialization даёт нестабильное schema name, coder не
должен придумывать dynamic factory. Остановиться с exact generated fragment;
архитектор выберет тонкую typed alternative.

### 6.6 Sidecar thin wrappers

`apps/solarsage/solarsage/schemas/activation.py`:

```py
class ActivationEvidence(ActivationEvidenceContract):
    pass


class ActivationLayer(ActivationLayerContract[ActivationEvidence]):
    pass
```

Sidecar response должен оставаться snake_case byte-for-byte. Не добавлять
camel aliases в sidecar wrapper и не менять endpoint outer envelope.

## 7. Version ownership

`packages/py-contracts/solarsage_contracts/versions.py` становится единственным
источником для shared boundary identity:

```py
ACTIVATION_SCHEMA_VERSION = "activation-layer.v1"
ACTIVATION_LAYER_VERSION = "al-1.1"
CALCULATION_VERSION = "ss-calc-1.2.0"
```

Existing modules:

```text
apps/api/app/core/versions.py
apps/solarsage/solarsage/core/versions.py
```

re-export shared constants под прежними import names. App-specific versions
(`SCORING_V2_VERSION`, content/prompt/payload versions) остаются у владельца.

Нельзя держать fallback literal в wrappers/endpoints. Defaults импортируют
shared constants.

### Version rule

Эта migration не меняет:

```text
schema_version
activation_layer_version
calculation_version
scoring_version
content_version
```

Любой diff version value — blocking regression.

## 8. Import migration

### 8.1 Preserve public imports

Существующие consumers продолжают импортировать:

```py
from app.schemas.activation import ...
from solarsage.schemas.activation import ...
```

Не выполнять repository-wide import churn. Boundary modules остаются stable
facades.

### 8.2 Forbidden imports

Tests/guards должны запрещать:

- sidecar import из `apps.api`/`app.schemas`;
- API import из `apps.solarsage`;
- shared package import из обоих apps;
- frontend import Python/shared runtime;
- direct frontend import generated internals вне approved barrels.

## 9. Python dependency and installation contract

### 9.1 App metadata

В оба `pyproject.toml` добавить dependency:

```text
solarsage-contracts==0.1.0
```

Package не публикуется в PyPI. Любая environment setup сначала устанавливает
локальный shared package, затем app package.

### 9.2 Local development

Canonical setup commands:

```bash
apps/api/.venv/bin/python -m pip install -e ./packages/py-contracts
apps/solarsage/venv/bin/python -m pip install -e ./packages/py-contracts
```

После install:

```bash
apps/api/.venv/bin/python -m pip check
apps/solarsage/venv/bin/python -m pip check
```

Не использовать global pip и не изменять `/opt/astro-project`.

### 9.3 Production release

Финальный release строит один wheel и устанавливает тот же artifact в оба venv:

```bash
python -m pip wheel --no-deps ./packages/py-contracts -w <release-temp>
apps/api/.venv/bin/python -m pip install --force-reinstall <same-wheel>
apps/solarsage/venv/bin/python -m pip install --force-reinstall <same-wheel>
```

Wheel hash записывается в release report. Не печатать environment secrets.

Stage A только доказывает команды; production venv installation выполняется в
финальной release wave, не сейчас.

## 10. Docker compatibility

Текущие Docker build contexts `apps/api` / `apps/solarsage` не видят
`packages/py-contracts`. Обновить оба compose manifests так, чтобы context был
repo root, а Dockerfile path оставался explicit.

Принцип:

```yaml
build:
  context: .
  dockerfile: apps/api/Dockerfile
```

и аналогично для sidecar.

Dockerfiles:

- использовать Python 3.12, соответствующий production venv и API metadata;
- copy shared package;
- install shared package;
- copy/install соответствующее приложение;
- sidecar entrypoint `solarsage.app:app`, не несуществующий
  `solarsage.main:app`;
- не добавлять secrets в image;
- не менять canonical host/systemd ports;
- `.dockerignore` обязан исключать venv, `.next*`, artifacts, `.env*`, git,
  caches и secrets.

Stage gate минимум:

```bash
docker compose config
docker compose -f docker-compose.prod.yml config
docker build -f apps/api/Dockerfile -t solarsage-api-contract-proof .
docker build -f apps/solarsage/Dockerfile -t solarsage-sidecar-contract-proof .
```

Не запускать эти images на production ports.

## 11. Explicit public schema registry

Убрать string-name registry из `scripts/contracts/export_openapi.py`.

Создать API-owned:

```text
apps/api/app/schemas/contract_registry.py
```

с explicit class objects:

```py
PUBLIC_CONTRACT_ROOTS: tuple[type[CamelModel], ...] = (
    AccessSummary,
    ActivationLayer,
    ...,
    TodayPayload,
)
```

`export_openapi.py` импортирует tuple и валидирует:

- unique class names;
- every root is a `CamelModel` subclass;
- deterministic order;
- no shared implementation/base class exposed as root;
- no duplicate schema title;
- expected public roots присутствуют.

Nested horizon models Stage B попадут в OpenAPI автоматически через
`TodayPayload`; их не нужно добавлять как roots без отдельного endpoint.

## 12. Fast developer workflow

### 12.1 Commands

Добавить package scripts:

```json
{
  "contracts:generate": "existing deterministic generation",
  "contracts:compat": "python scripts/contracts/check_compat.py",
  "contracts:sync": "bash scripts/contracts/sync.sh",
  "contracts:check": "existing CI drift check extended with new guards"
}
```

### 12.2 `contracts:sync`

Intentional developer update command выполняет:

```text
1. shared Python contract tests
2. OpenAPI export
3. TypeScript generation
4. Zod generation
5. compatibility classification against base ref
6. runtime contract Vitest
7. TypeScript compile of contract consumers
8. concise changed-contract report
```

Он не требует clean generated diff, потому что используется для intentional
change. Он обязан быть deterministic и не stage/commit files.

Supported environment:

```text
CONTRACT_BASE_REF defaults to merge-base with origin/main
```

Если ref недоступен, command падает с инструкцией, а не silently skips compat.

### 12.3 `contracts:check`

CI/drift command:

```text
generate
run fixture normalization check
run shared-source guards
git diff --exit-code generated artifacts
```

Не сравнивать весь dirty worktree; diff only owned generated files.

## 13. Compatibility checker

Создать:

```text
scripts/contracts/check_compat.py
scripts/contracts/test_check_compat.py
```

Он читает current `openapi.json` и base artifact через:

```bash
git show <base-ref>:packages/contracts/openapi.json
```

Не писать base artifact в repository.

### 13.1 Additive compatible

Классифицировать compatible:

- новое optional property;
- новый schema component, пока существующие roots не ссылаются на него как
  required;
- enum widening;
- новый optional endpoint response block;
- новое optional discriminator variant при tolerant consumer contract.

### 13.2 Breaking

Fail без explicit reviewed override:

- удалён property/schema/endpoint;
- optional -> required;
- добавлен required property;
- изменён primitive/container type;
- enum narrowing/removal;
- changed discriminator mapping;
- changed nullability;
- changed numeric/string constraint that rejects old valid payload;
- changed alias/wire property name;
- `additionalProperties` стал строже;
- changed documented semantic version without matching version discipline.

### 13.3 Output

Machine-readable JSON и concise stdout:

```text
classification: no-change | additive | breaking
changed schemas
added optional fields
breaking paths/reasons
required action
```

Override, если вообще нужен, требует:

```text
--allow-breaking
CONTRACT_BREAKING_REASON=<non-empty>
```

CI main/PR не использует override автоматически.

## 14. Single-source guards

Добавить Python tests, которые:

1. Сравнивают API/sidecar/shared field names, order, requiredness и defaults.
2. Проверяют API camel aliases.
3. Проверяют sidecar snake serialization.
4. Проверяют identical index validator behavior.
5. AST-проверкой запрещают field annotations в thin wrapper classes.
6. Запрещают local definitions shared enum names вне package/wrappers.
7. Проверяют version constants identity.
8. Проверяют `packages/py-contracts` не импортирует app code.

Guard не должен зависеть от строк docstring/comments.

## 15. Wire parity fixtures

Сохранить два canonical test artifacts только в test tree:

```text
packages/py-contracts/tests/fixtures/activation-layer-snake.json
apps/api/tests/fixtures/contracts/activation-layer-public-camel.json
```

Они представляют один semantic object на двух boundary casings.

Proof chain:

```text
sidecar wrapper validates snake fixture
  -> semantic model dump
  -> API wrapper validates same Python values
  -> public camel fixture byte match
  -> generated Zod validates public representation
```

Fixtures не импортируются production runtime.

## 16. CI changes

Обновить `.github/workflows/ci.yml`:

### Shared package

- Python 3.12 для API/contract jobs;
- install `./packages/py-contracts` first;
- run its tests.

### Sidecar job

Добавить отсутствующий sidecar test job:

```bash
python -m pip install -e ./packages/py-contracts
python -m pip install -e ./apps/solarsage
python -m pytest apps/solarsage/tests -q
```

### API job

```bash
python -m pip install -e ./packages/py-contracts
python -m pip install -e ./apps/api
python -m pytest apps/api/tests -q
```

### Contract job

Запускает shared tests, generation/drift, compat checker unit tests, existing
Vitest contract suites и typecheck.

Не публиковать wheel/package наружу.

## 17. Observability and security

Migration не добавляет бизнес-логи. Contract tooling выводит только:

- schema names;
- property paths;
- classification;
- versions;
- artifact hashes.

Запрещено выводить fixture values, если они могут содержать user data. Test
fixtures используют synthetic/Basil audit data без auth tokens/profile IDs.

## 18. Волны выполнения

## A1 — Shared package and thin wrappers

### Scope

- создать package;
- перенести field definitions/validator/version constants;
- создать API/sidecar thin wrappers;
- сохранить old imports;
- установить package в local venv;
- focused parity/AST tests;
- no Docker/CI/tooling changes ещё.

### Gates

```bash
apps/api/.venv/bin/python -m pip install -e ./packages/py-contracts
apps/solarsage/venv/bin/python -m pip install -e ./packages/py-contracts
apps/api/.venv/bin/python -m pytest packages/py-contracts/tests -q
cd apps/solarsage && venv/bin/python -m pytest tests -q
cd apps/api && .venv/bin/python -m pytest tests -q
pnpm contracts:generate
pnpm contracts:check
git diff --check
```

Generated OpenAPI/TS/Zod должны быть byte-identical S2.W1 accepted baseline.

### Callback

```text
READY_STAGE_A1_SHARED_MODELS
shared_fields_single_source: PASS
api_camel: PASS
sidecar_snake: PASS
wire_parity: PASS
versions_unchanged: PASS
sidecar_full: <result>
api_full: <result>
generated_diff: ZERO
commit: NOT_YET
push: NOT_YET
```

## A2 — Sync/compat/CI/Docker

### Scope

- explicit class registry;
- `contracts:sync`;
- compatibility checker + unit tests;
- CI installs/tests shared package and sidecar;
- Docker root contexts/package install/entrypoint correction;
- documentation.

### Gates

```bash
pnpm contracts:sync
pnpm contracts:check
apps/api/.venv/bin/python -m pytest scripts/contracts/test_check_compat.py -q
npx vitest run __tests__/contracts
npx tsc --noEmit
docker compose config
docker compose -f docker-compose.prod.yml config
docker build -f apps/api/Dockerfile -t solarsage-api-contract-proof .
docker build -f apps/solarsage/Dockerfile -t solarsage-sidecar-contract-proof .
git diff --check
```

Добавить compatibility unit cases минимум:

- optional add -> additive;
- required add -> breaking;
- property removal -> breaking;
- enum widen -> additive;
- enum narrow -> breaking;
- nullability narrowing -> breaking;
- alias rename -> breaking;
- no change -> no-change.

### Callback

```text
READY_STAGE_A2_CONTRACT_AUTOMATION
sync: PASS
compat_matrix: PASS
registry: PASS
ci_definition: PASS
docker_api_build: PASS
docker_sidecar_build: PASS
systemd_changes: NONE
commit: NOT_YET
push: NOT_YET
```

## A3 — Full proof and accepted checkpoint

### Scope

- устранить review findings A1/A2;
- full repository contract/backend/frontend regression;
- prove no product behavior change;
- prepare scoped commit sequence only after architect acceptance.

### Gates

```bash
pnpm install --frozen-lockfile
pnpm contracts:sync
pnpm contracts:check
npx vitest run
npx tsc --noEmit
(
  cd apps/solarsage
  venv/bin/python -m pytest tests -q
)
(
  cd apps/api
  .venv/bin/python -m pytest tests -q
)
NEXT_DIST_DIR=.next-stage-a-proof pnpm build
git diff --check
git status --short
git diff --cached --stat
```

После build удалить только owned `.next-stage-a-proof`; восстановить generated
Next config noise byte-for-byte без destructive checkout.

### Required parity evidence

- representative sidecar response before/after semantic/casing comparison;
- representative public API Today payload before/after byte comparison;
- OpenAPI/TS/Zod zero semantic diff;
- shared wheel builds;
- import smoke in both venvs;
- package/version location via `module.__file__` points to expected installed
  package, без вывода environment secrets.

### Callback

```text
READY_STAGE_A_SHARED_CONTRACTS
branch: <branch>
head: <sha>
shared_package: solarsage-contracts 0.1.0
wire_sidecar_unchanged: PASS
wire_api_unchanged: PASS
versions_unchanged: PASS
single_source_guards: PASS
contracts_sync: PASS
compat: PASS
sidecar_full: <result>
api_full: <result>
frontend_full: <result>
build: PASS
docker_builds: PASS
index: EMPTY
commit: NOT_YET
push: NOT_YET
```

## 19. Commit discipline

Coder не делает commit/push до architect acceptance каждой волны.

Предпочтительная sequence после acceptance:

```text
refactor(contracts): share activation models across python services
chore(contracts): add sync compatibility and packaging gates
```

Не squash без команды архитектора: отдельные commits упрощают rollback и blame.

## 20. Definition of done

Stage A не считается завершённой по наличию package directory или зелёному
focused test. Требуется доказать весь путь:

```text
canonical shared field definition
  -> sidecar snake wire unchanged
  -> API validation/public camel wire unchanged
  -> generated OpenAPI/TS/Zod unchanged
  -> one-command sync/compat
  -> local venv/CI/Docker installation
  -> full backend/frontend regressions green
  -> accepted commits pushed to feature branch
```

После Stage A остановиться и ждать отдельной команды на Stage B. Не начинать
horizon/product implementation самостоятельно.
