# Stage B3.W2 R1 — coder restart: preserve WIP, finish gates and callback

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted parent HEAD/origin: `ecae4d0ff95bf29953fbb6957e48c38a7d22e198`
Parent documents: `75`, `78`, `79`
Статус: **CONTINUE EXISTING WIP; FINAL VERIFICATION ONLY; NO COMMIT/PUSH**

## 1. Why this restart exists

Предыдущая coder session была случайно заменена новым UI-сеансом после почти
полного выполнения `79`. Все изменения находятся в общей рабочей копии и не
потеряны.

Не начинать W2 заново. Не переписывать уже реализованные tests или production
boundary без воспроизводимого failing gate. Задача этого restart — проверить
актуальный WIP, закончить только недостающие gates и вернуть exact callback.

## 2. Mandatory first actions

1. Полностью прочитать этот файл.
2. Прочитать `79` sections 10–13 и при необходимости соответствующие gate
   команды из `78 §17`.
3. Выполнить:

~~~bash
git status --short
git diff --stat
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git diff --cached --quiet
~~~

Ожидается:

- local/origin HEAD =
  `ecae4d0ff95bf29953fbb6957e48c38a7d22e198`;
- index empty;
- W2/R1 tracked diff и два untracked implementation/test files сохранены;
- unrelated `.grace/`, `artifacts/design/`, `skills/`, `grace.db` и frozen plan
  не тронуты и не staged.

## 3. Already implemented — verify, do not redesign

Текущий WIP уже содержит:

- exact-nine SemanticV2 canon boundary;
- unknown scoring canon filtering;
- stale scoring horizon canon protection;
- incomplete scoring-map proof and input immutability proof;
- current/previous/mismatch/missing-audit full TodayPayload matrix;
- internal/public horizon reason parity;
- 4/4 horizon canon cache-hash invalidation;
- current invalid cache-row miss proofs;
- mapping failure exact sanitized log and pipeline call count `0`;
- strengthened built/unavailable/error log assertions;
- TodayService exact activation/scoring/natal/advice identity reuse proof;
- current `today.v2.1/frontend=3` audit coverage;
- previous `today.v2/frontend=2` audit compatibility coverage;
- requested GRACE function contracts/module contract updates;
- defensive current-V2 wording.

Known last green evidence:

~~~text
focused backend: 167 passed
integration service: 9 passed
cache tests: 23 passed
semantic downstream mapping: 6 passed
TodayService sentinel identity targeted test: 1 passed
owned GRACE: 3/3 PASS
contract Vitest focused: 21 passed
contract sync Vitest: 137 passed
compatibility: breakingChanges=0 overrideUsed=false
fixture normalization: PASS
~~~

Do not reduce those counts or remove coverage merely to shorten the diff.

## 4. Generated/fixture hashes must remain exact

The previous session ran `pnpm contracts:sync` after R1 and obtained:

~~~text
packages/contracts/openapi.json
  917a04222aeeb793bd9ce6831d2ecfdcde8666663b6542ed6d1693028daba3dd

packages/contracts/_generated.ts
  e081d9dcf1ba19290c6489b52e6b01815d5e915474aab1d28569475304608a30

packages/contracts/_generated.zod.ts
  6fc7665fe0058803eef838fb9f3b84119b97695c857153d5984966666f4be78e

e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
  6100ddc601ae06a903ca038f975818b2f0ccec12e228ab2c86993f218e2bfa4c
~~~

Run generation/check once more and prove all four hashes stay exact. If any
hash changes, stop and report the reason; do not hand-edit generated files.

## 5. Required gates

### 5.1 Focused backend

Run the exact focused command from `79/78`. Expected minimum:

~~~text
167 passed
~~~

Any failure is a blocker.

### 5.2 Horizon regression

Run the complete eleven-file horizon regression command from `78 §17`.
Expected current count is `242 passed`; record the actual count.

### 5.3 Request-local reuse regression

Run the three-file request reuse command from `78 §17`.
Expected current count is `15 passed`; record the actual count.

### 5.4 Contracts

Run:

~~~bash
pnpm contracts:sync
pnpm contracts:fixture:check
npx vitest run \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts
python3 scripts/contracts/check_compat.py --json --json-output /tmp/stage-b3-w2-r1-contract-compat.json
npx tsc --noEmit
~~~

