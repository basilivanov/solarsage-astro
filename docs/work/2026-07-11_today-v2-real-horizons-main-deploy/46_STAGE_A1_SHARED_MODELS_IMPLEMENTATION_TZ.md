# Stage A1 Implementation TZ — shared activation models and thin boundaries

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Expected base HEAD/origin:
`524812fd9764770e247029651924a731addab4af`
Parent architecture: `40_STAGE_A_SHARED_PYTHON_CONTRACT_PLATFORM_TZ.md`
Статус: **START_STAGE_A_SHARED_CONTRACTS / implement A1 only**.

## 0. Режим работы

1. Полностью прочитать этот файл и `40_STAGE_A_SHARED_PYTHON_CONTRACT_PLATFORM_TZ.md`.
2. Работать только в текущей preview branch.
3. Не запускать субагентов, delegated agents или параллельных coding agents.
4. Product implementation выполняет coder; architect после callback независимо
   читает diff и запускает gates.
5. Запрещены до отдельной acceptance-команды:
   - `git add`;
   - `git commit`;
   - `git push`;
   - merge/rebase/cherry-pick/reset/checkout/switch;
   - изменение `main`;
   - systemd/nginx/Docker restart;
   - ручной `uvicorn`;
   - работа на production ports;
   - Stage A2 tooling/CI/Docker;
   - Stage B horizons/actions/frontend.
6. Не трогать unrelated paths:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

7. Existing services на `8000`, `18091`, `3003` не перезапускать и не
   использовать как замену test gates.
8. Если generic wrapper меняет OpenAPI, schema names или wire — остановиться с
   exact fragment. Не править generated artifacts вручную.

## 1. Результат волны

После A1 должно быть истинно:

```text
one canonical Python field definition
  -> sidecar thin wrapper, snake_case wire
  -> API thin wrapper, camelCase public wire
  -> current OpenAPI/TS/Zod byte-identical
```

В этой волне:

- создаётся локальный distribution `solarsage-contracts==0.1.0`;
- поля, Literals, defaults, constraints и index validator определяются один раз;
- API/sidecar import facades сохраняются;
- shared versions становятся единственным product-code source;
- package устанавливается editable в оба existing venv;
- добавляются parity, MRO, AST и fixture guards;
- public/runtime поведение не меняется.

Не добавлять contract sync/compat registry, CI или Docker. Это A2.

## 2. Preflight и baseline evidence до первого edit

Выполнить:

```bash
git branch --show-current
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git status --short
git diff --cached --name-only
pnpm contracts:check
```

Ожидание:

- branch совпадает;
- HEAD и origin равны `524812f...`;
- tracked worktree clean;
- index empty;
- присутствуют только перечисленные unrelated untracked paths.

Зафиксировать baseline hashes:

```bash
sha256sum \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts
```

Ожидаемые значения:

```text
bc4c9f93cee4c45e67cc568ea35c13716079ac818bbd2a558b1d23f7859e98ff  packages/contracts/openapi.json
8027ad45c4077318b2c5eafc4b0f1ec1cb61fc9dd319cd106195a03a21d2163f  packages/contracts/_generated.ts
bed54dd3c09adfe502538747a8c18fd8b059855a43a98783dd385755fb8b33f6  packages/contracts/_generated.zod.ts
```

До edits получить canonical real-wire hashes representative Basil build:

```text
birth: 1980-10-30 19:50 Europe/Moscow
lat/lon: 67.9394 / 32.8144
target: 2026-07-08 12:00 Europe/Moscow
house system: PLACIDUS
techniques: default/all
serialization: json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
```

Expected:

```text
sidecar snake bytes: 150762
sidecar snake sha256: 3c9b7038d3c01972ceb418160c918d40d4fa14d3542864ffa881a700f4437a5d

API camel bytes: 149166
API camel sha256: 0405c10915a8b327fc1d6dffc71963830132caeca61cb8c2bee5c7c49359267b

activations: 144
activation_layer_version: al-1.1
calculation_version: ss-calc-1.2.0
```

