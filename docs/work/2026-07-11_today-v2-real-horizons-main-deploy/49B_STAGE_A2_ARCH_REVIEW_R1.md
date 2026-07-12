# Stage A2 Architect Review R1 — compatibility false negatives and compose runtime

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Reviewed base HEAD: `6d0da88a815b1fa17d4e511b3bcf076d130bdc0a`
Implementation TZ: `49_STAGE_A2_CONTRACT_AUTOMATION_IMPLEMENTATION_TZ.md`
Packaging correction: `49A_STAGE_A2_SIDECAR_PACKAGING_CORRECTION.md`
Статус: **CHANGES REQUIRED / commit и push запрещены**.

## 1. Итог ревью

Положительно подтверждены:

- class-object registry и OpenAPI zero-diff;
- real merge-base classification `additive`;
- shared/registry/compat tests и `contracts:sync`;
- CI Python 3.12/shared-first install/new sidecar job;
- clean API/sidecar Docker builds/imports;
- permanent correction `setuptools.build_meta`;
- proof images/containers cleanup;
- no systemd/port changes.

Acceptance пока блокируют три функциональных дефекта и один packaging-quality
дефект ниже.

## 2. BLOCKER R1 — checker пропускает реальные breaking schema keywords

Независимый architect probe на текущей реализации вернул:

```text
const changed:       no-change
format changed:      no-change
uniqueItems added:   no-change
allOf ref changed:   no-change
```

Это ложные отрицательные результаты. Текущий OpenAPI реально использует
`const` и `format`, в том числе discriminator/card kinds, schema versions,
date/time/UUID fields. Такой checker может пропустить несовместимое изменение и
дать CI exit `0`.

### Required correction

В `scripts/contracts/check_compat.py` добавить explicit comparison минимум:

#### Non-version `const`

```text
absent -> const: breaking (accepted values narrowed)
const -> absent: additive (accepted values widened)
const A -> const B: breaking
```

Known version property продолжает идти через version discipline и не должен
получать второе ложное breaking при monotonic increase.

#### `format`

```text
absent -> format: breaking
format -> absent: additive
format A -> format B: breaking
```

#### `uniqueItems`

Отсутствие трактовать как `false`:

```text
false -> true: breaking
true -> false: additive
```

#### `allOf`

Порядок/annotations нормализовать. Exact normalized equality — no change.
Любое semantic изменение `allOf` пока классифицировать conservative breaking;
не пытаться доказывать subtype equivalence.

#### Remaining structural keywords

После обработки известных keys сравнить residual schema keys. Исключить только:

- documentation-only keys;
- keys, уже полностью обработанные comparator-ом.

Любое изменение неизвестного structural key классифицировать conservative
breaking `schema-key-changed`, чтобы новый JSON Schema keyword не проходил
silent `no-change`.

Не создавать duplicate report items для `properties`, `required`, `type`,
`items`, unions, enum, constraints, discriminator, `$ref`, defaults и
additionalProperties.

### Required tests

Добавить минимум:

```text
const add -> breaking
const remove -> additive
const change -> breaking
known version const monotonic increase -> informational/non-breaking
format add/change -> breaking
format remove -> additive
uniqueItems tighten -> breaking
uniqueItems loosen -> additive
allOf ref change -> breaking
unknown structural keyword change -> breaking
```

Повторить architect probe: ни один из четырёх случаев выше не может вернуть
`no-change`.

## 3. BLOCKER R2 — permanent real-artifact test ломает CI после merge

Сейчас:

```py
test_real_current_artifact_against_merge_base_is_additive_without_breaking
```

требует только `classification == "additive"`.

После merge в `main` default `git merge-base HEAD origin/main` равен текущему
HEAD, поэтому корректный результат будет `no-change`. `pnpm contracts:check`
запускает этот test, следовательно push CI на `main` станет красным без
контрактного дефекта.

### Required correction

Permanent test обязан проверять invariant:

```py
assert classification in {"no-change", "additive"}
assert breakingChanges == []
assert overrideUsed is False
```

