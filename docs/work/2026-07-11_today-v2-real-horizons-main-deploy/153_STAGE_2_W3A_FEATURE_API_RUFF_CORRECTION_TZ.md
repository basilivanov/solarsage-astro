# Stage 2.W3A — feature API Ruff correction on exact 19-path scope

Дата: `2026-07-13`
Branch: `preview/solarsage-v2-human-first-navigator-ux`
Parent master:
`127_STAGE_2_CORRECTIVE_RELEASE_MAIN_DEPLOY_WAVE_MASTER.md`.
Predecessor: W2C-4 must be accepted, committed and pushed first.
Evidence:

- `/tmp/stage2-w0-release-blocker-pathsets.txt`;
- `/tmp/stage2-w3a-current-ruff.log`.

Статус: **PREPARED W3A — NOT AUTHORIZED UNTIL ARCHITECT SENDS THIS PATH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Goal and exact baseline

Make Ruff clean on the exact 19 feature-owned API files without changing
public behavior, schemas, fixtures, test assertions or runtime protocols.

Accepted current baseline on the exact allowlist:

```text
Ruff diagnostics     97
failing paths        19
E401                  1
E402                  4
E701                 25
E702                 19
E731                  2
E741                  1
F401                 41
F541                  3
F811                  1
```

Required result:

```text
Ruff diagnostics      0
failing paths         0
full API pytest       green
contracts             green/no drift
```

This is implementation-only. No staging, commit or push until separate
architect review/acceptance.

## 2. Exact edit allowlist

```text
apps/api/app/core/versions.py
apps/api/app/schemas/horizon_content_canon.py
apps/api/app/schemas/horizon_content_canon_types.py
apps/api/app/services/horizon_claim_policy.py
apps/api/app/services/horizon_claim_validator.py
apps/api/app/services/horizon_guidance_formatter.py
apps/api/app/services/horizon_guidance_service.py
apps/api/app/services/personal_fact_pack_service.py
apps/api/tests/_horizon_guidance_testkit.py
apps/api/tests/test_horizon_actions_canon.py
apps/api/tests/test_horizon_canon_service.py
apps/api/tests/test_horizon_claim_validator.py
apps/api/tests/test_horizon_coverage.py
apps/api/tests/test_horizon_guidance_service.py
apps/api/tests/test_horizon_pipeline_service.py
apps/api/tests/test_horizon_selection_service.py
apps/api/tests/test_real_today_v2_api_proof.py
apps/api/tests/test_today_fixture_contract.py
apps/api/tests/test_today_horizon_integration_service.py
```

Edit exact 19 only. Do not edit MyPy-only paths, sidecar, shared contracts,
canons/YAML, generated contracts, configs, linters, manifests, docs, frontend
or deployment files.

No `git add`, commit or push. Do not start W3B/W3C/final RC/main/deploy.

## 3. Global correction constraints

- Do not change any public constant value, model field, alias, validation
  branch, exception code/message, fixture data, assertion, parametrization,
  patch target, request shape or expected outcome.
- Do not weaken Ruff through config changes, per-file ignores, blanket `noqa`,
  rule disable comments or `type: ignore`.
- Do not run `ruff --fix`, `ruff --unsafe-fixes`, Black, isort or a formatter.
  The two intentional re-export cases below would be broken by blind F401
  deletion. Apply reviewed edits manually.
- A targeted `# noqa: E402` is authorized only on the exact two fixture-test
  imports named in section 6.3 because they intentionally follow repo-root
  `sys.path` bootstrap. No other suppression is authorized.
- Preserve every GRACE header/contract/map/function/block marker and keep their
  facts truthful after formatting.
- Preserve test order and test names. Do not combine, split or delete tests.
- Every test module must remain at or below 700 lines after expansion.
- No raw secret, profile, initData or personal payload may enter logs/evidence.

## 4. Exact diagnostic ownership by path

