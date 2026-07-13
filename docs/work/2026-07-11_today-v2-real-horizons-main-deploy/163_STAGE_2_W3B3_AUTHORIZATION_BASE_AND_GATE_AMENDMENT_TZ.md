# Stage 2.W3B3 — authorization, exact base and gate amendment

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`a0646a0b2d02f3a40c209a45286cb60d0d846a91`
Implementation specification:
`160_STAGE_2_W3B3_SEMANTIC_TODAY_INTEGRATION_MYPY_TZ.md`.
Accepted predecessor:
`162_STAGE_2_W3B2_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md`.

Статус: **W3B3 AUTHORIZED — READ 160 AND THIS AMENDMENT, NO COMMIT/PUSH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Authorization

W3B2 is accepted, committed and pushed:

```text
commit   a0646a0b2d02f3a40c209a45286cb60d0d846a91
subject  refactor(api): type horizon guidance pipeline
local = tracking = remote feature
main/origin-main unchanged
```

Doc 160 is now explicitly authorized with the exact base and amendments in
this document. Read doc 160 completely first, then this document completely.
Where they differ, this document controls only the stated base/count/details.

## 2. Confirmed entry state

Cold MyPy:

```text
global diagnostics                  90
global failing paths                13
W3B3 diagnostics                    10
W3B3 failing paths                   2
legacy diagnostics                  80
legacy failing paths                11
```

Exact W3B3 diagnostics remain byte-for-byte the ten listed in doc 160:

```text
semantic_v2_service.py               2
today_service.py                     8
```

Confirmed hashes:

```text
9aa339148b43b8fa3040f069898a4f1f7f23a9eb9f3c503a4ccdfd9d22556dc5  apps/api/app/services/semantic_v2_service.py
d90c0b9bc3df24721d9d939afe05f2e56bfc3327d2418aa129fb904e3fe04a27  apps/api/app/services/today_service.py
b73f7f3745f2a7efd7866855ddb9a0fc44c32831224c45fe787cc43fc8b782bd  apps/api/app/schemas/today.py
b1c68018aeb14084b41f51ecb30e354f63c0515d9dc1110ede1021810e491ebf  apps/api/app/schemas/access.py
```

`schemas/access.py` remains byte-frozen.

## 3. Exact edit scope

Unchanged from doc 160:

```text
apps/api/app/schemas/today.py
apps/api/app/services/semantic_v2_service.py
apps/api/app/services/today_service.py
```

Edit exact three only. Doc 163 is architect-owned and must remain untracked,
unchanged and un-staged. No test edit is authorized.

## 4. Birth identity invariant — exact implementation detail

Doc 160 section 7.3 is authorized with this exact failure behavior.

Immediately after the successful call:

```python
natal_context = await context_service.get_or_build_natal_context(user_id)
```

bind:

```python
birth_date = profile.birthday
birth_tz = profile.birth_tz
```

Then guard:

```python
if birth_date is None or birth_tz is None:
    raise RuntimeError("validated natal profile is missing birth identity")
```

Why this is truthful: `get_or_build_natal_context` loads the same user profile
and always calls `_validate_profile_completeness` before cache hit or rebuild;
successful return proves both values exist. The guard protects a programming
invariant and contains no PII.

Use the narrowed locals only for:

```text
birth_date=...isoformat()
birth_tz=...
```

in the activation-layer request. Do not alter target timezone or birth-time
fallback.

Update `TodayService.get_today_payload` function-contract `error_behavior` to
mention this compact RuntimeError programming invariant in addition to the
existing HTTP failures. No new log event is required.

## 5. GRACE exact baseline

Before edit require:

```text
today_service.py
  clean

today.py
  exact one GRC004 unmatched END_BLOCK: TODAY_READ_MODELS

semantic_v2_service.py
  GRC020 missing module contract
  GRC021 missing module map
  exact five GRC010 missing function contracts
```

After edit require all three clean plus 13 GRACE self-tests PASS.

## 6. Corrected test-count expectations

W3B2 R1 added one parameterized timing test and changed the full API baseline.
Therefore every `1405 PASS / 4 SKIP` expectation in doc 160 is amended to:

```text
API full   1406 PASS / 4 SKIP
```

The doc-160 targeted W3B3 suite does not include the timing test and remains:

```text
10 files / 226 PASS
```

No test file changes are authorized, so both counts must remain exact.

## 7. Contract identity proof

After replacing the duplicate class in `today.py`, require directly:

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python - <<'PY'
from app.schemas.access import ContentAccessReason as AccessReason
from app.schemas.access import ContentAccessState as AccessState
from app.schemas.today import ContentAccessReason as TodayReason
from app.schemas.today import ContentAccessState as TodayState

assert TodayReason is AccessReason
assert TodayState is AccessState
assert TodayState(state="full").model_dump() == {
    "state": "full",
    "reason": None,
    "referral_days_left": None,
    "subscription_active": None,
    "access_until": None,
}
print("content_access_identity=PASS")
PY
```

`pnpm contracts:check` must produce no tracked generated diff.

## 8. Final required callback

Use doc 160 callback with these exact replacements:

```text
READY_STAGE_2_W3B3_SEMANTIC_TODAY_MYPY_REVIEW
base_head: a0646a0b2d02f3a40c209a45286cb60d0d846a91
tracked_scope: EXACT_3_FILES
mypy_before: 90_TOTAL_13_PATHS_10_W3B3_ERRORS
mypy_feature_after: PASS_ZERO_19_PATHS
mypy_total_after: 80_DIAGNOSTICS_11_LEGACY_PATHS
mypy_new_migrated: ZERO
content_access_source: SINGLE_CANONICAL_CLASS
content_access_identity: SAME_OBJECT
content_access_wire: UNCHANGED
semantic_grace: MODULE_MAP_PLUS_5_CONTRACTS
today_schema_grace: PASS
today_service_grace: PASS
runtime_behavior: PRESERVED_PLUS_INVALID_DEFAULT_FIXED
birth_identity_guard: VALIDATED_PROGRAMMING_INVARIANT
ruff: PASS_ZERO
grace_selftests: 13_PASS
authorized_grace: PASS_3
targeted_tests: 10_FILES_226_PASS
api_full: 1406_PASS_4_SKIP
contracts_check_compat_fixture: PASS_NO_DRIFT
py_contracts: 44_PASS
frontend_guard: PASS
git_diff_check: PASS_ZERO
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
main_deploy: NOT_STARTED
```

Then stop. W3C/final RC/main/deploy remain forbidden.