Сохранить baseline canonical JSON только в `/tmp/stage-a1-*`; не добавлять
real full response в repository.

## 3. Exact product/test allowlist

Разрешены:

```text
packages/py-contracts/**                                      # new package/tests/fixtures
apps/api/app/schemas/activation.py
apps/api/app/core/versions.py
apps/api/pyproject.toml
apps/api/tests/test_today_meta_versions.py
apps/api/tests/fixtures/contracts/activation-layer-public-camel.json
apps/solarsage/solarsage/schemas/activation.py
apps/solarsage/solarsage/core/versions.py
apps/solarsage/solarsage/api/activation_layer.py
apps/solarsage/pyproject.toml
apps/solarsage/tests/test_activation_schema.py
apps/solarsage/tests/test_activation_layer_endpoint.py
__tests__/contracts/activation-shared-parity.test.ts
```

Не обязательно менять каждый existing test path. Не расширять allowlist без
остановки и exact reason.

Generated files разрешено только перегенерировать для proof, но итоговый diff
обязан быть zero:

```text
packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
```

## 4. Shared package layout и metadata

Создать ровно:

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
    fixtures/
      activation-layer-snake.json
    test_activation_contract.py
    test_boundary_configs.py
    test_versions.py
```

`pyproject.toml` contract:

```toml
[project]
name = "solarsage-contracts"
version = "0.1.0"
description = "Shared Python wire contracts for SolarSage services"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.9,<3",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["solarsage_contracts*"]

