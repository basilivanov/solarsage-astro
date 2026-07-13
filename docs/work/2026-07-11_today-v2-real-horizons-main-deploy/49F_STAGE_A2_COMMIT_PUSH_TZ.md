# Stage A2 Commit/Push TZ — exact accepted scope only

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Acceptance: `49E_STAGE_A2_ACCEPTANCE.md`
Expected pre-commit HEAD/origin: `6d0da88a815b1fa17d4e511b3bcf076d130bdc0a`
Статус: **COMMIT_AND_PUSH_STAGE_A2_ONLY**.

## 0. Запреты

1. Полностью прочитать acceptance и этот файл.
2. Не запускать субагентов.
3. Не менять code/docs во время commit wave.
4. Не использовать `git add -A`, `git add .` или broad pathspec.
5. Не stage/commit unrelated untracked paths.
6. Не amend/rebase/reset/force-push.
7. Не менять `main`, systemd, nginx, env или запущенные preview services.
8. Не начинать Stage B после push.

## 1. Preflight

```bash
git branch --show-current
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git diff --cached --name-only
git diff --check
```

Ожидание:

```text
branch: preview/solarsage-v2-human-first-navigator-ux
HEAD: 6d0da88a815b1fa17d4e511b3bcf076d130bdc0a
origin feature: same
index: empty
diff check: PASS
```

Если HEAD/origin отличаются или index не пуст — остановиться без commit.

## 2. Exact staging

Stage только этот список:

```bash
git add -- \
  .github/workflows/ci.yml \
  .dockerignore \
  apps/api/Dockerfile \
  apps/api/app/schemas/contract_registry.py \
  apps/api/tests/test_contract_registry.py \
  apps/solarsage/Dockerfile \
  apps/solarsage/pyproject.toml \
  docker-compose.yml \
  docker-compose.prod.yml \
  package.json \
  packages/py-contracts/README.md \
  scripts/contracts/check.sh \
  scripts/contracts/check_compat.py \
  scripts/contracts/export_openapi.py \
  scripts/contracts/sync.sh \
  scripts/contracts/test_check_compat.py \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49_STAGE_A2_CONTRACT_AUTOMATION_IMPLEMENTATION_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49A_STAGE_A2_SIDECAR_PACKAGING_CORRECTION.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49B_STAGE_A2_ARCH_REVIEW_R1.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49C_STAGE_A2_ARCH_REVIEW_R2.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49D_STAGE_A2_ARCH_REVIEW_R3.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49E_STAGE_A2_ACCEPTANCE.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/49F_STAGE_A2_COMMIT_PUSH_TZ.md
```

Категорически не stage:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Generated contracts также не stage: у них zero diff.

## 3. Staged audit

```bash
git diff --cached --name-only
git diff --cached --check
git status --short
```

`git diff --cached --name-only` обязан содержать ровно 23 paths из section 2,
без generated files и unrelated paths.

Если есть лишний path — остановиться. Не использовать reset/restore; вернуть
architect exact staged list для решения.

## 4. Commit

Один commit:

```bash
git commit -m "feat(contracts): automate compatibility and service builds"
```

После commit:

```bash
git show --stat --oneline --decorate HEAD
git diff HEAD^ --name-only
git status --short
```

Commit path list обязан совпасть с exact 23 paths.

## 5. Push

Push только текущую feature branch без force:

```bash
git push origin HEAD:preview/solarsage-v2-human-first-navigator-ux
```

После push:

```bash
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git status --short --branch
git diff --cached --name-only
```

Требования:

- local HEAD == origin feature;
- tracked worktree clean;
- index empty;
- unrelated untracked paths всё ещё присутствуют и не вошли в commit;
- no force push;
- main untouched;
- preview ports/services untouched.

## 6. Callback

```text
READY_STAGE_A2_PUSHED
branch: preview/solarsage-v2-human-first-navigator-ux
commit: <sha>
subject: feat(contracts): automate compatibility and service builds
commit_paths: 23 EXACT
local_head: <sha>
origin_feature: <sha>
tracked_worktree: CLEAN
index: EMPTY
unrelated_untracked: PRESERVED
generated_contracts_in_commit: NO
main_changed: NO
force_push: NO
preview_services_changed: NO
```

После callback остановиться. Stage B не начинать.
