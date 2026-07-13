# Stage 2.W3B3 — semantic/today integration MyPy correction

Дата: `2026-07-13`
Branch: `preview/solarsage-v2-human-first-navigator-ux`
Parent master:
`127_STAGE_2_CORRECTIVE_RELEASE_MAIN_DEPLOY_WAVE_MASTER.md`.
Required predecessor:
`159_STAGE_2_W3B2_PURE_SELECTION_GUIDANCE_MYPY_TZ.md` must be architect-
accepted, committed and pushed first.

Статус: **PREPARED W3B3 — NOT AUTHORIZED UNTIL ARCHITECT SENDS THIS PATH AFTER W3B2 PUSH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Goal and entry baseline

W3B3 owns the final feature-added MyPy diagnostics after W3B2:

```text
app/services/semantic_v2_service.py    2
app/services/today_service.py          8
                                        --
total                                  10
```

Expected entry state after accepted W3B2:

```text
global diagnostics                  90
global failing paths                13
W3B3 diagnostics                    10
W3B3 failing paths                   2
legacy diagnostics                  80
legacy failing paths                11
```

W3B3 goal:

1. remove the exact ten semantic/today integration diagnostics;
2. make the two changed service paths GRACE-clean;
3. remove the duplicate `ContentAccessState` Python class so access and Today
   use one source of truth with identical wire schema;
4. preserve API JSON, selection behavior, cache identity, horizon integration,
   LLM prompt content and runtime flags.

Expected exit:

```text
global diagnostics                  80
global failing paths                11
all 19 feature-added W3B paths       0
legacy diagnostics                  80 unchanged
```

No staging, commit or push before separate architect review.

## 2. Authorization gate

This document is traceability only until all are true:

```text
W3B2 accepted/pushed                       yes
local/tracking/remote feature              equal accepted W3B2 SHA
tracked worktree/index                     clean/empty
architect explicitly sends this path       yes
```

Before authorization, do not edit any W3B3 path.

## 3. Exact edit allowlist

After explicit authorization, edit only:

```text
apps/api/app/schemas/today.py
apps/api/app/services/semantic_v2_service.py
apps/api/app/services/today_service.py
```

Do not edit `schemas/access.py`: it remains the canonical existing definition
that `today.py` will re-export.

Do not edit tests, LLM service, API routes, clients, DB models, contracts,
generated files, config, sidecar or frontend.

No `git add`, commit or push. Do not start W3C/final RC/main/deploy.

## 4. Absolute constraints

- No `Any` addition/widening, cast, ignore, `noqa`, MyPy config/plugin change
  or schema weakening.
- No public JSON field/literal/optionality change.
- No contract-version or generated-artifact edit.
- No cache-key/version/flag/selection logic change.
- No LLM prompt/copy/model/provider change.
- No sidecar request value fallback that changes a valid profile request.
- Keep fail-loud V2 and shadow fail-open behavior unchanged.
- Preserve every existing test selector and frontend contract.
- Add truthful GRACE comments/markers where explicitly required; comments must
  not hide runtime changes.
- No formatter or unrelated cleanup.

## 5. `semantic_v2_service.py` — local identity and full GRACE contract

### 5.1. Two MyPy diagnostics

The function-scoped local `key` is first inferred as target identity tuple and
then reused as a canon-version string.

Rename locals only:

```text
grouping loop target tuple:
  key -> target_identity

canon version overlay loop:
  key, value -> canon_key, canon_value
```

Update exact references in their own blocks. Preserve grouping keys, dict
order, membership check, string conversion and audit result exactly.

Do not add annotations/casts and do not change the accepted nine-key canon
overlay policy.

### 5.2. Required module contract/map

The touched file currently lacks a GRACE module contract/map. Add, without
runtime changes:

```text
START_MODULE_CONTRACT: M-SEMANTIC-V2-SERVICE
START_MODULE_MAP: M-SEMANTIC-V2-SERVICE
```

The truthful contract must state:

- purpose: deterministic Today V2 semantic/audit construction plus LLM
  evidence packet;
- inputs: activation/scoring/horizons/audit/contexts;
- outputs: TodayV2Block, sphere evidence, redacted structured packet;
- dependencies: version/canon services and typed schemas;
- side effects: canon bundle reads during service construction only;
- emitted logs: none;
- privacy invariant: no raw profile/session/token data;
- failure policy: Pydantic/canon errors propagate.

Module map public entrypoints:

```text
get_target_label
get_target_spheres
SemanticV2Service.build_v2_block
SemanticV2Service.get_evidence_for_sphere
SemanticV2Service.build_llm_evidence_packet
```

Use semantic blocks that match existing file regions; do not reorder code just
to fit the map.

### 5.3. Exact five missing function contracts

Add paired unique contracts to exactly:

```text
get_target_label
get_target_spheres
SemanticV2Service.build_v2_block.sort_key
SemanticV2Service.get_evidence_for_sphere
SemanticV2Service.build_llm_evidence_packet
```

Suggested unique IDs:

```text
F-M-SEMANTIC-V2-SERVICE.get_target_label
F-M-SEMANTIC-V2-SERVICE.get_target_spheres
F-M-SEMANTIC-V2-SERVICE.SemanticV2Service.build_v2_block.sort_key
F-M-SEMANTIC-V2-SERVICE.SemanticV2Service.get_evidence_for_sphere
F-M-SEMANTIC-V2-SERVICE.SemanticV2Service.build_llm_evidence_packet
```

Each contract must contain purpose, inputs, returns, side_effects,
emitted_logs, error_behavior and truthfully describe the existing body.

Do not alter the already accepted contract ID/body for `build_v2_block`.

Required final GRACE result: this file clean.

## 6. `schemas/today.py` — single ContentAccessState source and marker repair

### 6.1. Remove duplicate Python type definition

`schemas/access.py` and `schemas/today.py` currently define structurally
identical classes with the same wire name. This causes incompatible Python
nominal types even though OpenAPI already exposes one identical schema.

In `today.py`:

1. import and re-export:

```python
from .access import ContentAccessReason, ContentAccessState
```

2. remove only the local duplicate `ContentAccessReason` alias and local
   `ContentAccessState` class;
3. keep `TodayPayload.access` referencing the imported class;
4. update module contract/map wording from "local" definition to canonical
   re-export/consumption from `schemas.access`;
5. preserve the public import path `app.schemas.today.ContentAccessState` and
   `app.schemas.__init__` exports;
6. require `app.schemas.today.ContentAccessState is
   app.schemas.access.ContentAccessState` in review evidence.

Do not modify `schemas/access.py` or any field/literal/default. Generated
OpenAPI/TS/Zod artifacts must remain byte-identical after regeneration.

### 6.2. Existing unmatched block marker

The file has `END_BLOCK: TODAY_READ_MODELS` without its opener. Insert exactly:

```text
# START_BLOCK: TODAY_READ_MODELS
```

immediately before `DayChartHouse`. Do not move classes.

Required final GRACE result: `schemas/today.py` clean.

## 7. `today_service.py` — exact eight integration fixes

### 7.1. Canonical default access state

Replace the invalid alias-heavy construction:

```python
ContentAccessState(
    state="full",
    reason="cached_prefetch",
    referralDaysLeft=None,
    subscriptionActive=None,
    accessUntil=None,
)
```

with the canonical valid model construction:

```python
ContentAccessState(state="full")
```

Rationale:

- `cached_prefetch` is not a public `ContentAccessReason` and currently raises
  Pydantic ValidationError if this branch executes;
- all optional fields already default to `None`;
- full access with null commercial metadata is the existing preview/access
  contract.

Do not add `cached_prefetch` to the public enum.

This removes three call-arg diagnostics and fixes a real dormant runtime bug.

### 7.2. Cached payload access identity

After `today.py` re-exports the canonical access model, keep:

```python
cached.access = access_state
```

unchanged. The assignment must become type-correct because both sides now use
the same class. Do not serialize/reparse/copy the model.

### 7.3. Validated birth identity narrowing

`NatalContextService.get_or_build_natal_context` validates required profile
fields before returning. Immediately after that successful call:

1. copy `profile.birthday` and `profile.birth_tz` into clearly named locals;
2. guard the impossible `None` state with a compact programming-invariant
   failure that contains no PII;
3. use those narrowed locals for `birth_date.isoformat()` and
   `birth_tz=...` in the activation-layer request.

Do not use cast, ignore, `or "UTC"`, server timezone or a fake birth date.
Valid-profile request values must remain byte-identical.

The existing coordinate-specific 409 check and NatalContextService profile
validation order remain unchanged.

This removes the birthday union and birth-tz argument diagnostics.

### 7.4. LLM semantic-layer boundary

`LLMService.generate_notes` currently accepts the serialized dict form and its
helper already supports it. At this one call, pass:

```python
semantic_layer.model_dump()
```

Do not change `LLMService`, the generated semantic content, prompt text or the
`semantic_layer` object used by later pipeline stages.

### 7.5. Horizon audit union annotation

Import `TodayV2HorizonPipelineAudit` and declare the branch result before the
built/unavailable conditional:

```python
horizon_pipeline_audit: TodayV2HorizonPipelineAudit
```

Keep both existing constructors, status/reason/count fields and downstream
call unchanged. No cast or common base-class weakening.

Required final GRACE result: `today_service.py` remains clean and at or below
the repository 1000-line limit.

## 8. Accepted pre-W3B3 source hashes

These hashes describe the state before W3B2 and are inventory references. At
actual W3B3 authorization, architect will amend/confirm any path changed by an
accepted dependency wave:

```text
9aa339148b43b8fa3040f069898a4f1f7f23a9eb9f3c503a4ccdfd9d22556dc5  apps/api/app/services/semantic_v2_service.py
d90c0b9bc3df24721d9d939afe05f2e56bfc3327d2418aa129fb904e3fe04a27  apps/api/app/services/today_service.py
b73f7f3745f2a7efd7866855ddb9a0fc44c32831224c45fe787cc43fc8b782bd  apps/api/app/schemas/today.py
b1c68018aeb14084b41f51ecb30e354f63c0515d9dc1110ede1021810e491ebf  apps/api/app/schemas/access.py  # must remain byte-frozen
```

