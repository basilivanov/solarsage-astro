# Stage A2 Architect Review R2 — version discipline and sidecar canon runtime

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Reviewed base HEAD: `6d0da88a815b1fa17d4e511b3bcf076d130bdc0a`
Implementation TZ: `49_STAGE_A2_CONTRACT_AUTOMATION_IMPLEMENTATION_TZ.md`
Previous corrections: `49A_STAGE_A2_SIDECAR_PACKAGING_CORRECTION.md`,
`49B_STAGE_A2_ARCH_REVIEW_R1.md`
Статус: **CHANGES REQUIRED / commit и push запрещены**.

## 0. Режим работы

1. Полностью прочитать этот файл, `49`, `49A` и `49B` до edits.
2. Работать только в текущей preview branch и только в scope ниже.
3. Не запускать субагентов, delegated agents или параллельных coding agents.
4. Не выполнять `git add`, commit, push, merge, rebase, checkout, switch или
   reset.
5. Не начинать `50_STAGE_B_REAL_HORIZONS_ACTIONS_FRONTEND_TZ.md`, A3,
   baseline stabilization или release/deploy.
6. Не менять public activation fields, aliases, validators, defaults, versions,
   generated TS/Zod/OpenAPI или product behavior.
7. Не трогать unrelated paths:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 1. Итог R2

Исправления R1–R4 из `49B` подтверждены:

- `const`, `format`, `uniqueItems`, `allOf` и unknown structural keyword больше
  не проходят как silent `no-change`;
- permanent real-artifact test допускает `no-change|additive` и запрещает
  breaking/override;
- canonical compose использует `solarsage.app:app`;
- sidecar runtime image не содержит `gcc`/`g++`;
- focused suite сообщает `97 passed`, current real delta остаётся `additive`,
  breaking `0`;
- generated artifacts не изменены.

Acceptance всё ещё блокируют два класса дефектов:

1. version discipline даёт ложный `breaking` для поддерживаемого singleton
   enum и для реально существующих slash-style schema versions;
2. sidecar Docker image импортируется, но падает при первом реальном чтении
   canon YAML, поэтому calculation runtime внутри Docker неработоспособен.

## 2. BLOCKER R5 — singleton version enum получает двойную классификацию

### 2.1 Независимый probe

Текущий checker для known version property:

```text
schemaVersion enum [today.v1] -> [today.v2]
```

возвращает:

```text
classification: breaking
breaking: enum-changed
informational: version-monotonic-increase
```

Причина:

- `extract_version_value()` намеренно умеет читать singleton enum;
- `compare_default()` корректно передаёт change в version discipline;
- затем generic `compare_enum()` повторно классифицирует тот же singleton
  version change как `enum-changed`.

Это противоречит section 5.7 исходного ТЗ: monotonic known-version increase
должен быть informational/non-breaking.

### 2.2 Required correction

Изменить только comparator ownership, не отключая enum compatibility целиком.

Допустимая реализация:

- передать `property_name` в `compare_enum()` или добавить узкий helper;
- если property входит в `KNOWN_VERSION_PROPERTIES` **и одновременно** base и
  current содержат singleton string enum, version discipline является
  единственным владельцем сравнения этих двух singleton values;
- generic enum comparator для этого exact случая не добавляет
  `enum-changed`/`enum-narrowed`/`enum-widened`;
- non-version enum работает без изменений;
- multi-value version enum продолжает сравниваться generic comparator-ом;
- structural narrowing multi-value enum остаётся breaking даже при
  одновременном monotonic default bump.

Нельзя просто делать unconditional `return` для любого enum на known property.
Следующий случай обязан остаться breaking:

```text
base:
  payloadVersion default today.v1 enum [today.v1, today.v2]
current:
  payloadVersion default today.v2 enum [today.v2]
```

Здесь default bump informational, но removal `today.v1` из accepted enum —
structural narrowing и итоговый result `breaking`.

### 2.3 Required tests

Добавить минимум:

```text
known singleton enum today.v1 -> today.v2:
  classification additive
  informational version-monotonic-increase
  breaking empty
  generic enum-changed absent

known default + multi enum narrowing:
  classification breaking
  enum-narrowed present
```

