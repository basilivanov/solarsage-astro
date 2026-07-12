# Stage A2 Architect Review R3 — version metadata ownership must fail closed

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Reviewed base HEAD: `6d0da88a815b1fa17d4e511b3bcf076d130bdc0a`
Parent correction: `49C_STAGE_A2_ARCH_REVIEW_R2.md`
Статус: **ONE CHECKER BLOCKER / commit и push запрещены**.

## 0. Режим и границы

1. Полностью прочитать этот файл до edits.
2. Исправить только два checker paths из section 4.
3. Не менять Docker/compose/CI/registry/shared package/generated contracts.
4. Не запускать субагентов.
5. Не делать `git add`, commit, push, merge, rebase, checkout, switch или
   reset.
6. Не начинать Stage B, A3, baseline fixes или release.

## 1. Что уже принято из R2

Не переделывать следующие принятые части:

- strict slash parser `^([a-z][a-z0-9-]*)/v(\d+)$`;
- slash family/downgrade/malformed classifications;
- multi-value version enum narrowing остаётся breaking;
- sidecar runtime копирует `grace/canon` в `/usr/local/lib/grace/canon`;
- sidecar import/version/no-compiler/canon smokes прошли;
- proof image удалён;
- generated hashes/diff exact;
- real preview compat `additive`, breaking `0`, override `false`.

## 2. BLOCKER R8 — selected default masks changed const/singleton enum

### 2.1 Причина

`extract_version_value()` выбирает declaration по priority:

```text
default -> const -> singleton enum
```

Но текущие generic comparators подавляются шире:

- `compare_const()` unconditional возвращается для любого known version
  property;
- `compare_enum()` возвращается для любых двух singleton string enums на known
  version property.

Следовательно generic declaration может быть проигнорирован, хотя version
discipline сравнивала **другое** declaration.

### 2.2 Подтверждённые false negatives

Architect probe текущей R2 реализации:

```text
case A
base:    default=today.v1 enum=[today.v1]
current: default=today.v1 enum=[today.v2]
actual:  no-change
required: breaking enum-changed

case B
base:    default=today.v1 enum=[today.v1]
current: default=today.v2 enum=[today.v3]
actual:  additive + version-monotonic-increase
required: breaking because enum declaration diverges from selected version

case C
base:    default=today.v1 const=today.v1
current: default=today.v1 const=today.v2
actual:  no-change
required: breaking const-changed
```

Это silent false negative: CI exit `0` при structural drift.

## 3. Required implementation

Version discipline может владеть generic declaration только когда она
действительно сравнивает значение этого declaration.

### 3.1 Singleton enum ownership

В `compare_enum()` сохранить skip только если выполнены **все** условия:

```text
property_name входит в KNOWN_VERSION_PROPERTIES
base enum = singleton string
current enum = singleton string
extract_version_value(base_schema) == base_enum[0]
extract_version_value(current_schema) == current_enum[0]
```

Тогда version discipline действительно сравнила эти enum values и duplicate
generic report не нужен.

Если хотя бы equality не выполнено, использовать обычный enum comparator:

- value change -> `enum-changed` breaking;
- widen/narrow по существующим правилам;
- shape drift по существующим conservative rules.

Не менять поведение non-version enum и multi-value version enum.

### 3.2 Const ownership

В `compare_const()` нельзя unconditional skip по одному property name.

Skip generic const comparison допустим только для cases, где:

```text
обе стороны не содержат const
```

или где обе стороны содержат const и:

```text
extract_version_value(base_schema) == base_schema["const"]
extract_version_value(current_schema) == current_schema["const"]
```

Во всех остальных cases выполнять существующую generic const policy:

```text
absent -> const: breaking const-added
const -> absent: additive const-removed
const A -> const B: breaking const-changed
```

Это также закрывает declaration-shape drift:

```text
default-only -> same default + const
```

должен быть breaking `const-added`, потому что accepted values сузились.

### 3.3 Не создавать новый broad abstraction без необходимости

Допустим маленький helper для проверки ownership, если он:

- deterministic;
- pure;
- не меняет `extract_version_value()` priority;
- имеет function contract, если является нетривиальной публичной/модульной
  функцией;
- не выводит schema payload в report.

Не добавлять validation framework и не менять report schema в этой correction.

## 4. Exact allowlist

Разрешены только:

```text
scripts/contracts/check_compat.py
scripts/contracts/test_check_compat.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49D_STAGE_A2_ARCH_REVIEW_R3.md
```

Документ уже создан architect и coder его не переписывает.

Generated files могут быть переписаны существующим generator только для
proof, но итоговый generated diff обязан быть zero.

## 5. Required tests

Добавить минимум четыре direct report cases.

### 5.1 Stable default, changed singleton enum

```text
base:    default=today.v1 enum=[today.v1]
current: default=today.v1 enum=[today.v2]

classification: breaking
breaking kind: enum-changed
informational version increase: absent
```

### 5.2 Monotonic default, divergent singleton enum

```text
base:    default=today.v1 enum=[today.v1]
current: default=today.v2 enum=[today.v3]

classification: breaking
breaking kind: enum-changed
informational kind: version-monotonic-increase
```

### 5.3 Stable default, changed const

```text
base:    default=today.v1 const=today.v1
current: default=today.v1 const=today.v2

classification: breaking
breaking kind: const-changed
```

### 5.4 Aligned declarations remain non-breaking

```text
base:    default=today.v1 enum=[today.v1] const=today.v1
current: default=today.v2 enum=[today.v2] const=today.v2

classification: additive
breaking: empty
informational: version-monotonic-increase exactly once after dedup
generic enum-changed: absent
generic const-changed: absent
```

Сохранить и повторно пройти:

- singleton enum without default `today.v1 -> today.v2` informational;
- slash const `today/v1 -> today/v2` informational;
- default + multi enum narrowing breaking;
- non-version const/enum matrix;
- R1 structural keyword tests.

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

Expected real compat remains:

```text
classification: additive
breakingChanges: 0
overrideUsed: false
```

Expected generated hashes remain:

```text
bc4c9f93cee4c45e67cc568ea35c13716079ac818bbd2a558b1d23f7859e98ff
8027ad45c4077318b2c5eafc4b0f1ec1cb61fc9dd319cd106195a03a21d2163f
bed54dd3c09adfe502538747a8c18fd8b059855a43a98783dd385755fb8b33f6
```

Docker proof повторять не требуется: Dockerfile не входит в R3 scope и R2
canon proof уже прошёл. Architect повторит Docker при финальной acceptance.

## 7. Callback

```text
READY_STAGE_A2_REVIEW_R3
stable_default_changed_singleton_enum: BREAKING_PASS
monotonic_default_divergent_singleton_enum: BREAKING_PASS
stable_default_changed_const: BREAKING_PASS
aligned_default_const_enum_bump: INFORMATIONAL_PASS
singleton_enum_only_bump: INFORMATIONAL_PASS
slash_const_bump: INFORMATIONAL_PASS
multi_enum_narrowing: BREAKING_PASS
focused_tests: <count> passed
current_preview_real_compat: additive breaking=0 override=false
contracts_sync: PASS
contracts_check: PASS
contract_vitest: 132 passed
typecheck: PASS
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