## 9. Mandatory preflight after authorization

1. completely read `127`, `159`, the W3B2 acceptance document, and `160`;
2. prove W3B2 accepted/pushed and HEAD = tracking = remote feature;
3. prove main/origin-main unchanged;
4. prove tracked worktree/index clean and only frozen groups plus architect
   docs untracked;
5. run cold MyPy and prove expected 90/13, exact W3B3 10/2;
6. hash exact three edit files and frozen `schemas/access.py`;
7. run Ruff on three edit paths;
8. record current GRACE baselines exactly:
   - `today_service.py` clean;
   - `today.py` exact one unmatched read-model block;
   - `semantic_v2_service.py` exact missing module/map plus five contracts;
9. run targeted suite from section 11 and require 226 PASS;
10. prove contracts/runtime/ports unchanged.

Stop on mismatch. Never reset, restore, checkout paths, stash, amend or rebase.

## 10. Mandatory static gates

### 10.1. Ruff and GRACE

```bash
apps/api/.venv/bin/python -m ruff check \
  apps/api/app/schemas/today.py \
  apps/api/app/services/semantic_v2_service.py \
  apps/api/app/services/today_service.py

apps/api/.venv/bin/python scripts/test_grace_lint.py
apps/api/.venv/bin/python scripts/grace_lint.py \
  apps/api/app/schemas/today.py \
  apps/api/app/services/semantic_v2_service.py \
  apps/api/app/services/today_service.py
```

Require Ruff zero, GRACE self-tests 13 PASS and exact three files clean.

### 10.2. Cold MyPy

```bash
cd apps/api
set +e
./.venv/bin/mypy app --no-incremental --no-error-summary --show-error-codes \
  > /tmp/stage2-w3b3-mypy-after.log 2>&1
rc=$?
set -e
test "$rc" -eq 1
```

Require exactly:

```text
global diagnostics                  80
global failing paths                11
semantic_v2_service.py               0
today_service.py                     0
all 19 feature W3B paths             0
legacy normalized diagnostics       80 unchanged
new/migrated diagnostics             0
```

## 11. Mandatory regression gates

### 11.1. Targeted semantic/today suite

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_semantic_v2_service.py \
  apps/api/tests/test_today_v2_payload.py \
  apps/api/tests/test_today_horizon_integration_service.py \
  apps/api/tests/test_today_cache_v2_key.py \
  apps/api/tests/test_today_meta_versions.py \
  apps/api/tests/test_day_no_birthday_fallback.py \
  apps/api/tests/test_today_preview_access.py \
  apps/api/tests/test_today_preview_transport.py \
  apps/api/tests/test_contract_registry.py \
  apps/api/tests/test_today_horizons_contract.py \
  -q
```

Require exact 10 files / 226 PASS.

### 11.2. Full API and contracts

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
pnpm contracts:check
pnpm contracts:compat
pnpm contracts:fixture:check
PYTHONPATH=packages/py-contracts \
  apps/api/.venv/bin/python -m pytest packages/py-contracts/tests/ -q
pnpm guardrails:frontend
git diff --check
```

Require API 1405/4, contracts no drift/additive zero breaking, fixture clean,
44 py-contract tests, frontend guard and diff check all green.

Additionally prove after `contracts:check`:

```text
packages/contracts/openapi.json       unchanged
packages/contracts/_generated.ts      unchanged
packages/contracts/_generated.zod.ts  unchanged
ContentAccessState schema             one canonical wire schema
```

## 12. Final scope/integrity proof

Before callback require:

```text
tracked changed paths       exact 3
schemas/access.py            byte-identical
today/access class identity  SAME_OBJECT
index                       empty
feature W3B MyPy             zero on all 19 paths
global MyPy                 80 diagnostics / 11 legacy paths
Ruff/GRACE                  green exact 3
tests/contracts             green
runtime/services            unchanged
ports 3003/8001/18092       absent
commit/push                 not performed
main/deploy                 not started
```

Never touch/stage:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 13. Required callback

```text
READY_STAGE_2_W3B3_SEMANTIC_TODAY_MYPY_REVIEW
base_head: <accepted pushed W3B2 sha>
tracked_scope: EXACT_3_FILES
mypy_before: 90_TOTAL_13_PATHS_10_W3B3_ERRORS
mypy_feature_after: PASS_ZERO_19_PATHS
mypy_total_after: 80_DIAGNOSTICS_11_LEGACY_PATHS
mypy_new_migrated: ZERO
content_access_source: SINGLE_CANONICAL_CLASS
content_access_wire: UNCHANGED
semantic_grace: MODULE_MAP_PLUS_5_CONTRACTS
today_schema_grace: PASS
today_service_grace: PASS
runtime_behavior: PRESERVED_PLUS_INVALID_DEFAULT_FIXED
ruff: PASS_ZERO
grace_selftests: 13_PASS
authorized_grace: PASS_3
targeted_tests: 10_FILES_226_PASS
api_full: 1405_PASS_4_SKIP
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