Точное ожидание `additive` для текущей preview branch оставить как runtime gate
в A2 callback/architect command, не как вечный unit invariant.

Добавить отдельный unit case, где base/current identical и integration
invariant принимает `no-change`.

## 4. BLOCKER R3 — canonical compose всё ещё запускает несуществующий module

`apps/solarsage/Dockerfile` правильно использует:

```text
solarsage.app:app
```

Но `docker-compose.yml` override-ит CMD обратно:

```yaml
command: uvicorn solarsage.main:app --host 0.0.0.0 --port 8001
```

Обычный `docker compose up solarsage` поэтому остаётся сломанным.

### Required correction

Изменить ровно module path, сохранив host/container port:

```yaml
command: uvicorn solarsage.app:app --host 0.0.0.0 --port 8001
```

`docker-compose.prod.yml` не имеет override и уже использует Dockerfile CMD.

Proof после правки:

```bash
docker compose config --quiet
docker compose -f docker-compose.prod.yml config --quiet
docker compose config | rg 'solarsage\.app:app'
! docker compose config | rg 'solarsage\.main:app'
```

Не выполнять compose up и не занимать host ports.

## 5. BLOCKER R4 — compiler toolchain остаётся в runtime sidecar image

Текущий sidecar image устанавливает `g++`, `gcc`, `libc6-dev` отдельным layer и
оставляет их в финальном runtime image. Полученный proof image около `443 MB`.
Это лишняя attack surface и production bloat.

### Required correction

Выбрать один из двух допустимых вариантов:

1. multi-stage builder: build wheels с compiler, runtime stage устанавливает
   только wheels; или
2. один `RUN`, который устанавливает build deps, выполняет `pip install .`,
   затем `apt-get purge --auto-remove` и cleanup в том же layer.

Предпочтителен multi-stage builder, но вариант 2 допустим, если final proof
показывает отсутствие compiler binaries.

Required final smoke:

```bash
docker run --rm --entrypoint sh solarsage-sidecar-contract-proof:a2 -c \
  '! command -v gcc && ! command -v g++'
```

Import/version smoke из 49A сохранить. Proof image затем удалить exact tag.

## 6. Non-blocking cleanup

`sync.sh` печатает temp report path непосредственно перед `trap`, после выхода
файл уже удалён. Лучше заменить строку на summary без обещания существующего
artifact, но это не блокирует acceptance.

## 7. Разрешённый scope correction

Исправлять только уже разрешённые A2 paths:

```text
scripts/contracts/check_compat.py
scripts/contracts/test_check_compat.py
docker-compose.yml
apps/solarsage/Dockerfile
```

и этот review document. Другие product paths не менять.

## 8. Mandatory rerun

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

docker build -f apps/solarsage/Dockerfile \
  -t solarsage-sidecar-contract-proof:a2 .
# import/version/no-compiler smokes
docker image rm solarsage-sidecar-contract-proof:a2

git diff --check
git status --short
git diff --cached --name-only
```

Generated hashes/diff должны остаться exact A1/A2 baseline. Full API/sidecar
не нужно повторять, если correction не затронет Python app/runtime schemas;
архитектор всё равно повторит их при acceptance.

## 9. Callback

```text
READY_STAGE_A2_REVIEW_R1
compat_const: PASS
compat_format: PASS
compat_unique_items: PASS
compat_allof: PASS
compat_unknown_keyword_fails_closed: PASS
real_artifact_no_change_or_additive: PASS
current_preview_real_compat: additive breaking=0
canonical_compose_entrypoint: solarsage.app:app
sidecar_image_import: PASS
sidecar_image_shared_version: 0.1.0
sidecar_image_compilers: ABSENT
proof_image: REMOVED
focused_tests: <count> passed
contracts_sync: PASS
contracts_check: PASS
generated_diff: ZERO
index: EMPTY
commit: NOT_YET
push: NOT_YET
```

После callback остановиться. Commit/push, A3 и Stage B запрещены.
