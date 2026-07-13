# Stage 1.W0 — architect acceptance and exact commit/push checkpoint

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted base: `ae62ad8ced1865cef2b2b1b3a0382d2e06065ce0`
Parents: `104`, `105`
Статус: **AUTHORIZED EXACT COMMIT AND PUSH — NO S1.W1 IMPLEMENTATION**

## 0. Решение архитектора

Stage 1.W0 strict harness принят.

Принятые доказательства:

~~~text
launcher unit: 31 pass
full Vitest: 97 files / 1054 pass
typecheck: pass
prod guard: pass
isolated build: pass; candidate removed
real launcher: root 200; canonical API health 200
strict Chromium: auth/day 200/200; expected today.v1 identity failure
strict mobile iPhone 13 viewport: auth/day 200/200; expected today.v1 identity failure
route interception/mock/18092: zero/absent
next-env final diff: empty
3003/18092 final listeners: absent
index: empty
backend/product/generated/lock/next-config diff: empty
~~~

`pnpm guardrails:frontend` остаётся известным baseline failure:

~~~text
7442 problems = 7399 errors + 43 warnings
~~~

Архитектор независимо подтвердил:

- ошибки идут из уже существующих `.next-prod`, `.next-v2-preview` и старых
  frontend/test/docs файлов;
- current `eslint.config.mjs` не игнорирует эти два generated directory;
- `eslint.config.mjs` и guard script не изменены относительно accepted base;
- новые launcher/unit/E2E paths в текущем ESLint perimeter ignored и добавляют
  `0 errors`;
- исправление общего baseline lint не входит в W0 и не разрешается этой волной.

GRACE gate также остаётся прежним unrelated baseline:

~~~text
scripts/grace_front_lint.py:588
SyntaxError: from __future__ imports must occur at the beginning of the file
~~~

Эти два baseline не разрешают менять дополнительные файлы.

## 1. Exact staged paths

Разрешено staged ровно **17** путей: 7 implementation + 10 architect docs.

### 1.1 Implementation — exact 7

~~~text
.gitignore
package.json
tsconfig.json
scripts/preview-v2-real.mjs
__tests__/scripts/preview-v2-real.test.ts
e2e/real-v2-preview.spec.ts
e2e/README.md
~~~

### 1.2 Architect docs — exact 10

~~~text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/97_STAGE_B4_W3_REAL_PREVIEW_NO_INTERCEPTION_E2E_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/98_STAGE_B4_W3_ARCH_REVIEW_R1_REAL_PROOF_AND_LIFECYCLE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/99_STAGE_B4_W3_R1A_NO_CHECKOUT_RESTORE_INTENTIONAL_CONFIG_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/100_STAGE_B4_W3_BLOCKED_CANONICAL_API_V1_DIAGNOSIS_AND_OPTIONS.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/101_TWO_STAGE_COMPLETION_MASTER_PLAN.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/102_STAGE_1_SAFE_DEV_SCOPED_V2_PREVIEW_MASTER_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/103_STAGE_2_PREVIEW_TO_MAIN_PRODUCTION_MASTER_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/104_STAGE_1_W0_STRICT_HARNESS_STABILIZATION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/105_STAGE_1_W0_ARCH_ERRATA_NEXT16_DEV_TYPES_AND_CLEANUP_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/106_STAGE_1_W0_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
~~~

## 2. Frozen/unrelated paths

Не добавлять и не менять:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

Не добавлять никакие `test-results`, build dist или временные логи.

## 3. Pre-stage assertions

До `git add` проверить:

~~~text
branch exact preview/solarsage-v2-human-first-navigator-ux
HEAD exact ae62ad8ced1865cef2b2b1b3a0382d2e06065ce0
origin branch exact same SHA
index empty
3003/18092 absent
next-env.d.ts diff empty
.next-v2-real-preview absent
.next-stage1-w0-build absent
git diff --check pass
~~~

Если любое условие не выполнено — не commit/push, вернуть callback архитектору.

## 4. Exact staging procedure

Использовать один explicit `git add --` со всеми 17 путями из раздела 1.

После staging получить sorted staged list и сравнить с exact sorted expected
list. Должно быть ровно 17 строк, без missing/extra.

Дополнительно доказать:

~~~text
git diff --cached --check => pass
git diff --cached -- next-env.d.ts => empty
git diff --cached -- pnpm-lock.yaml next.config.mjs apps/api apps/solarsage packages/contracts e2e/mock-visual => empty
~~~

Запрещены broad `git add .`, `git add -A`, checkout/restore/reset и любые
file rewrites.

## 5. Commit and push

Exact commit subject:

~~~text
test(preview): harden real v2 harness
~~~

После commit:

- получить exact commit SHA;
- проверить commit path list — ровно 17 путей;
- проверить commit subject;
- push только текущую ветку:

~~~text
git push origin preview/solarsage-v2-human-first-navigator-ux
~~~

После push:

~~~text
local HEAD == origin branch == new SHA
index empty
tracked worktree clean
remaining untracked only frozen/unrelated roots listed in section 2
3003/18092 absent
next-env diff empty
~~~

## 6. Запрет следующей волны

Не начинать S1.W1, backend selection, marker, cache или service restart. После
callback остановиться и ждать нового ТЗ архитектора.

## 7. Callback

~~~text
PUSHED_STAGE_1_W0
base_sha: ae62ad8ced1865cef2b2b1b3a0382d2e06065ce0
commit_sha: <exact>
commit_subject: test(preview): harden real v2 harness
commit_paths: EXACT_17
implementation_paths: EXACT_7
architect_docs: EXACT_10_97_TO_106
staged_diff_check: PASS
next_env_final_diff: EMPTY
forbidden_commit_paths: ZERO
push: PASS
local_origin_equal: PASS_<sha>
index: EMPTY
tracked_worktree: CLEAN
ports_3003_18092: ABSENT
unrelated_paths: UNTOUCHED_UNTRACKED
services_env_main: UNCHANGED
next_wave: NOT_STARTED
~~~

После callback остановиться.
