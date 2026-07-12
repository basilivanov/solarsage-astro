# Stage A2 Acceptance — contract automation, CI and Docker

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted base HEAD/origin: `6d0da88a815b1fa17d4e511b3bcf076d130bdc0a`
Implementation TZ: `49_STAGE_A2_CONTRACT_AUTOMATION_IMPLEMENTATION_TZ.md`
Corrections: `49A`, `49B`, `49C`, `49D`
Статус: **ACCEPTED / READY FOR EXACT COMMIT AND PUSH**.

## 1. Принятый результат

Stage A2 создаёт рабочую цепочку:

```text
explicit class-object API registry
  -> deterministic OpenAPI generation
  -> fail-closed compatibility classification against Git base
  -> developer sync/check commands
  -> Python 3.12 shared-first CI for API and sidecar
  -> repo-root Docker builds with installed shared contracts
```

Public product payload, activation aliases/defaults/validators и generated
wire artifacts не изменены этой стадией.

## 2. Registry и generation

Принято:

- `PUBLIC_CONTRACT_ROOTS` содержит exact 22 API-owned `CamelModel` classes;
- порядок и имена совпадают с ТЗ;
- string/getattr registry удалён из exporter;
- shared `*Contract` classes не становятся public roots;
- duplicate object/name/title, unsorted, non-class/non-Camel/shared roots
  отклоняются deterministic validation;
- OpenAPI dummy roots и component names не изменились;
- generated artifacts имеют zero diff.

Exact hashes:

```text
bc4c9f93cee4c45e67cc568ea35c13716079ac818bbd2a558b1d23f7859e98ff  packages/contracts/openapi.json
8027ad45c4077318b2c5eafc4b0f1ec1cb61fc9dd319cd106195a03a21d2163f  packages/contracts/_generated.ts
bed54dd3c09adfe502538747a8c18fd8b059855a43a98783dd385755fb8b33f6  packages/contracts/_generated.zod.ts
```

## 3. Compatibility checker

Принят stdlib checker с:

- safe Git ref resolution без `shell=True`;
- deterministic human/JSON report;
- exit contract `0/1/2`;
- explicit breaking override только с non-empty reason;
- paths + component schemas comparison;
- ignored documentation annotations;
- additive/breaking constraints, enums, unions, nullability, refs,
  discriminator, defaults и additionalProperties;
- explicit `const`, `format`, `uniqueItems`, `allOf`;
- fail-closed residual structural keys;
- known version discipline для dot/dash и slash formats;
- correct ownership между `default`, `const` и singleton enum;
- multi-value version enum narrowing остаётся breaking;
- no silent version-metadata drift.

Targeted independent probes подтверждены:

```text
const add/remove/change: PASS
format add/remove/change: PASS
uniqueItems tighten/loosen: PASS
allOf semantic drift: PASS
unknown keyword fail-closed: PASS
singleton version enum bump: informational PASS
slash calendar/natal/today bump: informational PASS
slash family/downgrade/malformed: breaking PASS
stable default + changed enum: breaking PASS
monotonic default + divergent enum: breaking PASS
stable default + changed const: breaking PASS
aligned default/const/enum bump: informational once PASS
multi enum narrowing: breaking PASS
```

Real preview delta:

```text
classification: additive
breakingChanges: 0
overrideUsed: false

ActivationEvidence.activeFrom: optional-property-added
ActivationEvidence.activeUntil: optional-property-added
ActivationLayer.activationLayerVersion: al-1.0 -> al-1.1 informational
```

## 4. Developer commands and CI

Принято:

- `pnpm contracts:sync`;
- `pnpm contracts:check`;
- `pnpm contracts:compat`;
- focused shared/registry/compat guards;
- deterministic generation and fixture normalization;
- contract Vitest and TypeScript gates;
- Python `3.12` in all Python CI jobs;
- shared package installed before API/sidecar packages;
- new blocking sidecar full-test job;
- contract checkout `fetch-depth: 0`;
- push base selection uses `github.event.before`, zero SHA fallback only
  `HEAD^`;
- no `continue-on-error`, `|| true`, automatic allow-breaking or deploy job.

