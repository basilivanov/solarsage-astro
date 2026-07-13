# Stage 2.W2C-1 — architect acceptance, exact commit and push

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`d50f0268efe6c5c9ea88e7c6bc1cc12f85fdfc6e`
Accepted implementation documents:

- `141_STAGE_2_W2C_GRACE_ACTIVE_SLICE_SUBWAVE_MASTER_TZ.md`;
- `142_STAGE_2_W2C1_APP_PAGES_TRUTHFUL_GRACE_PREAMBLES_TZ.md`;
- `143_STAGE_2_W2C1_R1_SELF_CONTAINED_GRACE_NEGATIVE_HARNESS_TZ.md`;
- `144_STAGE_2_W2C1_R2_EXACT_ESLINT_NEGATIVE_RULE_ASSERTIONS_TZ.md`.

Prepared next-wave document, included for traceability but not execution:

- `145_STAGE_2_W2C2_GRACE_COMPONENTS_TRUTHFUL_PREAMBLES_TZ.md`.

Статус: **ARCHITECT ACCEPTED — AUTHORIZED EXACT COMMIT/PUSH ONLY**

## 1. Acceptance boundary

Этот документ разрешает только exact staging, one commit, post-commit gates и
normal push уже принятой W2C-1 реализации.

Никакие source/tooling/docs edits в acceptance-wave не разрешены. Если
architect callback перед отправкой этого пути не подтвердил R2, документ не
выполнять.

Architect independently reviewed the exact diff and reran the strict harness,
comment-only/runtime-suffix proofs, GRACE checks, ESLint, typecheck, targeted
Vitest, exact marker parser, aggregate frontend diagnostic, refs, services and
ports. Эти личные проверки архитектора являются основанием acceptance.

Во время coder R2 профиль `Coding-Leader` один раз создал delegated review
task. После обнаружения task был явно отменён, его approval и любые результаты
полностью исключены из evidence. В этой и всех последующих волнах запрещены
subagents, delegation, `delegate_*`, background coding/review tasks и ссылка на
их результаты.

Accepted implementation scope:

```text
14 app/(grace) page files — truthful comment-only module preambles
1 scripts/grace/check-negative.sh — self-contained exact-reason harness
```

Accepted semantic evidence must include:

```text
app executable suffixes                  byte-identical 14/14
app changes                              comments only
module contract/map IDs                 unique and paired 14/14
authorized-path GRACE                    PASS 14/14
negative clean baseline                 PASS
marker negative reasons                 GRC001/GRC004/GRC030/GRC031
ESLint negative reasons                 exact two grace/* rule IDs
ESLint negative exit contract           exactly 1
Parsing error acceptance                forbidden
generic any-nonzero helper              absent
negative total                          6 PASS / 0 FAIL
GRACE linter self-tests                 11 PASS
frontend ESLint                         zero errors / zero warnings
typecheck                               PASS
targeted Vitest                         5 files / 31 tests PASS
remaining GRACE                         32 violations / 27 failing
remaining green/checked                 20 / 47
remaining prefixes                      components/grace, lib/api, lib/grace
git diff check                          PASS
runtime/services                        unchanged
ports 3003/8001/18092                   absent
```

## 2. Mandatory preflight

До staging:

1. полностью прочитать 141–146;
2. `git fetch origin` без merge/rebase;
3. доказать branch =
   `preview/solarsage-v2-human-first-navigator-ux`;
4. доказать local HEAD = tracking = remote feature =
   `d50f0268efe6c5c9ea88e7c6bc1cc12f85fdfc6e`;
5. доказать `main` = `origin/main` =
   `c9bc36bd9a947566eddb1ffcf5617967c7412676` и main является ancestor HEAD;
6. доказать пустой index;
7. доказать tracked diff exact 15 implementation paths из section 3;
8. повторить source inspection R2 helper и подтвердить exact exit/rule/parser
   semantics;
9. повторить hashes 14 pages и comment-only/runtime-suffix equivalence;
10. доказать, что docs 141–146 — ровно шесть task docs, ожидающих staging;
11. доказать отсутствие иных task-generated untracked paths;
12. доказать, что только пять frozen unrelated untracked paths остаются вне
    task scope;
13. доказать runtime/services/ports unchanged.

Stop on any mismatch. Never reset, rebase, stash, amend or force.
Все preflight, staging, gates и push исполнитель выполняет лично, без
subagents/delegation.

## 3. Exact implementation paths

```text
app/(grace)/calendar/page.tsx
app/(grace)/chat/page.tsx
app/(grace)/checkin/page.tsx
app/(grace)/debug/page.tsx
app/(grace)/onboarding/page.tsx
app/(grace)/page.tsx
app/(grace)/profile/page.tsx
app/(grace)/readings/horary/[id]/page.tsx
app/(grace)/readings/horary/page.tsx
app/(grace)/readings/natal/[id]/page.tsx
app/(grace)/readings/natal/generating/page.tsx
app/(grace)/readings/natal/page.tsx
app/(grace)/readings/page.tsx
app/(grace)/today/page.tsx
scripts/grace/check-negative.sh
```

Tracked implementation count: exactly 15.

## 4. Exact staging set

Stage only exact 21 paths:

```text
15 implementation paths from section 3
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/141_STAGE_2_W2C_GRACE_ACTIVE_SLICE_SUBWAVE_MASTER_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/142_STAGE_2_W2C1_APP_PAGES_TRUTHFUL_GRACE_PREAMBLES_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/143_STAGE_2_W2C1_R1_SELF_CONTAINED_GRACE_NEGATIVE_HARNESS_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/144_STAGE_2_W2C1_R2_EXACT_ESLINT_NEGATIVE_RULE_ASSERTIONS_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/145_STAGE_2_W2C2_GRACE_COMPONENTS_TRUTHFUL_PREAMBLES_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/146_STAGE_2_W2C1_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

Use only explicit file arguments. Forbidden:

```text
git add .
git add -A
git add app
git add docs/work/...
```

Before commit require:

```text
staged count                       exactly 21
staged set                         exact list above
unstaged tracked diff              empty
cached executable app changes      none
cached diff check                  PASS
frozen paths in index              zero
unrelated paths in index           zero
```

If a docs EOF/trailing-whitespace problem appears, stop for architect; do not
edit docs as coder.

## 5. Exact commit

Create exactly one normal commit:

```text
chore(grace): migrate app contracts and harden checks
```

No amend, fixup, rebase or second commit.

After commit, before push, prove:

```text
HEAD parent = d50f0268efe6c5c9ea88e7c6bc1cc12f85fdfc6e
HEAD subject exact
HEAD changed paths exact 21
tracked worktree clean
index empty
```

## 6. Mandatory post-commit gates

### 6.1. Strict negative harness

```bash
bash -n scripts/grace/check-negative.sh
bash scripts/grace/check-negative.sh
```

Require exact semantic result:

```text
clean baseline PASS
GRC001/GRC004/GRC030/GRC031 exact
grace/contracts-only-import exact
grace/no-redeclare-contract-types exact
pass=6 fail=0
```

### 6.2. GRACE linter and accepted app slice

```bash
python3 scripts/test_grace_front_lint.py
python3 scripts/grace_front_lint.py \
  'app/(grace)/calendar/page.tsx' \
  'app/(grace)/chat/page.tsx' \
  'app/(grace)/checkin/page.tsx' \
  'app/(grace)/debug/page.tsx' \
  'app/(grace)/onboarding/page.tsx' \
  'app/(grace)/page.tsx' \
  'app/(grace)/profile/page.tsx' \
  'app/(grace)/readings/horary/[id]/page.tsx' \
  'app/(grace)/readings/horary/page.tsx' \
  'app/(grace)/readings/natal/[id]/page.tsx' \
  'app/(grace)/readings/natal/generating/page.tsx' \
  'app/(grace)/readings/natal/page.tsx' \
  'app/(grace)/readings/page.tsx' \
  'app/(grace)/today/page.tsx'
```

Require: 11 self-tests PASS; 14 authorized files clean.

### 6.3. Frontend static and targeted regression gates

```bash
pnpm lint
pnpm typecheck
npx vitest run \
  __tests__/app/checkin-page.test.tsx \
  __tests__/app/today-redirect.test.ts \
  __tests__/horary/horary-error-state.test.tsx \
  __tests__/natal/natal-component-states.test.tsx \
  __tests__/natal/natal-no-english.test.tsx
```

Require:

```text
ESLint             zero errors / zero warnings
typecheck          PASS
targeted Vitest    5 files / 31 tests PASS
```

### 6.4. Exact remaining marker diagnostic

Run full marker gate and parse its complete captured output. Require exactly:

```text
violations=32
failing_paths=27
green_paths=20
checked_paths=47
app/(grace) failing paths=0
remaining prefixes=components/grace_AND_lib/api_AND_lib/grace_ONLY
```

Then run `pnpm guardrails:frontend` diagnostically. Non-zero is accepted only
when ESLint/typecheck/negative sections passed and the sole failure is the same
exact marker remainder above.

Finally:

```bash
git diff --check origin/main...HEAD
```

Require PASS_ZERO.

Comment-only W2C-1 не требует повторного production build. Full Vitest и build
будут обязательны в final release candidate; не расширять эту commit-only
волну самостоятельно.

## 7. Normal push and equality

После всех post-commit gates:

1. выполнить normal push текущей feature branch;
2. never force and never set a different upstream;
3. доказать local HEAD = tracking = remote feature SHA;
4. доказать tracked worktree clean and index empty;
5. доказать, что вне git остаются только пять frozen unrelated paths;
6. доказать `main`/`origin/main` untouched;
7. доказать runtime/env/systemd/nginx untouched;
8. доказать listeners `3003`, `8001`, `18092` absent.

Не начинать W2C-2 до callback и нового architect message. Наличие doc 145 в
commit не является авторизацией исполнения.

## 8. Frozen unrelated paths

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 9. Required callback

```text
PUSHED_STAGE_2_W2C1_APP_CONTRACTS
commit: <sha> chore(grace): migrate app contracts and harden checks
staged_scope: EXACT_21
implementation_scope: EXACT_15
app_comment_only_equivalence: PASS_14
negative_harness: 6_PASS_0_FAIL_EXACT_REASONS
grace_linter_self_tests: 11_PASS
authorized_paths_grace: PASS_14
eslint: PASS_ZERO_ERRORS_ZERO_WARNINGS
typecheck: PASS
targeted_tests: 5_FILES_31_PASS
remaining_grace: 32_VIOLATIONS_27_FAILING_20_GREEN_47_CHECKED
remaining_prefixes: COMPONENTS_GRACE_LIB_API_LIB_GRACE_ONLY
feature_diff_check: PASS_ZERO
head_tracking_remote: EQUAL
tracked_index: CLEAN_EMPTY
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
main_deploy: NOT_STARTED
```

Затем остановиться.
