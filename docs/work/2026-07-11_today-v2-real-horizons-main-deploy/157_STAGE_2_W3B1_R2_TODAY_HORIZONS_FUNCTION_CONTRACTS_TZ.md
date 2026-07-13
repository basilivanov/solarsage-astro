# Stage 2.W3B1 R2 — today-horizons function-contract completion

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`24efa83eb91a36c6419cf174c8d24ee95870086b`
Parents:

- `155_STAGE_2_W3B1_SCHEMA_MYPY_CORRECTION_TZ.md`;
- `156_STAGE_2_W3B1_R1_DOWNSTREAM_TYPE_PRECISION_RECLASSIFICATION_TZ.md`.

Статус: **MANDATORY COMMENT-ONLY GRACE REPAIR — NO COMMIT/PUSH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Architect finding

R1 completion exposed a pre-existing backend GRACE baseline in the now-touched
schema module:

```text
apps/api/app/schemas/today_horizons.py
GRC010 missing function contracts: 16
other W3B1 files: clean
```

W3B1 did not create these missing contracts. However, because
`today_horizons.py` is now an active changed path, acceptance requires it to be
GRACE-clean.

Add truthful comments only. Preserve every W3B1 type edit and all runtime
bytes/statements.

## 2. Exact coder edit scope

Edit only:

```text
apps/api/app/schemas/today_horizons.py
```

Docs 156/157 are architect-owned and must not be edited/staged. The other
three W3B1 schema files are byte-frozen.

No test/config/service/shared-contract/frontend edit. No staging, commit or
push. W3B2/W3B3/W3C remain forbidden.

## 3. Hard comment-only invariant

- Insert exactly 16 paired function-contract blocks inside the 16 functions in
  section 4.
- Do not change decorators, signatures, type annotations, statements,
  whitespace inside existing executable statements, strings, validation order
  or error paths.
- Preserve the new `AbstractSet[str]` annotation exactly.
- Do not add/remove imports.
- Do not run formatter.
- Comment-stripped source and runtime suffix must remain equivalent.
- Existing function-contract IDs must remain unchanged.
- New IDs must be class-qualified where method names repeat.

## 4. Exact required contracts

Use the standard fields in this order:

```text
START_FUNCTION_CONTRACT
purpose
inputs
returns
side_effects
emitted_logs
error_behavior
END_FUNCTION_CONTRACT
```

### 4.1. Nested provenance accumulator

Function:

```text
_collect_provenance_activation_ids.extend_from_provenance
```

ID:

```text
F-M-CONTRACTS-TODAY-HORIZONS._collect_provenance_activation_ids.extend_from_provenance
```

Required facts:

```text
purpose: Append every activation id from one provenance object with its
         structural path to the enclosing references accumulator.
inputs: path - already-built structural path; provenance - typed provenance.
returns: none.
side_effects: mutates only the enclosing local references list.
emitted_logs: none.
error_behavior: none; iterates the validated activation_ids list.
```

### 4.2. `TodayV2Provenance`

`validate_unique_lists`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Provenance.validate_unique_lists
purpose: Enforce uniqueness for each provenance scalar list.
inputs: values - validated field list selected by the Pydantic field validator.
returns: the same list unchanged when unique.
side_effects: none.
emitted_logs: none.
error_behavior: raises ValueError through _ensure_unique on duplicates.
```

`validate_non_empty_sources`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Provenance.validate_non_empty_sources
purpose: Require at least one non-empty provenance source list.
inputs: self - validated provenance candidate.
returns: the same model when at least one source list is populated.
side_effects: none.
emitted_logs: none.
error_behavior: raises structural ValueError when all four source lists are empty.
```

### 4.3. `TodayV2HorizonTiming`

`validate_non_blank_labels`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonTiming.validate_non_blank_labels
purpose: Reject blank range/state/timezone label fields.
inputs: value - field string; info - Pydantic field metadata.
returns: the original value when non-blank after stripping for validation.
side_effects: none.
emitted_logs: none.
error_behavior: raises structural ValueError through _ensure_non_empty_after_strip.
```

`validate_peak_label`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonTiming.validate_peak_label
purpose: Permit a null peak label or reject a present blank peak label.
inputs: value - optional peak label.
returns: None unchanged or the original validated non-blank string.
side_effects: none.
emitted_logs: none.
error_behavior: raises structural ValueError for a present blank label.
```

### 4.4. `TodayV2TechniqueExplanation`

`validate_non_blank_fields`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2TechniqueExplanation.validate_non_blank_fields
purpose: Reject blank technique, label, definition and relevance copy.
inputs: value - field string; info - Pydantic field metadata.
returns: the original non-blank value.
side_effects: none.
emitted_logs: none.
error_behavior: raises structural ValueError for blank copy.
```

`validate_activation_ids_unique`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2TechniqueExplanation.validate_activation_ids_unique
purpose: Enforce unique activation references in one technique explanation.
inputs: values - activation id list.
returns: the same list unchanged when unique.
side_effects: none.
emitted_logs: none.
error_behavior: raises structural ValueError on duplicate ids.
```

### 4.5. `TodayV2Manifestation`