```text
apps/api/app/core/versions.py                            2 F401
apps/api/app/schemas/horizon_content_canon.py           3 F401 + 1 E731
apps/api/app/schemas/horizon_content_canon_types.py     2 F401
apps/api/app/services/horizon_claim_policy.py           4 F401
apps/api/app/services/horizon_claim_validator.py        2 F401
apps/api/app/services/horizon_guidance_formatter.py     1 F541
apps/api/app/services/horizon_guidance_service.py       1 F401
apps/api/app/services/personal_fact_pack_service.py     1 F401
apps/api/tests/_horizon_guidance_testkit.py              8 F401 + 2 E402 + 1 F811
apps/api/tests/test_horizon_actions_canon.py             1 E731
apps/api/tests/test_horizon_canon_service.py             1 F401
apps/api/tests/test_horizon_claim_validator.py           3 F401
apps/api/tests/test_horizon_coverage.py                  2 F401 + 2 F541
apps/api/tests/test_horizon_guidance_service.py          5 F401
apps/api/tests/test_horizon_pipeline_service.py          1 F401
apps/api/tests/test_horizon_selection_service.py         1 F401
apps/api/tests/test_real_today_v2_api_proof.py           1 E401 + 2 F401 + 25 E701 + 19 E702 + 1 E741
apps/api/tests/test_today_fixture_contract.py            1 F401 + 2 E402
apps/api/tests/test_today_horizon_integration_service.py 2 F401
```

Total must reproduce exactly 97 before editing. Stop on drift.

## 5. Production-module corrections

### 5.1. Preserve intentional version re-exports

In `apps/api/app/core/versions.py`, these imports are public API and are used by
multiple callers:

```python
ACTIVATION_LAYER_VERSION
CALCULATION_VERSION
```

Do not delete them. Mark each as an explicit same-name re-export in the import
list:

```python
ACTIVATION_LAYER_VERSION as ACTIVATION_LAYER_VERSION
CALCULATION_VERSION as CALCULATION_VERSION
```

All version values and object identities must remain unchanged.

### 5.2. Horizon content schema imports and lambda

In `apps/api/app/schemas/horizon_content_canon.py`:

- remove only dead imports `BRACE_RE` and `PLACEHOLDER_RE`;
- preserve `PRODUCT_SPHERE_ORDER` because other runtime modules import it from
  this module; convert it to an explicit same-name re-export:
  `PRODUCT_SPHERE_ORDER as PRODUCT_SPHERE_ORDER`;
- replace the validator-local `eligible = lambda template: ...` with a local
  `def eligible(template: ActionTemplate) -> bool:` having the exact same
  `tone`, `verdict`, safety-class lookup and boolean expression;
- do not move the function outside the current loop/closure and do not change
  iteration order or counts.

In `apps/api/app/schemas/horizon_content_canon_types.py`, remove only the dead
`HORIZON_IDS` and `PUBLIC_PRODUCT_SPHERES` imports. Preserve
`KNOWN_TECHNIQUES`, every Literal/order and all helpers unchanged.

### 5.3. Remove exact dead production imports

Remove only these Ruff-proven unused names:

```text
horizon_claim_policy.py:
  typing.Any
  ActionTemplate
  TodayV2Horizon
  TodayV2ProductSphereKey

horizon_claim_validator.py:
  ordered_intersection
  statement_text_for_fact

horizon_guidance_service.py:
  TodayV2HorizonTiming

personal_fact_pack_service.py:
  AspectPredicate
```

Do not remove neighboring names or alter import layering.

### 5.4. Exact F541 production correction

In `horizon_guidance_formatter.py`, change only the f-string without
placeholders at the reported line into the identical ordinary string. Preserve
the exact message bytes after Python string evaluation.

## 6. Test-support and test-module corrections

### 6.1. `_horizon_guidance_testkit.py`

At the existing top import block:

- consolidate Pydantic import as
  `BaseModel, Field, field_validator, model_validator`;
- consolidate zoneinfo import as
  `ZoneInfo, ZoneInfoNotFoundError`;
- delete the two late module-level imports before coverage models;
- this resolves both E402 and the duplicate `ZoneInfo` F811 without a `noqa`.

Remove only these eight unused names:

```text
HORIZON_ORDER
NatalChartAspect
PersonalFactPack
SphereContribution
SphereScoreV2
load_horizon_content_canons
HorizonGuidanceFormatter
build_sphere_verdicts
```

Preserve all builders, accepted sets, Pydantic validators, timezone behavior
and deterministic case ordering.

### 6.2. Test canon lambda

In `test_horizon_actions_canon.py`, replace the reported local
`eligible = lambda template: ...` with an equivalent nested `def eligible(...)`
inside the same tone/verdict loop. Do not change the 480-combination proof,
template counts or assertions.

### 6.3. Intentional repo-root bootstrap in fixture test

