# Post-push cleanup TZ — remove accepted-diff trailing whitespace

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Текущий pushed HEAD: `d991423e8c6924b157df592be8de64a90f34593b`
Статус: обязательный mechanical cleanup после нарушенного `--cached --check`.

## 0. Причина и режим

Commit 2 был создан и отправлен, хотя `git diff --cached --check` показал
trailing whitespace. Дополнительная проверка `git show --check` нашла такие же
строки и в commit 1.

Запрещено:

- amend/rebase/reset/force-push;
- менять смысл, слова, код или тестовые assertions;
- начинать Stage A/B;
- включать unrelated untracked paths;
- использовать `git add .` или `git add -A`.

Нужен отдельный третий commit, состоящий только из удаления конечных spaces/tabs
и этого audit/TZ файла.

## 1. Exact cleanup paths

Удалить только конечные spaces/tabs в следующих существующих файлах:

```text
apps/solarsage/solarsage/services/transit_timing.py
apps/solarsage/tests/test_transit_timing.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/36_S2_W1_REAL_TIMING_IMPLEMENTATION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/37_S2_W1_ARCH_GUIDANCE_R1.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/38_S2_W1_ARCH_GUIDANCE_R2_VERSION_FIXTURES.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/39_S2_W1_ARCH_REVIEW_R1.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/40_STAGE_A_SHARED_PYTHON_CONTRACT_PLATFORM_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/41_S2_W1_ARCH_GUIDANCE_R3_CONTRACT_DRIFT_GATE.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/42_S2_W1_ARCH_REVIEW_R2.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/43_S2_W1_ACCEPTANCE.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/44_S2_W1_COMMIT_PUSH_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/50_STAGE_B_REAL_HORIZONS_ACTIONS_FRONTEND_TZ.md
```

Допустима одна механическая formatter/sed операция по exact paths. Не применять
её ко всему repository.

## 2. Verification before commit

Проверить:

```bash
rg -n '[ \t]+$' <exact paths>
git diff --check
git diff --word-diff=porcelain -- <exact paths>
```

Ожидание:

- `rg` не находит строк;
- `git diff --check` возвращает 0;
- word diff показывает только удаление whitespace, без изменения слов.

Запустить:

```bash
cd apps/solarsage
venv/bin/python -m pytest tests/test_transit_timing.py -q
cd /opt/solarsage-astro
pnpm contracts:check
```

## 3. Commit

Stage только exact cleanup paths из section 1 плюс:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/45_POST_PUSH_WHITESPACE_CLEANUP_TZ.md
```

Перед commit:

```bash
git diff --cached --name-only
git diff --cached --check
git diff --cached --stat
```

Commit message:

```text
chore: clean timing whitespace
```

## 4. Push and final proof

```bash
git push origin preview/solarsage-v2-human-first-navigator-ux
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git status --short --branch
git show --check --format=oneline HEAD
pnpm contracts:check
```

Допустимы только unrelated untracked paths:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 5. Callback

```text
PUSHED_S2_W1_WHITESPACE_CLEANUP
cleanup_commit: <sha>
transit_timing_tests: PASS
contracts_check: PASS
git_diff_check: PASS
head: <sha>
origin_feature: <sha>
tracked_worktree: CLEAN
index: EMPTY
unrelated_untracked: PRESERVED
push: PASS
```

После callback остановиться.
