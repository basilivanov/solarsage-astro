# Stage 2.W3B1 R1 — downstream type-precision reclassification

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`24efa83eb91a36c6419cf174c8d24ee95870086b`
Parent: `155_STAGE_2_W3B1_SCHEMA_MYPY_CORRECTION_TZ.md`.

Статус: **ARCHITECT REVIEW RESOLUTION — FREEZE CODE, COMPLETE GATES, NO COMMIT/PUSH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Architect finding

The W3B1 implementation is structurally correct:

```text
exact W3B1 files                 4
owned MyPy diagnostics before  16
owned MyPy diagnostics after    0
Ruff                            PASS_ZERO
runtime/schema behavior         unchanged by reviewed diff
index                           empty
```

The explicit `HorizonThemeKey` Literal repaired a previously invalid alias.
That increased type precision and revealed five real call-site diagnostics in
three files already assigned to planned W3B2:

```text
app/services/horizon_guidance_builders.py:292  themes.get(horizon_theme: str)
app/services/horizon_guidance_builders.py:414  themes.get(horizon_theme: str)
app/services/horizon_guidance_service.py:138   themes[horizon_theme: str]
app/services/horizon_guidance_service.py:316   themes.get(primary_theme: str)
app/services/horizon_claim_policy.py:189       themes.get(horizon_theme: str)
```

These are not runtime regressions and must not be hidden by weakening
`HorizonThemeKey` back to `str`, using casts/ignores, or changing typed canon
dictionaries. W3B2 will narrow/propagate the theme-key type at the service
boundaries.

The section-10 expectation in doc 155 is therefore amended for this exact
implementation only.

## 2. Accepted frozen source state

Freeze these exact hashes:

```text
22c72c6f48dec30bc930800fad2901eb337e62599a97bb005979c99429e51f65  apps/api/app/schemas/today_horizons.py
db6454a999d55990c5b53c828e7669b098ef9b026c8260558607aefe28a2088f  apps/api/app/schemas/horizon_canon.py
b8c56a2187ab7de3eac587ab1920e534a5117df2a07f2cfc1e892840b0c21672  apps/api/app/schemas/horizon_content_canon.py
82b486fb69422f3400aad6c608aaab931139145add4f9e55713701d18d35cff6  apps/api/app/schemas/horizon_content_canon_types.py
```

Coder must not edit any source, test, config or doc file. Architect-owned doc
156 is expected untracked and must remain untouched/un-staged.

No service-file edit is authorized. No W3B2 implementation is authorized.

## 3. Revised exact MyPy acceptance

Run from `apps/api` with a cold/no-incremental proof:

```bash
set +e
./.venv/bin/mypy app --no-incremental --no-error-summary --show-error-codes \
  > /tmp/stage2-w3b1-r1-mypy.log 2>&1
rc=$?
set -e
test "$rc" -eq 1
```

Require exactly:

```text
total diagnostics             118
total failing paths            21
exact four W3B1 paths           0
new precision diagnostics       5
new precision paths             3
new precision path set          horizon_guidance_builders.py,
                                horizon_guidance_service.py,
                                horizon_claim_policy.py
all five owned by future W3B2   yes
```

No new diagnostic may exist outside those exact five. Existing W3B2/W3B3 and
legacy errors remain diagnostic evidence, not authority to edit them.

## 4. Mandatory completion gates

### 4.1. Frozen hashes and exact scope

Recheck the four hashes from section 2, then require:

```text
tracked diff paths    exact four schema files
index                 empty
doc 156               untracked architect-owned
other untracked       exact five frozen groups
```

### 4.2. Ruff, GRACE and targeted tests

Run the exact commands from doc 155 section 11. Require:

```text
Ruff                  PASS_ZERO
GRACE self-tests      13_PASS
authorized GRACE      PASS_4
targeted tests        7_FILES_139_PASS
```

### 4.3. Full API and contracts

Run the exact commands from doc 155 section 12. Require:

```text
API full              1405_PASS_4_SKIP
contracts check       PASS_NO_DRIFT
contracts compat      ADDITIVE_ZERO_BREAKING
fixture check         PASS
py-contracts          44_PASS
frontend guard        PASS
git diff check        PASS_ZERO
```

### 4.4. Runtime and git integrity

Require HEAD/tracking/remote still equal base SHA, main/origin-main untouched,
services unchanged and ports `3003`, `8001`, `18092` absent.

No staging, commit or push.

## 5. Required callback

```text
READY_STAGE_2_W3B1_R1_SCHEMA_REVIEW
base_head: 24efa83eb91a36c6419cf174c8d24ee95870086b
tracked_scope: EXACT_4_SCHEMA_FILES
frozen_hashes: PASS_4
mypy_w3b1: PASS_ZERO
mypy_total: 118_DIAGNOSTICS_21_PATHS
reclassified_downstream: EXACT_5_ERRORS_3_W3B2_PATHS
mypy_unexpected_new_errors: ZERO
ruff: PASS_ZERO
grace_selftests: 13_PASS
authorized_grace: PASS_4
targeted_tests: 7_FILES_139_PASS
api_full: 1405_PASS_4_SKIP
contracts_check_compat_fixture: PASS
py_contracts: 44_PASS
frontend_guard: PASS
git_diff_check: PASS_ZERO
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
main_deploy: NOT_STARTED
```

Then stop. W3B2/W3B3/W3C remain forbidden.