`validate_non_blank_fields`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Manifestation.validate_non_blank_fields
purpose: Reject blank manifestation title/body copy.
inputs: value - field string; info - Pydantic field metadata.
returns: the original non-blank value.
side_effects: none.
emitted_logs: none.
error_behavior: raises structural ValueError for blank copy.
```

`validate_condition`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Manifestation.validate_condition
purpose: Permit a null condition or reject a present blank condition.
inputs: value - optional condition copy.
returns: None unchanged or the original validated non-blank string.
side_effects: none.
emitted_logs: none.
error_behavior: raises structural ValueError for a present blank condition.
```

`validate_sphere_keys_unique`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Manifestation.validate_sphere_keys_unique
purpose: Enforce unique sphere references in one manifestation.
inputs: values - sphere key list.
returns: the same list unchanged when unique.
side_effects: none.
emitted_logs: none.
error_behavior: raises structural ValueError on duplicate keys.
```

### 4.6. `TodayV2HorizonActions`

`validate_non_blank_fields`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonActions.validate_non_blank_fields
purpose: Reject blank action heading and valid-until label.
inputs: value - field string; info - Pydantic field metadata.
returns: the original non-blank value.
side_effects: none.
emitted_logs: none.
error_behavior: raises structural ValueError for blank copy.
```

### 4.7. `TodayV2Horizon`

`validate_non_blank_text_fields`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Horizon.validate_non_blank_text_fields
purpose: Reject blank eyebrow/title/summary/plain-explanation copy.
inputs: value - field string; info - Pydantic field metadata.
returns: the original non-blank value.
side_effects: none.
emitted_logs: none.
error_behavior: raises structural ValueError for blank copy.
```

`validate_unique_scalar_lists`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Horizon.validate_unique_scalar_lists
purpose: Enforce uniqueness for likely_spheres and activation_ids.
inputs: values - selected list; info - Pydantic field metadata.
returns: the same list unchanged when unique.
side_effects: none.
emitted_logs: none.
error_behavior: raises structural ValueError on duplicates.
```

### 4.8. `TodayV2HorizonIntro`

`validate_non_blank_text_fields`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonIntro.validate_non_blank_text_fields
purpose: Reject blank intro eyebrow/headline/body/theme key.
inputs: value - field string; info - Pydantic field metadata.
returns: the original non-blank value.
side_effects: none.
emitted_logs: none.
error_behavior: raises structural ValueError for blank text/id.
```

`validate_activation_ids_unique`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonIntro.validate_activation_ids_unique
purpose: Enforce unique activation references in the intro.
inputs: values - activation id list.
returns: the same list unchanged when unique.
side_effects: none.
emitted_logs: none.
error_behavior: raises structural ValueError on duplicate ids.
```

### 4.9. `TodayV2HorizonsBlock`

`validate_warnings`:

```text
ID: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonsBlock.validate_warnings
purpose: Enforce ordered unique non-blank warning strings.
inputs: values - warning list.
returns: the same list in original order when valid.
side_effects: none.
emitted_logs: none.
error_behavior: raises structural ValueError on duplicate or blank warnings.
```

## 5. Mechanical equivalence proof

Before edit snapshot the current accepted `today_horizons.py`. After edit
require:

```text
changed file                         today_horizons.py only
new function-contract pairs          exactly 16
new unique IDs                       exactly 16
existing function contracts          unchanged
runtime/comment-stripped source       equivalent
imports/signatures/decorators         unchanged
AbstractSet W3B1 type edit            unchanged
other three W3B1 hashes               unchanged
index                                 empty
```

Run `git diff --check` and inspect the full delta relative to the R1 frozen
snapshot: it may contain comments/adjacent blank lines only.

## 6. Mandatory gates

```bash
apps/api/.venv/bin/python -m ruff check \
  apps/api/app/schemas/today_horizons.py \
  apps/api/app/schemas/horizon_canon.py \
  apps/api/app/schemas/horizon_content_canon.py \
  apps/api/app/schemas/horizon_content_canon_types.py

apps/api/.venv/bin/python scripts/test_grace_lint.py
apps/api/.venv/bin/python scripts/grace_lint.py \
  apps/api/app/schemas/today_horizons.py \
  apps/api/app/schemas/horizon_canon.py \
  apps/api/app/schemas/horizon_content_canon.py \
  apps/api/app/schemas/horizon_content_canon_types.py
```

Require Ruff zero, GRACE self-tests 13 PASS and all four files clean.

Then rerun the exact MyPy no-incremental proof from doc 156. Require:

```text
118 diagnostics / 21 paths
W3B1 four paths zero
exact five reclassified W3B2 errors
no unexpected new errors
```

Run all remaining gates from doc 156 section 4. Require targeted 139, API
1405/4, contracts/fixture/44, frontend guard and diff check all green.

## 7. Required callback

```text
READY_STAGE_2_W3B1_R2_GRACE_COMPLETE
base_head: 24efa83eb91a36c6419cf174c8d24ee95870086b
tracked_scope: EXACT_4_SCHEMA_FILES
r2_coder_scope: TODAY_HORIZONS_COMMENTS_ONLY
function_contracts_added: EXACT_16_PAIRED_UNIQUE
runtime_equivalence: PASS
mypy_w3b1: PASS_ZERO
mypy_total: 118_DIAGNOSTICS_21_PATHS
reclassified_downstream: EXACT_5_ERRORS_3_W3B2_PATHS
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
