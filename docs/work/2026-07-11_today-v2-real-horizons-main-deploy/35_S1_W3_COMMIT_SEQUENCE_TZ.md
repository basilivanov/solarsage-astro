# S1.W3 Commit Sequence ТЗ — baseline repair, then contract foundation

Дата: 2026-07-11
Исполнитель: coder в `tmux astro:0.0`
Архитектор: только review/acceptance

## 1. Цель

Сделать и push два строго разделённых commit в текущую preview branch:

1. visual baseline repair без code changes;
2. S1.W3 contract foundation без binary changes.

Main, production services и другие branches не менять.

## 2. Исходное состояние

Перед началом ожидается:

```text
staged: 30 S1.W3 paths
unstaged: ровно два accepted full-page PNG
untracked task docs:
  docs/work/2026-07-11_preview-visible-sphere-status-labels/02_VISUAL_BASELINE_REPAIR_ACCEPTANCE.md
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/34_S1_W3_ACCEPTANCE.md
```

Unrelated paths не трогать:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 3. Commit A — visual baseline repair

Сначала очистить только index, не worktree:

```bash
git restore --staged -- .
```

Эта команда не должна менять содержимое файлов в worktree.

Stage только три path:

```bash
git add \
  docs/work/2026-07-11_preview-visible-sphere-status-labels/02_VISUAL_BASELINE_REPAIR_ACCEPTANCE.md \
  docs/work/2026-07-11_solarsage-v2-three-horizon-why-preview/assets/03-full-day-three-horizons-mobile.png \
  e2e/mock-visual/day-v2.spec.ts-snapshots/03-full-day-three-horizons-mobile-mobile-linux.png
```

Перед commit доказать:

```bash
git diff --cached --name-only
git diff --cached --check
git status --short --branch
```

`git diff --cached --name-only` обязан содержать ровно перечисленные три path.

Commit:

```bash
git commit -m "test(today): align accepted sphere status visual baseline"
git push origin preview/solarsage-v2-human-first-navigator-ux
```

Зафиксировать local SHA и origin SHA; они должны совпасть.

## 4. Commit B — S1.W3 contract foundation

После успешного push Commit A stage только следующий allowlist:

```bash
git add \
  .github/workflows/ci.yml \
  __tests__/app/day-page.test.tsx \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts \
  __tests__/guardrails/preview-isolation.test.ts \
  __tests__/lib/presentation/today-v2.test.ts \
  apps/api/app/schemas/activation.py \
  apps/api/tests/test_activation_contracts.py \
  apps/api/tests/test_today_fixture_contract.py \
  apps/solarsage/solarsage/schemas/activation.py \
  apps/solarsage/tests/test_activation_schema.py \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/26_S1_W3_ARCHITECTURE_AMENDMENT.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/27_S1_W3_IMPLEMENTATION_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/28_S1_W3_IMPORT_BOOTSTRAP_GUIDANCE.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/29_S1_W3_DAY_PAGE_TEST_GUIDANCE.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/30_S1_W3_ARCH_REVIEW_R1.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/31_S1_W3_ARCH_REVIEW_R2.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/32_S1_W3_ARCH_REVIEW_R3.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/33_S1_W3_ARCH_REVIEW_R4.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/34_S1_W3_ACCEPTANCE.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/35_S1_W3_COMMIT_SEQUENCE_TZ.md \
  e2e/mock-visual/fixtures/day-v2-2026-07-08.ts \
  e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json \
  lib/presentation/today-v2.ts \
  package.json \
  packages/contracts/README.md \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts \
  scripts/contracts/check.sh \
  scripts/contracts/normalize_today_fixture.py \
  scripts/contracts/today_fixture.sh
```

Ожидается ровно `32` staged paths: прежние 30 плюс acceptance и это commit ТЗ.

Перед commit:

```bash
git diff --cached --name-only | wc -l
git diff --cached --name-status
git diff --cached --check
git diff --cached --name-only | rg '\.(png|jpg|jpeg|webp)$' || true
git status --short --branch
```

Требования:

```text
count: 32
binary matches: 0
unrelated staged: 0
```

Commit/push:

```bash
git commit -m "test(contracts): prove today v2 fixture round trip"
git push origin preview/solarsage-v2-human-first-navigator-ux
```

## 5. Финальная проверка

```bash
git rev-parse HEAD
git ls-remote origin refs/heads/preview/solarsage-v2-human-first-navigator-ux
git log -2 --oneline
git status --short --branch
```

После двух commit допустимы только заранее существовавшие unrelated untracked
paths. Tracked modifications/staged paths отсутствуют.

Не начинать S2.W1 в этом turn. Вернуть callback и остановиться.

## 6. Callback

```text
PUSHED_BASELINE_AND_S1_W3
baseline_commit: <sha>
baseline_subject: test(today): align accepted sphere status visual baseline
baseline_paths: 3
s1_w3_commit: <sha>
s1_w3_subject: test(contracts): prove today v2 fixture round trip
s1_w3_paths: 32
origin_sha: <sha equal s1_w3_commit>
binary_paths_in_s1_w3: 0
unrelated_paths_committed: 0
remaining_status: <only allowed unrelated untracked>
main_changed: NO
s2_w1_started: NO
```