In `test_today_fixture_contract.py`:

- remove unused `pytest` import;
- preserve the `REPO_ROOT` calculation and conditional `sys.path.insert`;
- keep `normalize_file` and `TodayPayload` imports after that bootstrap;
- append exact targeted `# noqa: E402` to those two import lines only;
- do not move those imports before bootstrap and do not suppress E402
  anywhere else.

### 6.4. Exact dead imports in other tests

Remove only the reported unused names:

```text
test_horizon_canon_service.py:
  HorizonSelectionCanon

test_horizon_claim_validator.py:
  ActivationEvidence
  SelectedHorizonAnchor
  PersonalFactPack

test_horizon_coverage.py:
  pytest
  build_sphere_verdicts

test_horizon_guidance_service.py:
  json
  TodayV2Horizon
  validate_horizons_against_evidence
  build_layer
  build_story

test_horizon_pipeline_service.py:
  build_selected_story

test_horizon_selection_service.py:
  ActivationEvidence

test_today_horizon_integration_service.py:
  HorizonSelectionService
  build_activation
```

In `test_horizon_coverage.py`, remove the `f` prefix from the two reported
strings without placeholders, preserving evaluated text exactly.

## 7. Mechanical expansion of `test_real_today_v2_api_proof.py`

This 48-diagnostic file owns formatting cleanup only. Preserve its six test
functions, two fixtures, every parameter row, patch target, expected code,
assertion and source-contract scan.

Required edits:

1. split `import json, re, ast, asyncio` into one import per line and remove
   unused `re`;
2. format stdlib/third-party/project imports normally; remove unused
   `emit_outcome` only;
3. expand every one-line function body, `if`, `with`, `for`, `try/except`,
   assignment/assertion sequence and semicolon-separated statement into normal
   indented lines;
4. rename only the ambiguous comprehension/local variable `l` to `line` (or a
   more precise equivalent) without changing filtering;
5. preserve all string literals, dictionary contents, ordering-sensitive
   assertions, mock call counts and return codes;
6. preserve exactly the six `test_*` function names and collected case count;
7. keep the completed file `<=700` lines and GRACE-clean.

Do not refactor test logic into new helpers merely to silence Ruff. Do not
rewrite patch stacks or change sync/async execution.

## 8. Mandatory preflight

Before editing:

1. completely read 127 and 153;
2. confirm W2C-4 pushed and local HEAD = tracking = remote feature;
3. record accepted base SHA;
4. prove tracked worktree clean and index empty;
5. prove only five frozen unrelated untracked paths remain;
6. run exact Ruff command on the 19 paths and reproduce 97 diagnostics, 19
   paths and exact rule counts from section 1;
7. hash all 19 files and record test collection/counts for affected tests;
8. record canonical API full pytest baseline and contract hashes;
9. record canonical MyPy diagnostic baseline before edits; MyPy is not fixed in
   this wave but must not gain a new normalized error outside the later W3B
   scope;
10. prove runtime services unchanged and ports `3003`, `8001`, `18092` absent.

Stop on mismatch. Never reset, restore, checkout, stash, amend or rebase.

## 9. Mandatory Ruff command

Run from repository root before and after edits:

```bash
apps/api/.venv/bin/python -m ruff check \
  apps/api/app/core/versions.py \
  apps/api/app/schemas/horizon_content_canon.py \
  apps/api/app/schemas/horizon_content_canon_types.py \
  apps/api/app/services/horizon_claim_policy.py \
  apps/api/app/services/horizon_claim_validator.py \
  apps/api/app/services/horizon_guidance_formatter.py \
  apps/api/app/services/horizon_guidance_service.py \
  apps/api/app/services/personal_fact_pack_service.py \
  apps/api/tests/_horizon_guidance_testkit.py \
  apps/api/tests/test_horizon_actions_canon.py \
  apps/api/tests/test_horizon_canon_service.py \
  apps/api/tests/test_horizon_claim_validator.py \
  apps/api/tests/test_horizon_coverage.py \
  apps/api/tests/test_horizon_guidance_service.py \
  apps/api/tests/test_horizon_pipeline_service.py \
  apps/api/tests/test_horizon_selection_service.py \
  apps/api/tests/test_real_today_v2_api_proof.py \
  apps/api/tests/test_today_fixture_contract.py \
  apps/api/tests/test_today_horizon_integration_service.py
```

