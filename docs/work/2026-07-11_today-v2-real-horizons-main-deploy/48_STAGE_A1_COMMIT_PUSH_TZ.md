# Stage A1 Commit/Push TZ — accepted shared activation contracts

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Base до commit: `524812fd9764770e247029651924a731addab4af`
Acceptance: `47_STAGE_A1_ACCEPTANCE.md`
Статус: **commit/push authorized exactly as specified below**.

## 0. Режим и запреты

1. Полностью прочитать этот файл и acceptance.
2. Не запускать субагентов или delegated agents.
3. Не менять содержимое product/test/package файлов.
4. Не начинать Stage A2, Stage B или baseline stabilization.
5. Не использовать `git add .`, `git add -A` или wildcard staging.
6. Не включать unrelated paths:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

7. Не делать merge/rebase/squash/amend/force-push и не переключать branch.
8. Не перезапускать systemd/nginx/Docker и не трогать порты.
9. Если exact staged path set отличается от allowlist — снять ошибочные paths
   из index и остановиться с отчётом.

## 1. Preflight

```bash
git branch --show-current
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git diff --check
git diff --cached --name-only
```

Ожидание:

```text
branch = preview/solarsage-v2-human-first-navigator-ux
HEAD = origin feature = 524812fd9764770e247029651924a731addab4af
index empty
```

## 2. Exact commit

Commit message:

```text
refactor(contracts): share activation models
```

Stage только следующие paths, каждый явно:

```text
__tests__/contracts/activation-shared-parity.test.ts
apps/api/app/core/versions.py
apps/api/app/schemas/activation.py
apps/api/pyproject.toml
apps/api/tests/fixtures/contracts/activation-layer-public-camel.json
apps/api/tests/test_today_meta_versions.py
apps/solarsage/pyproject.toml
apps/solarsage/solarsage/api/activation_layer.py
apps/solarsage/solarsage/core/versions.py
apps/solarsage/solarsage/schemas/activation.py
apps/solarsage/tests/test_activation_layer_endpoint.py
apps/solarsage/tests/test_activation_schema.py
packages/py-contracts/README.md
packages/py-contracts/pyproject.toml
packages/py-contracts/solarsage_contracts/__init__.py
packages/py-contracts/solarsage_contracts/activation.py
packages/py-contracts/solarsage_contracts/base.py
packages/py-contracts/solarsage_contracts/py.typed
packages/py-contracts/solarsage_contracts/versions.py
packages/py-contracts/tests/fixtures/activation-layer-snake.json
packages/py-contracts/tests/test_activation_contract.py
packages/py-contracts/tests/test_boundary_configs.py
packages/py-contracts/tests/test_versions.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/46_STAGE_A1_SHARED_MODELS_IMPLEMENTATION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/47_STAGE_A1_ACCEPTANCE.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/48_STAGE_A1_COMMIT_PUSH_TZ.md
```

Перед commit вывести и проверить:

```bash
git diff --cached --name-only
git diff --cached --check
git diff --cached --stat
```

Staged path set должен совпасть с allowlist полностью и точно.

## 3. Post-commit gates

После commit обязательно:

```bash
pnpm contracts:check
npx vitest run __tests__/contracts
npx tsc --noEmit
git diff --name-only
git diff --cached --name-only
git status --short
```

Ожидание:

```text
contracts check: PASS
contract Vitest: 132 passed
typecheck: PASS
tracked worktree: CLEAN
index: EMPTY
unrelated untracked: PRESERVED
```

Если любой gate не проходит — не push, вернуть exact failure.

## 4. Push

```bash
git push origin preview/solarsage-v2-human-first-navigator-ux
```

После push:

```bash
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git status --short --branch
git log -1 --oneline
```

HEAD и origin feature обязаны совпасть. Force push запрещён.

## 5. Callback

```text
PUSHED_STAGE_A1_SHARED_MODELS
branch: preview/solarsage-v2-human-first-navigator-ux
base: 524812fd9764770e247029651924a731addab4af
commit: <sha> refactor(contracts): share activation models
contracts_check: PASS
contract_tests: 132 passed
typecheck: PASS
head: <sha>
origin_feature: <sha>
tracked_worktree: CLEAN
index: EMPTY
unrelated_untracked: PRESERVED <exact list>
push: PASS
```

После callback остановиться. Не начинать Stage A2.
