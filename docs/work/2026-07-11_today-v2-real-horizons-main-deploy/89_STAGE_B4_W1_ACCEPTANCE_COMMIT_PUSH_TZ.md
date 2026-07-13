# Stage B4.W1 acceptance — exact commit and push

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Ожидаемый parent SHA: `1a944717efa7a70124f81cb950992998491bf72e`
Статус: **ARCHITECT ACCEPTED — AUTHORIZE ONE COMMIT AND PUSH**

## 1. Accepted evidence

Архитектор независимо подтвердил:

~~~text
targeted B4.W1:            57 passed
full frontend Vitest:      96 files / 1012 passed
generated contract tests:  21 passed
typecheck:                 PASS
production guard:          PASS
git diff check:            PASS
generated contract diff:   EMPTY
index:                     EMPTY
~~~

GRACE full gate имеет единственный unrelated baseline SyntaxError в
`scripts/grace_front_lint.py:588`; этот path не входит в commit и не исправляется.

## 2. Exact commit allowlist

Закоммитить ровно девять paths:

~~~text
lib/contracts/today.ts
lib/adapters/today-payload.ts
components/today/today-screen.tsx
components/today/why-expanded.tsx
__tests__/lib/adapt-payload.test.ts
__tests__/components/TodayScreen.v2-downstream.test.tsx
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/86_STAGE_B4_W1_GENERATED_WIRE_STEADY_STATE_CONSUMER_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/87_STAGE_B4_W1_ARCH_REVIEW_R1_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/88_STAGE_B4_W1_ARCH_REVIEW_R2_FINAL_CLEANUP_TZ.md
~~~

Этот acceptance-документ `89` также должен быть включён в тот же commit, поэтому
финальный staged allowlist составляет **10 exact paths**: девять выше + сам `89`.

Ничего иного не stage.

## 3. Pre-commit proof

~~~bash
git branch --show-current
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git diff --cached --name-only
git diff --check
git diff -- packages/contracts/_generated.ts packages/contracts/_generated.zod.ts packages/contracts/openapi.json
git status --short --branch
~~~

Требования:

- branch exact;
- HEAD/origin exact parent SHA;
- index пуст до staging;
- generated diff пуст;
- tracked diff только шесть implementation/test files;
- untracked docs только `86`–`89` плюс известные unrelated paths.

## 4. Stage, verify, commit

Использовать явный `git add -- <10 exact paths>`, без `git add .`, `-A` и
wildcards.

После staging вывести:

~~~bash
git diff --cached --name-only
git diff --cached --stat
git diff --cached --check
~~~

Если список не равен exact 10 paths — ничего не коммитить, очистить только
ошибочно staged paths безопасным non-destructive способом и вернуть blocker.

Commit subject:

~~~text
feat(today): consume backend horizon wire identity
~~~

Создать ровно один commit.

## 5. Push and post-proof

Push только текущей ветки:

~~~bash
git push origin preview/solarsage-v2-human-first-navigator-ux
~~~

Затем доказать:

~~~bash
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git show --name-status --format=fuller HEAD
git diff --cached --name-only
git status --short --branch
~~~

Ожидается:

- local/origin новый SHA совпадают;
- commit subject exact;
- commit содержит exact 10 paths;
- index пуст;
- tracked tree чист;
- остаются только известные unrelated untracked paths:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

## 6. Запрещено

- менять содержимое accepted файлов;
- повторно запускать/исправлять код;
- stage unrelated paths;
- amend/rebase/squash;
- switch main;
- services/3003/systemd/nginx/env;
- начинать B4.W2/W3;
- создавать больше одного commit.

## 7. Callback

~~~text
PUSHED_STAGE_B4_W1
parent_sha: 1a944717efa7a70124f81cb950992998491bf72e
commit_sha: <sha>
origin_sha: <same sha>
commit_subject: feat(today): consume backend horizon wire identity
staged_paths: 10 EXACT_ALLOWLIST
full_vitest: 96 files / 1012 passed
typecheck: PASS
generated_contract_tests: 21 PASS
prod_guard: PASS
generated_diff: EMPTY
tracked_tree: CLEAN
index: EMPTY
unrelated_paths: UNTOUCHED
main: UNCHANGED
services: UNCHANGED
next_wave: NOT_STARTED
~~~

После callback остановиться.
