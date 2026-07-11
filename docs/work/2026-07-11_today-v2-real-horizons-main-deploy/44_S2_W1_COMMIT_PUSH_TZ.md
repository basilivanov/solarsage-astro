# S2.W1 Commit/Push TZ — accepted real timing and architecture plans

Дата: 2026-07-12  
Ветка: `preview/solarsage-v2-human-first-navigator-ux`  
Base до commit: `1f8fc1e2e0e7ddcb96706a1934f65eb5ea4f20e4`  
Acceptance: `43_S2_W1_ACCEPTANCE.md`  
Статус: **commit/push authorized exactly as specified below**.

## 0. Запреты

1. Не менять содержимое product/test/generated файлов.
2. Не начинать Stage A/B implementation.
3. Не исправлять baseline API failures.
4. Не использовать `git add .`, `git add -A` или wildcard staging.
5. Не включать unrelated paths:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

6. Не делать merge/rebase/squash/amend/force-push.
7. Не переключать branch.
8. Если staged path set отличается от allowlist — выполнить
   `git restore --staged <wrong-path>` и остановиться с отчётом.

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
HEAD = origin feature = 1f8fc1e2...
index empty
```

## 2. Commit 1 — accepted S2.W1 implementation

Message:

```text
feat(activation): add real timing windows
```

Stage только следующие paths:

```text
apps/api/app/core/versions.py
apps/api/app/schemas/activation.py
apps/api/tests/test_activation_contracts.py
apps/api/tests/test_activation_layer_contract.py
apps/api/tests/test_activation_layer_firdar.py
apps/api/tests/test_activation_layer_profections.py
apps/api/tests/test_activation_layer_returns.py
apps/api/tests/test_activation_layer_transits.py
apps/api/tests/test_today_cache_v2_key.py
apps/api/tests/test_today_meta_versions.py
apps/solarsage/solarsage/api/activation_layer.py
apps/solarsage/solarsage/core/versions.py
apps/solarsage/solarsage/schemas/activation.py
apps/solarsage/solarsage/services/activation_builder.py
apps/solarsage/solarsage/services/firdar.py
apps/solarsage/solarsage/services/returns.py
apps/solarsage/solarsage/services/transit_timing.py
apps/solarsage/solarsage/utils/ephemeris.py
apps/solarsage/tests/test_activation_layer_endpoint.py
apps/solarsage/tests/test_activation_transits.py
apps/solarsage/tests/test_firdar.py
apps/solarsage/tests/test_lunar_return.py
apps/solarsage/tests/test_profections.py
apps/solarsage/tests/test_solar_return.py
apps/solarsage/tests/test_transit_timing.py
packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/36_S2_W1_REAL_TIMING_IMPLEMENTATION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/37_S2_W1_ARCH_GUIDANCE_R1.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/38_S2_W1_ARCH_GUIDANCE_R2_VERSION_FIXTURES.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/39_S2_W1_ARCH_REVIEW_R1.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/41_S2_W1_ARCH_GUIDANCE_R3_CONTRACT_DRIFT_GATE.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/42_S2_W1_ARCH_REVIEW_R2.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/43_S2_W1_ACCEPTANCE.md
```

Перед commit вывести и проверить:

```bash
git diff --cached --name-only
git diff --cached --check
git diff --cached --stat
```

Если exact path set совпадает — commit.

После commit 1 обязательно:

```bash
pnpm contracts:check
```

Результат обязан быть `0`. Если нет — не продолжать к commit 2/push.

## 3. Commit 2 — accepted architecture documentation

Message:

```text
docs(architecture): plan shared contracts and human horizons
```

Stage только:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/00_MASTER_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/10_STAGE_1_CONTRACT_FOUNDATION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/20_STAGE_2_REAL_HORIZONS_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/40_STAGE_A_SHARED_PYTHON_CONTRACT_PLATFORM_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/44_S2_W1_COMMIT_PUSH_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/50_STAGE_B_REAL_HORIZONS_ACTIONS_FRONTEND_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/90_MAIN_RELEASE_DEPLOY_TZ.md
```

Снова проверить exact staged set, `--cached --check`, stat и только затем
commit.

## 4. Cleanliness before push

После двух commits:

```bash
git diff --name-only
git diff --cached --name-only
git status --short
pnpm contracts:check
git log -2 --oneline
```

Допустимы только unrelated untracked paths из section 0. Tracked worktree и
index должны быть чистыми.

## 5. Push

```bash
git push origin preview/solarsage-v2-human-first-navigator-ux
```

Запрещён force push.

После push:

```bash
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git status --short --branch
```

HEAD и origin feature обязаны совпасть.

## 6. Callback

```text
PUSHED_S2_W1_REAL_TIMING
branch: preview/solarsage-v2-human-first-navigator-ux
commit_1: <sha> feat(activation): add real timing windows
contracts_check_after_commit_1: PASS
commit_2: <sha> docs(architecture): plan shared contracts and human horizons
contracts_check_final: PASS
head: <sha>
origin_feature: <sha>
tracked_worktree: CLEAN
index: EMPTY
unrelated_untracked: PRESERVED <exact list>
push: PASS
```

После callback остановиться. Не начинать Stage A.
