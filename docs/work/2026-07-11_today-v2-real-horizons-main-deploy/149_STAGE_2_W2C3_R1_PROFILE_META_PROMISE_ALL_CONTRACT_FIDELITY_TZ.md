# Stage 2.W2C-3 R1 — profile-meta Promise.all contract fidelity

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`6c93217fa6fe778388d735659db4f7ae5b894700`
Parents:

- `141_STAGE_2_W2C_GRACE_ACTIVE_SLICE_SUBWAVE_MASTER_TZ.md`;
- `147_STAGE_2_W2C3_API_FACADES_TRUTHFUL_GRACE_PREAMBLES_TZ.md`.

Статус: **MANDATORY ARCHITECT REVIEW REPAIR — NO COMMIT/PUSH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Accepted and frozen W2C-3 state

Architect accepts and freezes:

```text
exact API implementation scope          13 files
comment-only/runtime suffix proof       PASS 13/13
module IDs                              unique and paired 13/13
authorized GRACE                        PASS 13/13
GRACE self-tests                        11 PASS
negative harness                        6/0 exact reasons
ESLint/typecheck                        PASS
targeted regression                     13 files / 104 tests PASS
remaining marker                        3/3/44/47, lib/grace only
index                                   empty
runtime/services/ports                  unchanged
```

Заморозить все 12 other API files побайтно. В `lib/api/profile-meta.ts`
заморозить runtime suffix и все preamble строки, кроме exact three lines below.

## 2. Review finding

Current preamble says:

```text
Successful endpoint data can populate independently of the other endpoint.
```

and map descriptions say:

```text
QUOTA_MAPPING: apply successful quota fields independently.
REFERRAL_MAPPING: apply successful referral fields independently.
```

This overstates the runtime contract. The implementation uses:

```ts
const [quotaRes, referralRes] = await Promise.all([fetch(...), fetch(...)])
```

Consequences:

- when both fetch promises resolve, each response is conditionally applied by
  its own `.ok`, so one non-ok HTTP response does not block the other;
- when either fetch promise rejects, `Promise.all` rejects and control enters
  the single catch before either successful sibling response is applied;
- the function then returns defaults, not the successful sibling payload.

The preamble must document this actual behavior. Runtime must not be changed to
`Promise.allSettled`; that would be a different, unauthorized feature change.

## 3. Architect-owned docs state

Architect has already corrected the corresponding specification sentence in:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/147_STAGE_2_W2C3_API_FACADES_TRUTHFUL_GRACE_PREAMBLES_TZ.md
```

Coder must not edit, stage or restore that doc. It is an expected architect
tracked diff during R1.

## 4. Exact coder edit scope

Edit only:

```text
lib/api/profile-meta.ts
```

Do not edit the other 12 facades, docs, tests, config, scripts or runtime.
No staging/commit/push. W2C-4 forbidden.

## 5. Exact required three-line correction

Replace the invariant line with this exact meaning, wrapped as normal `//`
comment lines if needed:

```text
When both fetch promises resolve, each response is applied only if its own
response.ok is true; a rejected promise sends the whole Promise.all to the
catch fallback.
```

Replace the two semantic map descriptions with:

```text
QUOTA_MAPPING: apply quota fields only when the quota response is ok.
REFERRAL_MAPPING: apply referral fields only when the referral response is ok.
```

No other preamble wording change.

## 6. Mandatory equivalence proof

Before edit hash all 13 current API files. After edit require:

```text
other 12 hashes                    unchanged
profile-meta runtime suffix        unchanged
profile-meta changed lines         exact three comment meanings only
profile-meta imports/exports       unchanged
profile-meta module ID             unchanged and paired
Promise.all runtime                unchanged
all URLs/defaults/error behavior   unchanged
index                              empty
```

The combined tracked diff may contain only:

```text
13 accepted API facade files
architect-owned doc 147
```

Within the R1 delta relative to the accepted callback, only
`lib/api/profile-meta.ts` may change.

## 7. Required gates

```bash
python3 scripts/test_grace_front_lint.py
python3 scripts/grace_front_lint.py \
  lib/api/access.ts \
  lib/api/calendar.ts \
  lib/api/chat.ts \
  lib/api/checkin.ts \
  lib/api/cities.ts \
  lib/api/config.ts \
  lib/api/dev-auth-guard.ts \
  lib/api/horary.ts \
  lib/api/natal.ts \
  lib/api/profile-meta.ts \
  lib/api/profile.ts \
  lib/api/readings.ts \
  lib/api/today.ts
bash scripts/grace/check-negative.sh
pnpm lint
pnpm typecheck
npx vitest run __tests__/api/profile-meta.test.ts
```

Then full marker must remain exactly:

```text
3 violations
3 failing paths
44 green paths
47 checked paths
remaining prefix lib/grace only
```

`pnpm guardrails:frontend` remains expected-nonzero only for the same final
W2C-4 marker remainder. Run `git diff --check` and final scope/runtime audit.

## 8. Required callback

```text
READY_STAGE_2_W2C3_R1_PROFILE_META_CONTRACT_REVIEW
r1_coder_scope: lib/api/profile-meta.ts_ONLY
architect_doc_147: UNTOUCHED_BY_CODER
other_api_hashes: UNCHANGED_12
runtime_suffix_hashes: UNCHANGED_13
profile_meta_delta: EXACT_THREE_COMMENT_MEANINGS
promise_all_runtime: UNCHANGED
authorized_paths_grace: PASS_13
grace_linter_self_tests: 11_PASS
negative_harness: 6_PASS_0_FAIL_EXACT_REASONS
eslint: PASS_ZERO
typecheck: PASS
targeted_profile_meta: PASS_<EXACT_TEST_COUNT>
remaining_grace: 3_VIOLATIONS_3_FAILING_44_GREEN_47_CHECKED
remaining_prefixes: LIB_GRACE_ONLY
guardrails_frontend: EXPECTED_FINAL_MARKER_REMAINDER_ONLY
git_diff_check: PASS
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
```

Then stop. W2C-4 remains forbidden.