Known non-blocking cleanup retained: `sync.sh` prints its temporary report path
before exit trap removes that file. Это не влияет на correctness или CI и не
блокирует acceptance.

## 5. Docker и compose

Принято:

- repo-root contexts для API и sidecar в обоих compose files;
- API/sidecar Python `3.12-slim`;
- shared contract package устанавливается до service package;
- sidecar permanent build backend исправлен на `setuptools.build_meta`;
- sidecar использует multi-stage wheel build;
- compiler binaries отсутствуют в runtime;
- canonical entrypoint `solarsage.app:app` в Dockerfile и compose;
- sidecar runtime содержит `/usr/local/lib/grace/canon`;
- real sidecar canon loaders читают aspect/activation/firdar YAML;
- ports, systemd, nginx и env не менялись;
- proof containers использовали `--rm`, host ports не занимались;
- exact proof images удалены.

Independent final smokes:

```text
docker compose config: PASS
docker-compose.prod config: PASS
canonical compose solarsage.app:app: PASS
forbidden solarsage.main:app: ABSENT
API image build/import: PASS
API shared version 0.1.0: PASS
API canon readable: PASS
sidecar image build/import: PASS
sidecar shared version 0.1.0: PASS
sidecar gcc/g++: ABSENT
sidecar aspect/activation/firdar canon loaders: PASS
proof images: REMOVED
```

## 6. Test evidence

Final independent architect run:

```text
focused shared + registry + compat: 110 passed
contracts:sync: PASS
contracts:check: PASS
contracts:compat: additive, breaking 0, override false
contract Vitest: 132 passed
TypeScript typecheck: PASS
sidecar full: 201 passed, 1 warning
API full: 6 failed, 843 passed, 5 skipped, 1 warning
```

API result is exact accepted baseline-red. Только эти failures:

```text
test_calendar_status_cache_duplicate_rereads_winning_row
test_semantic_v2_service_no_convergence
test_semantic_v2_service_with_convergence
test_audit_canon_versions_only_contains_strings
test_techniques_list_is_sorted
test_today_payload_v2_block_included_when_flag_enabled
```

Новых failures нет. Эти baseline defects не исправляются в A2.

## 7. Static and scope audit

Подтверждено:

- YAML parse: CI + оба compose PASS;
- Python compileall PASS;
- `git diff --check` PASS;
- trailing whitespace в A2 files отсутствует;
- generated diff zero;
- index empty;
- HEAD = origin feature = `6d0da88...` до commit;
- proof images отсутствуют;
- systemd/nginx/ports unchanged;
- frontend product/test files не изменены A2;
- unrelated untracked paths сохранены без изменений.

Unrelated, запрещённые к staging:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 8. Accepted commit scope

В exact A2 commit разрешены:

```text
.github/workflows/ci.yml
.dockerignore
apps/api/Dockerfile
apps/api/app/schemas/contract_registry.py
apps/api/tests/test_contract_registry.py
apps/solarsage/Dockerfile
apps/solarsage/pyproject.toml
docker-compose.yml
docker-compose.prod.yml
package.json
packages/py-contracts/README.md
scripts/contracts/check.sh
scripts/contracts/check_compat.py
scripts/contracts/export_openapi.py
scripts/contracts/sync.sh
scripts/contracts/test_check_compat.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49_STAGE_A2_CONTRACT_AUTOMATION_IMPLEMENTATION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49A_STAGE_A2_SIDECAR_PACKAGING_CORRECTION.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49B_STAGE_A2_ARCH_REVIEW_R1.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49C_STAGE_A2_ARCH_REVIEW_R2.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49D_STAGE_A2_ARCH_REVIEW_R3.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49E_STAGE_A2_ACCEPTANCE.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49F_STAGE_A2_COMMIT_PUSH_TZ.md
```

Generated files не имеют diff и не должны появиться в commit.

## 9. Следующий шаг

Выполнить только `49F_STAGE_A2_COMMIT_PUSH_TZ.md`.

После успешного push:

- проверить exact origin SHA и clean tracked worktree;
- Stage A2 считается завершённым;
- `50_STAGE_B_REAL_HORIZONS_ACTIONS_FRONTEND_TZ.md` можно запускать только
  отдельной следующей командой после post-push audit.