Существующие non-version enum widen/narrow tests сохранить.

## 3. BLOCKER R6 — checker не понимает реальные slash-style schema versions

### 3.1 Фактический public wire

Текущий generated OpenAPI содержит:

```text
CalendarMeta.schemaVersion const calendar/v1
NatalMeta.schemaVersion    const natal/v1
TodayMeta.schemaVersion    const today/v1
```

Но `parse_known_version()` понимает `today.vN`, а slash-style family не
понимает. Поэтому реальный monotonic change:

```text
today/v1 -> today/v2
```

сейчас возвращает:

```text
classification: breaking
breaking: version-malformed
```

Это делает обычное будущее повышение уже существующего public schema version
невозможным без breaking override.

### 3.2 Required correction

Добавить строгую поддержку slash-style family. Предпочтительный deterministic
pattern:

```regex
^([a-z][a-z0-9-]*)/v(\d+)$
```

Family в parsed result должна включать prefix, например `slash:today`, чтобы:

```text
today/v1 -> today/v2       informational
calendar/v1 -> calendar/v2 informational
natal/v1 -> natal/v2       informational
calendar/v1 -> natal/v2    breaking family-changed
today/v2 -> today/v1       breaking downgrade
today/v1 -> today/vx       breaking malformed
```

Существующие formats из section 5.7 сохранить без регрессии:

```text
activation-layer.vN
al-N.N
ss-calc-N.N.N
ss-scoring-N.N
today.vN
```

Не нормализовать dot и slash family друг в друга: `today.v1 -> today/v2`
остаётся family change и conservative breaking.

### 3.3 Required tests

Добавить parameterized tests минимум для:

- `calendar/v1 -> calendar/v2` informational/non-breaking;
- `natal/v1 -> natal/v2` informational/non-breaking;
- `today/v1 -> today/v2` informational/non-breaking;
- slash family change -> breaking;
- slash downgrade -> breaking;
- malformed slash version -> breaking.

Проверять не только classification, но и отсутствие unexpected
`const-changed`/`enum-changed`: known version comparator должен владеть version
value ровно один раз.

## 4. BLOCKER R7 — sidecar Docker runtime не содержит canon YAML

### 4.1 Независимый proof

Architect собрал текущий image exact temporary tag и подтвердил:

```text
import solarsage.app: PASS
solarsage-contracts version: 0.1.0
gcc/g++: ABSENT
```

Но реальные canon loaders падают:

```text
FileNotFoundError: /usr/local/lib/grace/canon/aspect_rules.v1.yml
FileNotFoundError: /usr/local/lib/grace/canon/activation_rules.v1.yml
FileNotFoundError: /usr/local/lib/grace/canon/firdar.v1.yml
```

Причина — sidecar services вычисляют project root от установленного wheel:

```text
/usr/local/lib/python3.12/site-packages/solarsage/services/...
  -> four parents
  -> /usr/local/lib
  -> grace/canon/*.yml
```

Новый multi-stage image копирует wheel, но не копирует `grace/canon` в runtime.
Import-only smoke поэтому был ложноположительным: YAML читаются лениво при
calculation request.

Architect proof image `solarsage-sidecar-contract-proof:architect-r2` уже
удалён. Чужие images/containers не трогались.

### 4.2 Required Docker correction

В runtime stage `apps/solarsage/Dockerfile` добавить ровно canon assets по тому
же installed-package contract, который уже применён API image:

```dockerfile
COPY grace/canon /usr/local/lib/grace/canon
```

Обновить Dockerfile GRACE contract:

- `inputs` включает `grace/canon`;
- `dependencies` включает canon YAML;
- invariant фиксирует наличие canon в path, который ожидают installed sidecar
  services.

Не делать:

- не копировать весь repository или весь `grace/`;
- не менять `_resolve_canon_path()` в product services в этой волне;
- не добавлять env/path workaround;
- не возвращать compiler toolchain в runtime;
- не менять compose ports/commands;
- не запускать compose up и не bind-ить host ports.

Root `.dockerignore` уже не исключает `grace/canon`; менять его не требуется.

### 4.3 Required image smokes

После build обязательны все проверки, а не только import:

```bash
docker build -f apps/solarsage/Dockerfile \
  -t solarsage-sidecar-contract-proof:a2 .

docker run --rm --entrypoint python \
  solarsage-sidecar-contract-proof:a2 -c \
  'from importlib.metadata import version; import solarsage.app, solarsage_contracts; assert version("solarsage-contracts") == "0.1.0"; print("sidecar-import-ok")'

docker run --rm --entrypoint sh \
  solarsage-sidecar-contract-proof:a2 -c \
  '! command -v gcc && ! command -v g++ && echo compilers-absent'

docker run --rm --entrypoint python \
  solarsage-sidecar-contract-proof:a2 -c \
  'from solarsage.services.activation_builder import _load_aspect_rules, _load_activation_rules; from solarsage.services.firdar import _load_firdar_canon; from solarsage.services.eclipses import _load_canon_config; assert _load_aspect_rules()["schema_version"] == "aspect_rules.v1"; assert _load_activation_rules()["schema_version"] == "activation_rules.v1"; assert _load_firdar_canon()["schema_version"] == "firdar.v1"; assert _load_canon_config(); print("sidecar-canon-ok")'
```

После smoke удалить только exact proof tag:

```bash
docker image rm solarsage-sidecar-contract-proof:a2
```

## 5. Exact correction scope

Разрешены только:

```text
scripts/contracts/check_compat.py
scripts/contracts/test_check_compat.py
apps/solarsage/Dockerfile
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49C_STAGE_A2_ARCH_REVIEW_R2.md
```

Документ уже создан architect; coder его не переписывает, кроме исправления
явной опечатки по согласованию.

Generated artifacts можно перегенерировать для proof, но итоговый diff обязан
быть zero:

```text
packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
```

## 6. Mandatory rerun

```bash
apps/api/.venv/bin/python -m pytest \
  packages/py-contracts/tests \
  apps/api/tests/test_contract_registry.py \
  scripts/contracts/test_check_compat.py -q

pnpm contracts:sync
pnpm contracts:check
pnpm contracts:compat
npx vitest run __tests__/contracts
npx tsc --noEmit

docker compose config --quiet
docker compose -f docker-compose.prod.yml config --quiet

# sidecar build + import/version/compiler/canon smokes from section 4.3

sha256sum \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts

git diff --exit-code -- \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts

git diff --check
git status --short
git diff --cached --name-only
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
```

Expected generated hashes остаются:

```text
bc4c9f93cee4c45e67cc568ea35c13716079ac818bbd2a558b1d23f7859e98ff
8027ad45c4077318b2c5eafc4b0f1ec1cb61fc9dd319cd106195a03a21d2163f
bed54dd3c09adfe502538747a8c18fd8b059855a43a98783dd385755fb8b33f6
```

Current preview real compat обязан остаться:

```text
classification: additive
breakingChanges: 0
overrideUsed: false
```

Full API/sidecar suites coder повторно не запускает: correction не меняет
application Python code или schemas. Architect повторит full suites при
финальной A2 acceptance.

## 7. Callback

```text
READY_STAGE_A2_REVIEW_R2
known_version_singleton_enum: PASS
known_version_multi_enum_narrowing: BREAKING_PASS
slash_versions_calendar_natal_today: PASS
slash_family_change: BREAKING_PASS
slash_downgrade_malformed: BREAKING_PASS
current_preview_real_compat: additive breaking=0 override=false
focused_tests: <count> passed
contracts_sync: PASS
contracts_check: PASS
contract_vitest: 132 passed
typecheck: PASS
compose_config: PASS
sidecar_image_import: PASS
sidecar_image_shared_version: 0.1.0
sidecar_image_compilers: ABSENT
sidecar_image_canon_loaders: PASS
proof_image: REMOVED
generated_hashes: PASS <three short hashes>
generated_diff: ZERO
index: EMPTY
head: 6d0da88a815b1fa17d4e511b3bcf076d130bdc0a
origin_feature: 6d0da88a815b1fa17d4e511b3bcf076d130bdc0a
commit: NOT_YET
push: NOT_YET
```

После callback остановиться. Commit/push и Stage B запрещены до architect
acceptance.