Prove:

- generated backend contract tests pass;
- all contract Vitest suites pass;
- focused Vitest = `21 passed`;
- `breakingChanges=0`;
- `overrideUsed=false`;
- fixture normalized;
- hashes equal section 4.

### 5.5 Python diagnostics

Run compileall for all changed production Python modules and new service.

### 5.6 GRACE

Run:

~~~bash
python3 scripts/grace_lint.py \
  apps/api/app/services/today_horizon_integration_service.py \
  apps/api/tests/test_today_horizon_integration_service.py \
  apps/api/app/services/today_service.py
~~~

Expected `3 file(s) clean`.

Also source-check the exact paired contracts named in `79 §8`; do not claim
legacy modules are globally GRACE-clean.

### 5.7 Full API suite — authoritative invocation is from repository root

Important: do **not** run the authoritative proof after `cd apps/api`.
`test_horizon_pipeline_service.py` contains a repo-relative source guard and
produces a false seventh `FileNotFoundError` solely under that working
directory.

Run from `/opt/solarsage-astro`:

~~~bash
apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
~~~

Expected current result is approximately:

~~~text
1242 passed, 5 skipped, exact 6 frozen failures
~~~

Counts may differ only if pytest accounting changes, but failure identity must
be exactly these six:

1. `test_calendar_status_cache_duplicate_rereads_winning_row`;
2. `test_semantic_v2_service_no_convergence`;
3. `test_semantic_v2_service_with_convergence`;
4. `test_audit_canon_versions_only_contains_strings`;
5. `test_techniques_list_is_sorted`;
6. `test_today_payload_v2_block_included_when_flag_enabled`.

Do not change those tests in this restart. They belong to B3.W3. Any seventh
failure from repository-root invocation is a blocker.

## 6. Static and scope audit

Run and prove:

~~~bash
git diff --check
git diff --cached --quiet
git status --short
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
~~~

Also prove:

- exact 22 tracked changed paths already accepted by W2/R1;
- exact W2 untracked production/test files;
- architect docs `78`, `79`, `79A` are untracked and not edited by coder;
- no tracked/untracked path outside the accepted W2 set except the frozen
  unrelated roots already present before W2;
- no added production line over 140 chars;
- change-size budgets from `78 §16` still pass;
- no forbidden imports in the integration service;
- `next-env.d.ts` has no diff;
- no staged files;
- no commit/push.

Do not print every file under `.grace/`; summarize that frozen unrelated root
as one preserved prefix.

## 7. Forbidden actions

- no implementation redesign;
- no broad cleanup;
- no editing tests outside W2/R1 allowlist;
- no fixing the six B3.W3 baseline failures;
- no `git add`;
- no commit;
- no push;
- no branch switch;
- no B3.W3;
- no B4/frontend/3003;
- no main/deploy/systemd/nginx;
- no subagents/delegation.

## 8. Exact callback

~~~text
READY_STAGE_B3_W2_R1_REVIEW
accepted_w1_sha: ecae4d0ff95bf29953fbb6957e48c38a7d22e198 local/origin unchanged
canon_boundary: PASS exact 9; unknown dropped; horizon keys current; core overlay only
public_identity_matrix: PASS current/previous/mismatch/missing-audit
reason_parity: PASS internal minus selected equals public unavailable
cache_horizon_invalidation: PASS 4/4 keys alter both hashes
cache_invalid_current_rows: PASS miss without exception
mapping_failure_log: PASS exact sanitized event and pipeline calls=0
runtime_wiring_exact_reuse: PASS activation/scoring/natal/advice identities once
audit_identity_coverage: PASS current fresh + previous compatible
grace_changed_boundaries: PASS named contracts present
generated_contract_hashes: UNCHANGED exact section-4 hashes
fixture_hash: UNCHANGED normalized
focused_backend: <count> PASS
horizon_regression: <count> PASS
request_reuse: <count> PASS
contract_vitest: <count> PASS
contract_compat: breakingChanges=0 overrideUsed=false
full_api_root: <passed> passed, <skipped> skipped, exact 6 frozen failures only
git_diff_check: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback.