[tool.setuptools.package-data]
solarsage_contracts = ["py.typed"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Не добавлять runtime dependencies кроме Pydantic.

`README.md` кратко фиксирует:

- package не публикуется в PyPI;
- package владеет calculation-evidence semantics;
- casing принадлежит boundary wrappers;
- local editable install commands;
- wire versions не равны package version.

`py.typed` остаётся пустым marker file.

Все новые `.py` files получают полный GRACE header/module contract/map.
Нетривиальный validator получает function contract и semantic block.

## 5. Shared base

`packages/py-contracts/solarsage_contracts/base.py`:

```py
from pydantic import BaseModel, ConfigDict


class StrictContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=False,
        frozen=False,
    )
```

Инварианты:

- никакого `alias_generator`;
- никакой зависимости от API `CamelModel`;
- unknown fields rejected;
- ordinary Pydantic coercion semantics сохраняются;
- model mutable, как сейчас.

## 6. Shared versions

`solarsage_contracts/versions.py` — единственный product-code literal source:

```py
ACTIVATION_SCHEMA_VERSION = "activation-layer.v1"
ACTIVATION_LAYER_VERSION = "al-1.1"
CALCULATION_VERSION = "ss-calc-1.2.0"
```

Добавить explicit `__all__`.

Запрещено менять values или добавлять package version в wire payload.

## 7. Canonical activation contract

`solarsage_contracts/activation.py` импортирует:

```py
from typing import Any, Generic, Literal, TypeVar
from pydantic import Field, model_validator
```

Определить один раз:

```py
ActivationTargetType = Literal["planet", "house", "lot", "angle", "sphere"]
ActivationPolarity = Literal["supportive", "tense", "mixed", "neutral"]
ActivationPhase = Literal[
    "applying",
    "exact",
    "separating",
    "background",
    "period",
]
```

### 7.1 Exact evidence fields и порядок

```py
class ActivationEvidenceContract(StrictContractModel):
    id: str
    technique: str
    technique_family: str
    target_type: ActivationTargetType
    target_key: str
    kind: str
    active: bool = True
    source_planet: str | None = None
    source_frame: str | None = None
    target_planet: str | None = None
    target_frame: str | None = None
    aspect: str | None = None
    orb: float | None = None
    applying: bool | None = None
    active_from: str | None = None
    exact_at: str | None = None
    active_until: str | None = None
    phase: ActivationPhase = "background"
    house: int | None = None
    lot: str | None = None
    angle: str | None = None
    strength: float = Field(ge=0.0, le=1.0)
    polarity: ActivationPolarity = "neutral"
    weight_hint: float | None = None
    evidence: str
    debug: dict[str, Any] = Field(default_factory=dict)
```

Не менять annotations, order, requiredness, default factories или constraints.

### 7.2 Exact layer fields и validator

```py
EvidenceT = TypeVar("EvidenceT", bound=ActivationEvidenceContract)


class ActivationLayerContract(StrictContractModel, Generic[EvidenceT]):
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

Перенести existing index-reference validator без изменения message semantics:

```text
{map_name}[{key}] references '{ref_id}' which is not present in activations
```

Validator один — только в shared class. API/sidecar wrappers не объявляют
validators.

## 8. Package root exports

`solarsage_contracts/__init__.py` re-export:

```text
StrictContractModel
ActivationTargetType
ActivationPolarity
ActivationPhase
ActivationEvidenceContract
ActivationLayerContract
ACTIVATION_SCHEMA_VERSION
ACTIVATION_LAYER_VERSION
CALCULATION_VERSION
```

Добавить explicit `__all__`. Package root не импортирует apps.

## 9. API thin boundary — обязательный MRO amendment

Текущий `scripts/contracts/export_openapi.py` до A2 принимает только
`CamelModel` subclasses. Простое назначение `model_config` недостаточно:
`issubclass(ActivationLayer, CamelModel)` стало бы false и generation сломался.

Поэтому A1 API wrappers должны быть именно multiple-inheritance facades, shared
base первым, `CamelModel` последним:

```py
class ActivationEvidence(ActivationEvidenceContract, CamelModel):
    """Single activation evidence entry for a transit/technique interaction."""


class ActivationLayer(
    ActivationLayerContract[ActivationEvidence],
    CamelModel,
):
    """Full activation layer output for a given target date."""
```

Почему порядок обязателен:

- shared field definitions приходят из первого base;
- `CamelModel` остаётся в MRO для current registry;
- Pydantic merge config получает API alias generator;
- wrapper names остаются public schema names;
- nested `activations` используют public `ActivationEvidence` wrapper.

В `apps/api/app/schemas/activation.py` разрешены только:

- GRACE/docs;
- imports shared types/contracts;
- import `CamelModel`;
- две wrapper class declarations и их exact existing docstrings;
- re-export imported Literal aliases.

Запрещены:

- field annotations;
- defaults;
- validators;
- version literals;
- dynamic model factories;
- `create_model`;
- manual `__name__`/schema-title mutation.

Mandatory proofs:

```py
issubclass(ActivationEvidence, CamelModel)
issubclass(ActivationLayer, CamelModel)
issubclass(ActivationEvidence, ActivationEvidenceContract)
issubclass(ActivationLayer, ActivationLayerContract)
type(layer.activations[0]) is ActivationEvidence
```

API must accept both snake and camel input and recursively dump camel aliases.

## 10. Sidecar thin boundary

`apps/solarsage/solarsage/schemas/activation.py`:

```py
class ActivationEvidence(ActivationEvidenceContract):
    """Single activation evidence entry (sidecar calculation output)."""


class ActivationLayer(ActivationLayerContract[ActivationEvidence]):
    """Full activation layer output from sidecar."""
```

Файл содержит только facade imports/docs/classes/re-export aliases.

Sidecar requirements:

- `model_dump(mode="json")` использует snake_case;
- camel-only keys rejected;
- unknown fields rejected;
- endpoint outer envelope не меняется;
- nested evidence type — sidecar wrapper;
- no API import.

## 11. Version re-exports and endpoint default

### API core

`apps/api/app/core/versions.py`:

```py
from solarsage_contracts.versions import (
    ACTIVATION_LAYER_VERSION,
    CALCULATION_VERSION,
)
```

Остальные API-owned constants остаются на месте. Удалить только два duplicated
literals. Обновить module contract dependencies/ownership.

### Sidecar core

`apps/solarsage/solarsage/core/versions.py` re-export тех же constants. В файле
не остаётся `al-1.1`/`ss-calc-1.2.0` literal.

### Sidecar endpoint

`apps/solarsage/solarsage/api/activation_layer.py` импортирует
`ACTIVATION_LAYER_VERSION` из sidecar core и использует:

```py
activation_layer_version: str = ACTIVATION_LAYER_VERSION
```

Не импортировать shared package напрямую во все consumers. Existing core facade
остаётся stable local import surface.

После migration product-code search:

```bash
rg -n 'activation-layer\.v1|al-1\.1|ss-calc-1\.2\.0' \
  apps/api/app apps/solarsage/solarsage --glob '*.py'
```

Ожидание: wire literals отсутствуют в apps; они существуют только в shared
`versions.py`. Tests/docs могут содержать expected literals.

## 12. App dependency metadata and editable install

В оба app `pyproject.toml` добавить:

```text
solarsage-contracts==0.1.0
```

Не менять другие pins/backends/metadata в A1.

Install после создания package:

```bash
apps/api/.venv/bin/python -m pip install -e ./packages/py-contracts
apps/solarsage/venv/bin/python -m pip install -e ./packages/py-contracts
apps/api/.venv/bin/python -m pip check
apps/solarsage/venv/bin/python -m pip check
```

Proof:

```bash
apps/api/.venv/bin/python -c 'import solarsage_contracts; print(solarsage_contracts.__file__)'
apps/solarsage/venv/bin/python -c 'import solarsage_contracts; print(solarsage_contracts.__file__)'
```

Оба paths должны указывать на `packages/py-contracts/solarsage_contracts`.
Не выводить весь environment или secrets.

## 13. Canonical parity fixtures

Создать один semantic object в двух test-only casings:

```text
packages/py-contracts/tests/fixtures/activation-layer-snake.json
apps/api/tests/fixtures/contracts/activation-layer-public-camel.json
```

Object содержит:

- root versions `activation-layer.v1`, `al-1.1`, `ss-calc-1.2.0`;
- target `2026-07-08 12:00 Europe/Moscow`, `WHOLE_SIGN`;
- timed `t2n__MOON__OPPOSITION__PLUTO` evidence;
- date-only `annual_profection__HOUSE__10` evidence;
- matching `by_planet`/`by_house` indexes;
- empty `by_lot`, `by_angle`, `warnings`;
- all model-dumped optional/default fields, including explicit nulls;
- debug timing keys remain snake_case inside arbitrary `debug` dict.

Use the exact values already present in
`test_activation_layer_service_timed_sidecar_parity`; do not invent another
semantic fixture.

Canonical file formatting:

```text
json.dumps(..., indent=2, sort_keys=True, ensure_ascii=False) + "\n"
```

Do not import these fixtures in production code.

## 14. Python test requirements

### 14.1 `test_activation_contract.py`

Prove shared-only behavior:

1. Exact evidence field order equals section 7.1.
2. Exact layer field order equals section 7.2.
3. Required/default/default_factory matrix unchanged.
4. Strength rejects `<0` and `>1`.
5. Unknown field rejected.
6. All Literal values accepted; unknown value rejected.
7. Index validator accepts valid refs and rejects each of four invalid maps.
8. Generic layer materializes `ActivationEvidenceContract` correctly.
9. Default lists/dicts are not shared between instances.

### 14.2 `test_boundary_configs.py`

Add repo `apps/api` and `apps/solarsage` roots only inside test bootstrap, then
prove:

1. MRO/issubclass requirements from section 9.
2. API alias map exactly:

```text
technique_family -> techniqueFamily
target_type -> targetType
target_key -> targetKey
source_planet -> sourcePlanet
source_frame -> sourceFrame
target_planet -> targetPlanet
target_frame -> targetFrame
active_from -> activeFrom
exact_at -> exactAt
active_until -> activeUntil
weight_hint -> weightHint
schema_version -> schemaVersion
activation_layer_version -> activationLayerVersion
calculation_version -> calculationVersion
target_date -> targetDate
target_time -> targetTime
target_tz -> targetTz
house_system -> houseSystem
by_planet -> byPlanet
by_house -> byHouse
by_lot -> byLot
by_angle -> byAngle
```

Unlisted single-word fields keep same wire name.

3. API accepts canonical snake and camel fixtures.
4. API recursive `model_dump(mode="json", by_alias=True)` byte-matches public
   camel fixture.
5. Sidecar validates snake fixture and byte-matches it after canonical dump.
6. Sidecar camel-only root/evidence aliases reject.
7. API and sidecar field order/requiredness/defaults/constraints match shared.
8. Both wrappers execute identical index validator behavior/message.
9. Nested activation runtime type is correct wrapper, not shared base.
10. AST of both wrapper files contains no field `AnnAssign`, no local validator,
    no local Literal assignment and no version literal.
11. AST/import scan of `packages/py-contracts/solarsage_contracts` contains no
    import starting `app`, `apps`, or `solarsage`.

AST guards inspect syntax, not docstrings/comments.

### 14.3 `test_versions.py`

Prove:

- exact three shared constants;
- API core values equal shared values;
- sidecar core values equal shared values;
- both app core files import/re-export, not assign duplicated literals;
- both app pyprojects contain exact dependency once;
- package distribution metadata remains `0.1.0` and is distinct from wire
  versions.

### 14.4 Existing tests

Update only where architecture changed:

- replace `test_api_and_sidecar_calculation_version_literals_match` with a
  shared-source equality/AST proof; duplicated literals are no longer expected;
- preserve all existing schema behavior tests;
- add sidecar extra-forbid and snake-only proof;
- sidecar endpoint meta default still equals `al-1.1` via imported constant.

Do not delete/relax existing assertions.

## 15. Generated Zod parity test

Create `__tests__/contracts/activation-shared-parity.test.ts` with full GRACE
header/map. It must:

- load `activation-layer-public-camel.json` as test data;
- import generated `ActivationLayer` Zod schema;
- assert valid fixture parses;
- assert missing required nested `id` rejects;
- assert wrong `activeFrom` type rejects;
- assert date-only period strings remain strings;
- use no CSS/UI/runtime mocks.

No frontend product file changes.

## 16. OpenAPI zero-diff gate

После wrapper migration:

```bash
pnpm contracts:generate
sha256sum \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts
git diff -- \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts
```

Hashes обязаны совпасть с section 2, diff обязан быть пустым.

Mandatory OpenAPI structural checks:

```text
components.schemas.ActivationEvidence exists
components.schemas.ActivationLayer exists
ActivationLayer.activations.items.$ref ends /ActivationEvidence
no ActivationEvidenceContract component
no ActivationLayerContract component
no generic/specialization component name
public property casing unchanged
descriptions unchanged
required arrays unchanged
defaults unchanged
```

Если хоть один generated byte отличается — не принимать migration как
"семантически то же". Остановиться и вернуть exact diff.

## 17. Real wire parity after migration

Повторить section 2 representative build тем же process/serialization.

Обязательные exact hashes:

```text
snake: 3c9b7038d3c01972ceb418160c918d40d4fa14d3542864ffa881a700f4437a5d
camel: 0405c10915a8b327fc1d6dffc71963830132caeca61cb8c2bee5c7c49359267b
```

Дополнительно сравнить post-migration canonical JSON byte-for-byte с
`/tmp/stage-a1-*` baseline. Не включать full payload в callback.

## 18. Mandatory gates

### 18.1 Package/install

```bash
apps/api/.venv/bin/python -m pip install -e ./packages/py-contracts
apps/solarsage/venv/bin/python -m pip install -e ./packages/py-contracts
apps/api/.venv/bin/python -m pip check
apps/solarsage/venv/bin/python -m pip check

apps/api/.venv/bin/python -m pytest packages/py-contracts/tests -q
apps/solarsage/venv/bin/python -m pytest packages/py-contracts/tests -q
```

### 18.2 Sidecar

```bash
cd apps/solarsage
venv/bin/python -m pytest \
  tests/test_activation_schema.py \
  tests/test_activation_layer_endpoint.py \
  tests/test_activation_transits.py -q
venv/bin/python -m pytest tests -q
```

### 18.3 API

```bash
cd apps/api
source .venv/bin/activate
python -m pytest \
  tests/test_activation_contracts.py \
  tests/test_activation_layer_contract.py \
  tests/test_activation_layer_transits.py \
  tests/test_today_meta_versions.py \
  tests/test_pipeline_invariants.py -q
python -m pytest tests -q
```

Known base API full state:

```text
6 failed, 830 passed, 5 skipped
```

Разрешён только exact same six baseline failures from `43_S2_W1_ACCEPTANCE.md`
и большее pass count из-за новых tests. Никаких новых failure/trace изменений.
Не чинить их в A1.

### 18.4 Contracts/static

```bash
pnpm contracts:generate
pnpm contracts:check
npx vitest run __tests__/contracts
npx tsc --noEmit

apps/api/.venv/bin/python -m compileall \
  packages/py-contracts/solarsage_contracts \
  packages/py-contracts/tests \
  apps/api/app/schemas/activation.py \
  apps/api/app/core/versions.py

apps/solarsage/venv/bin/python -m compileall \
  apps/solarsage/solarsage/schemas/activation.py \
  apps/solarsage/solarsage/core/versions.py

git diff --check
rg -n '[ \t]+$' \
  packages/py-contracts \
  apps/api/app/schemas/activation.py \
  apps/api/app/core/versions.py \
  apps/solarsage/solarsage/schemas/activation.py \
  apps/solarsage/solarsage/core/versions.py \
  apps/solarsage/solarsage/api/activation_layer.py \
  __tests__/contracts/activation-shared-parity.test.ts
```

`rg` должен вернуть no matches. Учитывать, что обычный `git diff --check` не
видит untracked files.

## 19. Scope/final state audit

Перед callback:

```bash
git status --short
git diff --name-only
git diff --cached --name-only
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
```

Требования:

- HEAD/origin всё ещё `524812f...`;
- index empty;
- no commit/push;
- no generated diff;
- no Docker/CI/scripts/package.json changes;
- no frontend product changes;
- unrelated untracked preserved;
- only exact allowlist paths changed/new.

## 20. Callback

Вернуть:

```text
READY_STAGE_A1_SHARED_MODELS
branch: preview/solarsage-v2-human-first-navigator-ux
head: 524812fd9764770e247029651924a731addab4af
origin_feature: 524812fd9764770e247029651924a731addab4af
shared_package: solarsage-contracts 0.1.0
shared_module_api_path: <path>
shared_module_sidecar_path: <path>
shared_fields_single_source: PASS
api_camel: PASS
sidecar_snake: PASS
wire_fixture_parity: PASS
wire_real_snake: PASS 3c9b7038...
wire_real_camel: PASS 0405c109...
index_validator_shared: PASS
ast_guards: PASS
versions_unchanged: PASS
version_literals_single_source: PASS
pip_check_api: PASS
pip_check_sidecar: PASS
shared_tests_api_venv: <result>
shared_tests_sidecar_venv: <result>
sidecar_focused: <result>
sidecar_full: <result>
api_focused: <result>
api_full: BASELINE_RED_IDENTICAL <counts>
openapi_hash: bc4c9f93...
generated_ts_hash: 8027ad45...
generated_zod_hash: bed54dd3...
generated_diff: ZERO
contract_tests: <result>
typecheck: PASS
diff_paths: <exact list>
index: EMPTY
commit: NOT_YET
push: NOT_YET
```

После callback остановиться. Не начинать A2.