Required final output: `All checks passed!` and exit zero.

## 10. Required tests and contracts

### 10.1. GRACE and syntax

```bash
apps/api/.venv/bin/python -m compileall -q \
  apps/api/app \
  apps/api/tests
apps/api/.venv/bin/python scripts/test_grace_lint.py
apps/api/.venv/bin/python scripts/grace_lint.py \
  <the exact 19 paths from section 2>
```

Require syntax PASS, GRACE self-tests PASS and exact 19 clean. Do not add
markers solely to change unrelated contracts.

### 10.2. Affected test modules

Run all ten edited `test_*.py` modules from the allowlist; their imports also
exercise the edited shared testkit. Add the direct production-owner tests
listed below. At minimum:

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_actions_canon.py \
  apps/api/tests/test_horizon_canon_service.py \
  apps/api/tests/test_horizon_claim_validator.py \
  apps/api/tests/test_horizon_coverage.py \
  apps/api/tests/test_horizon_guidance_service.py \
  apps/api/tests/test_horizon_pipeline_service.py \
  apps/api/tests/test_horizon_selection_service.py \
  apps/api/tests/test_real_today_v2_api_proof.py \
  apps/api/tests/test_today_fixture_contract.py \
  apps/api/tests/test_today_horizon_integration_service.py \
  apps/api/tests/test_personal_fact_pack_service.py \
  apps/api/tests/test_horizon_language_canon.py \
  apps/api/tests/test_personal_patterns_canon.py \
  apps/api/tests/test_today_meta_versions.py \
  -q
```

Record exact file/test totals; all pass.

### 10.3. Full API and contracts

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
pnpm contracts:check
pnpm contracts:compat
pnpm contracts:fixture:check
PYTHONPATH=packages/py-contracts \
  apps/api/.venv/bin/python -m pytest packages/py-contracts/tests/ -q
```

Require full API green (current expected baseline 1405 passed / 4 skipped),
contracts no drift/compatible/fixture clean and shared contract package 44
PASS. If collected counts legitimately differ, stop and report before any
commit; do not silently update the expectation.

### 10.4. MyPy non-regression diagnostic

From `apps/api` run:

```bash
./.venv/bin/mypy app --no-error-summary --show-error-codes
```

This remains expected-nonzero until W3B. Compare normalized pre/post output.
W3A may remove diagnostics incidentally but must add none. No `Any` blanket,
ignore, cast or typing rewrite is authorized here.

### 10.5. Frontend and feature integrity

```bash
pnpm guardrails:frontend
git diff --check
```

Require frontend guard PASS and diff check PASS_ZERO.

## 11. Final exact-scope review

Before callback prove:

```text
tracked changed paths             exact 19 allowlisted files
index                             empty
Ruff exact scope                  0 diagnostics / 0 failing paths
public constants/re-exports       unchanged
schema/model/validation behavior  unchanged
test names/params/assertions       unchanged
GRACE markers/contracts           preserved
test modules                      <=700 lines
full API                          green
contracts                         green/no drift
MyPy normalized diagnostics       no new errors
runtime/services                  unchanged
ports 3003/8001/18092             absent
commit/push                       not performed
```

Inspect the complete diff manually. Formatting expansion in the real-proof
test must not hide semantic edits.

## 12. Frozen state

Never touch or stage:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Do not mutate env, systemd, nginx, database, Docker or runtime processes.

## 13. Required callback

```text
READY_STAGE_2_W3A_FEATURE_API_RUFF_REVIEW
base_head: <accepted pushed W2C4 sha>
tracked_scope: EXACT_19_API_RUFF_FILES
ruff_before: 97_DIAGNOSTICS_19_PATHS
ruff_after: PASS_ZERO
intentional_reexports: PRESERVED
runtime_schema_behavior: UNCHANGED
test_logic_collection: UNCHANGED
grace_syntax: PASS
targeted_tests: PASS_<EXACT_FILES_AND_TESTS>
api_full: 1405_PASS_4_SKIP
contracts_check_compat_fixture: PASS
py_contracts: 44_PASS
mypy_non_regression: PASS_NO_NEW_NORMALIZED_ERRORS
frontend_guard: PASS
git_diff_check: PASS_ZERO
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
main_deploy: NOT_STARTED
```

Then stop for architect review. W3B/W3C remain forbidden.
