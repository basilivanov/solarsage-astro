# Stage B4.W2 acceptance — isolated build cleanup, exact commit and push

Дата: 2026-07-12  
Ветка: `preview/solarsage-v2-human-first-navigator-ux`  
Базовый SHA: `c0c86c540a1d8f77b282ff21705758c8594d5a6e`  
Предыдущие ТЗ: `91`–`95`  
Статус: **ARCHITECT ACCEPTED — AUTHORIZED CLEANUP + ONE COMMIT + PUSH**

## 1. Решение архитектора

B4.W2 принята по runtime, UI contract, tests и GRACE comments.

Независимые проверки архитектора после R4:

~~~text
targeted Vitest: 2 files / 43 tests PASS
typecheck: PASS
full Vitest: 96 files / 1023 tests PASS
guardrails:prod: PASS
isolated Next build: PASS
git diff --check: PASS
generated contracts diff: EMPTY
index: EMPTY
GRACE gate: only accepted unrelated baseline SyntaxError at scripts/grace_front_lint.py:588
~~~

Isolated build был намеренно запущен архитектором с:

~~~bash
NEXT_DIST_DIR=.next-b4-w2-architect pnpm build
~~~

Next 16 создал только известные generated последствия, которые теперь надо
точно убрать перед commit:

~~~text
M next-env.d.ts
M tsconfig.json
?? .next-b4-w2-architect/
~~~

До build оба tracked файла были clean; это зафиксировано архитектором.

## 2. Роль и ограничения

Ты кодер. Выполни только точный cleanup generated build output, затем stage
закрытого allowlist, один commit и push текущей preview‑ветки.

Не использовать субагентов. Не менять product code/tests/docs. Не начинать
B4.W3, не запускать 3003 и не трогать systemd/nginx/API/auth.

## 3. Точный cleanup isolated build

### 3.1 Удалить только generated dist

Удалить ровно:

~~~text
.next-b4-w2-architect/
~~~

Перед удалением подтвердить, что это directory, созданный указанным isolated
build. Не трогать `.next`, `.next-prod`, `.next-v2-preview` или другие dist.

### 3.2 Восстановить `next-env.d.ts` точным patch

Текущую generated строку:

~~~ts
import "./.next-b4-w2-architect/types/routes.d.ts";
~~~

вернуть в pre-build состояние:

~~~ts
import "./.next/types/routes.d.ts";
~~~

Остальной файл не менять.

### 3.3 Восстановить `tsconfig.json` точным patch

Из `include` удалить только две generated строки:

~~~json
".next-b4-w2-architect/types/**/*.ts",
".next-b4-w2-architect/dev/types/**/*.ts"
~~~

После удаления предыдущая строка
`.next-v2-preview/dev/types/**/*.ts` снова должна быть последней и без
generated trailing entries. Остальной `tsconfig.json` не менять.

Для tracked cleanup использовать точный patch, а не broad checkout/reset.

## 4. Pre-commit proof

После cleanup выполнить:

~~~bash
git diff --check
git diff --name-only
git diff --cached --name-only
git status --short --branch
git diff -- next-env.d.ts tsconfig.json
git diff -- packages/contracts/_generated.ts packages/contracts/_generated.zod.ts packages/contracts/openapi.json
test ! -e .next-b4-w2-architect
~~~

Ожидания:

- `next-env.d.ts` и `tsconfig.json` clean;
- isolated dist отсутствует;
- index пуст;
- generated contracts diff пуст;
- tracked diff — ровно следующие 8 paths:

~~~text
__tests__/components/ConcreteDayAdvice.keyboard.test.tsx
__tests__/components/TodayScreen.v2-downstream.test.tsx
components/today/concrete-day-advice.tsx
components/today/horizon-actions.tsx
components/today/horizon-technique-disclosure.tsx
components/today/today-screen.tsx
components/today/why-expanded.tsx
components/today/why-time-horizon-card.tsx
~~~

- untracked task docs — ровно `91`–`96`;
- известные unrelated untracked paths остаются untouched:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

Любое другое tracked изменение — blocker, commit не делать.

## 5. Exact stage allowlist

Stage ровно 14 paths: 8 implementation/test paths выше плюс 6 task docs:

~~~text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/91_STAGE_B4_W2_FINAL_HUMAN_FIRST_UX_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/92_STAGE_B4_W2_ARCH_REVIEW_R1_COMPLETENESS_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/93_STAGE_B4_W2_ARCH_REVIEW_R2_PROOF_TRUTH_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/94_STAGE_B4_W2_ARCH_REVIEW_R3_FINAL_CONTRACT_CLEANUP_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/95_STAGE_B4_W2_ARCH_REVIEW_R4_CARD_COPY_ORDER_INVARIANT_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/96_STAGE_B4_W2_ACCEPTANCE_BUILD_CLEANUP_COMMIT_PUSH_TZ.md
~~~

Не использовать `git add .`, `git add -A` или directory-wide add.

После stage доказать:

~~~bash
git diff --cached --name-only
git diff --cached --check
git status --short --branch
~~~

Cached list должна быть exact 14 paths, ничего больше.

## 6. Commit и push

Сделать ровно один commit:

~~~text
feat(today): finish human-first horizon experience
~~~

Затем push только текущей ветки:

~~~text
preview/solarsage-v2-human-first-navigator-ux
~~~

Не force-push, не rebase, не merge, не push `main`.

## 7. Post-push proof

~~~bash
git branch --show-current
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git log -1 --oneline
git status --short --branch
git diff HEAD^ --name-only
git diff --cached --name-only
test ! -e .next-b4-w2-architect
~~~

Ожидания:

- branch exact preview branch;
- local HEAD == origin preview SHA;
- last commit subject exact;
- commit contains exact 14 paths;
- tracked tree и index clean;
- status содержит только пять frozen unrelated untracked paths;
- B4.W3/3003 не начаты.

## 8. Запрещено

- любые runtime/test/doc изменения кроме точного generated cleanup;
- paths вне exact 14 commit allowlist;
- коммитить `.next*`, frozen unrelated paths или generated build edits;
- менять generated contracts;
- запускать новые модели/сессии;
- subagents;
- merge/rebase/force-push/main deploy;
- B4.W3, preview 3003, systemd/nginx/API/auth changes.

## 9. Callback

~~~text
READY_FOR_ARCH_REVIEW_STAGE_B4_W2_PUSHED
isolated_dist_removed: YES
next_env_restored: YES
tsconfig_restored: YES
staged_paths: EXACT_14
commit_sha: <sha>
commit_subject: feat(today): finish human-first horizon experience
commit_paths: EXACT_14
push_branch: preview/solarsage-v2-human-first-navigator-ux
local_origin_equal: YES
tracked_tree: CLEAN
index: EMPTY
generated_diff: EMPTY
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

После callback остановиться.
