# Stage 2.W3B1 — schema-level MyPy correction

Дата: `2026-07-13`
Branch: `preview/solarsage-v2-human-first-navigator-ux`
Parent master:
`127_STAGE_2_CORRECTIVE_RELEASE_MAIN_DEPLOY_WAVE_MASTER.md`.
Predecessor: W3A must be accepted, committed and pushed first.

Статус: **PREPARED W3B1 — NOT AUTHORIZED UNTIL ARCHITECT SENDS THIS PATH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. W3B decomposition and this subwave

The accepted canonical MyPy run after W3A reports:

```text
full app diagnostics    129
full app failing paths   24
W3B owned diagnostics    49
W3B owned failing paths  13
```

W3B is decomposed by dependency direction:

```text
W3B1 schemas/closed aliases        4 paths / 16 diagnostics  <- this wave
W3B2 pure selection/guidance       7 paths / 23 diagnostics
W3B3 semantic/today integration    2 paths / 10 diagnostics
```

The remaining six paths from the original 19-path typed inventory are already
MyPy-clean and remain frozen unless a later precise dependency reason is
approved.

W3B1 goal: remove the exact 16 schema-owned diagnostics through truthful
covariant input types, explicit Literal aliases, fixed-tuple construction and
semantically unique loop variable names. Runtime behavior and validation order
must remain unchanged.

No staging, commit or push before separate architect review.

## 2. Exact edit allowlist

```text
apps/api/app/schemas/today_horizons.py
apps/api/app/schemas/horizon_canon.py
apps/api/app/schemas/horizon_content_canon.py
apps/api/app/schemas/horizon_content_canon_types.py
```

Edit exact four only. Do not edit tests, services, shared contracts, YAML
canons, generated artifacts, MyPy/Ruff config, docs, sidecar or frontend.

No `git add`, commit or push. Do not start W3B2/W3B3/W3C/final RC/main/deploy.

## 3. Exact accepted MyPy baseline

From `apps/api`, canonical command:

```bash
./.venv/bin/mypy app --no-error-summary --show-error-codes
```

Exact W3B1 diagnostics:

```text
app/schemas/today_horizons.py
  5 x [arg-type] at provenance likely_spheres calls

app/schemas/horizon_canon.py
  2 x [assignment] from reusing values across differently typed loops

app/schemas/horizon_content_canon_types.py
  1 x [valid-type] for Literal[*THEME_KEYS]
  1 x [return-value] for tuple(sorted(...)) as tuple[str, ...]

app/schemas/horizon_content_canon.py
  6 x [assignment] from function-scoped loop-variable reuse
  1 x [index] from sphere variable type pollution
```

Required W3B1 result:

```text
exact four paths        0 MyPy errors
new errors elsewhere   0
Ruff                    clean
tests/contracts         green
```

Fixing explicit aliases may remove additional downstream W3B diagnostics. Such
removals are allowed and must be reported. New diagnostics are not accepted;
do not broaden scope to fix them without architect review.

## 4. Absolute typing constraints

- No `Any` addition or widening.
- No `cast`, `# type: ignore`, `noqa`, `typing.cast`, `assert_type` masking,
  file/module ignore, MyPy config change or Pydantic plugin change.
- Do not weaken Literal unions, field types, validators, model config,
  min/max constraints or closed key sets.
- Do not convert typed models/collections to untyped dict/list/set.
- Do not change error strings, validation order, iteration order, public
  aliases, exported names, YAML interpretation or model serialization.
- Preserve GRACE contracts/maps/function contracts and update only an input
  description if its static type wording becomes materially inaccurate.
- No formatter or unrelated line wrapping.

## 5. `today_horizons.py` — covariant read-only sphere set

Current helper accepts:

```python
likely_spheres: set[str]
```

Callers pass `set[TodayV2ProductSphereKey]`. Mutable `set` is invariant, while
the helper only reads membership/subset state.

Required correction:

1. import `AbstractSet` from `typing` alongside existing typing imports;
2. change only the helper parameter to:

```python
likely_spheres: AbstractSet[str]
```

3. retain the same `set(provenance.sphere_keys).issubset(likely_spheres)`
   expression and all five callers unchanged;
4. update the function-contract input wording only if needed to say read-only
   allowed sphere set.

Do not cast the caller set and do not widen `TodayV2ProductSphereKey`.

Expected result: all five `[arg-type]` errors disappear.

## 6. `horizon_canon.py` — unique loop variable identities

MyPy pins function-scoped loop variable `values` to the first typed mapping and
then rejects its reuse for theme lists.

Inside `HorizonSelectionCanon.validate_canon`, rename local loop values only:

```text
technical_to_product_spheres loop: values -> product_spheres
technical_sphere_themes loop:      values -> theme_ids
target_planet_themes loop:         values -> planet_theme_ids
```

Update every reference inside its own loop. Preserve `technical_key`,
`planet_key`, all conditions, sets, messages, ordering and return value.

No annotation/cast is required. Expected result: two `[assignment]` errors
disappear.

## 7. `horizon_content_canon_types.py` — explicit closed alias and fixed pair

### 7.1. Explicit theme Literal and runtime tuple

`Literal[*THEME_KEYS]` is invalid to MyPy because `THEME_KEYS` is a runtime
tuple. Replace the declaration pair with an explicit alias and an explicitly
typed tuple containing the same ten keys in the same order:

```python
HorizonThemeKey = Literal[
    "communication_learning_documents",
    "structure_boundaries_control",
    "relationships_values_closeness",
    "resources_security",
    "energy_body_pacing",
    "home_belonging",
    "inner_clarity_recovery",
    "direction_growth_meaning",
    "creativity_visibility",
    "change_innovation",
]

THEME_KEYS: tuple[HorizonThemeKey, ...] = (
    "communication_learning_documents",
    "structure_boundaries_control",
    "relationships_values_closeness",
    "resources_security",
    "energy_body_pacing",
    "home_belonging",
    "inner_clarity_recovery",
    "direction_growth_meaning",
    "creativity_visibility",
    "change_innovation",
)
```

Do not derive the alias from a runtime value, use a cast, reorder keys or
change the exported `THEME_KEYS` runtime tuple.

### 7.2. Exact two-element canonical pair

Keep all existing invalid-input guards. Replace only the return construction:

```python
first, second = sorted((point_a, point_b), key=PLANET_ORDER.index)
return first, second
```

This preserves the exact order and runtime values while making the fixed
two-element return visible to MyPy. Do not cast the sorted tuple.

Expected result: `[valid-type]` and `[return-value]` both disappear.

## 8. `horizon_content_canon.py` — remove loop-variable type pollution

The validator is function-scoped; repeated names such as `key`, `value`,
`sphere` and `statement` become pinned to incompatible model/dict value types.
Rename locals only. Use this semantic mapping:

```text
self.horizons.items():
  horizon_id, horizon_labels
  horizon_field_name, horizon_field_value

tone/timing label group tuple:
  label_group_path, label_mapping
  label_key, label_value

self.timing_templates.items():
  timing_template_key, timing_template

self.techniques.items():
  technique_key, technique_language
  technique_field_name, technique_field_value

self.themes.items():
  theme_key, theme_language
  horizon_id
  theme_field_name, theme_field_value

self.product_spheres.items():
  product_sphere_key, sphere_language

self.sphere_fact_statements.items():
  product_sphere_key, sphere_statement

self.personal_statements.items():
  statement_key, personal_statement
```

Requirements:

- update all references and f-string path fragments to preserve exactly the
  same resulting strings;
- keep dictionary/model iteration order unchanged;
- keep every `_validate_copy`, `_template_placeholders`, set comparison and
  error branch unchanged;
- keep `expected = f"sphere.active.{product_sphere_key}"` and index
  `self.product_spheres[product_sphere_key]` semantically identical;
- do not add annotations, casts or helper functions;
- do not rename class fields or public aliases.

Expected result: six `[assignment]` and one `[index]` errors disappear.

## 9. Mandatory preflight

Before editing:

1. completely read 127 and 155;
2. confirm W3A pushed and local HEAD = tracking = remote feature;
3. prove tracked worktree clean, index empty and only five frozen unrelated
   paths untracked;
4. run canonical MyPy and save full output to
   `/tmp/stage2-w3b1-mypy-before.log`;
5. prove full baseline 129 diagnostics / 24 paths;
6. filter the four exact paths and prove 16 diagnostics with the decomposition
   in section 3;
7. hash all four source files;
8. run Ruff on exact four and require current clean baseline;
9. run the targeted seven-file suite from section 11 and require 139 PASS;
10. prove generated contracts, runtime services and ports unchanged.

Stop on mismatch. Never reset, restore, checkout, stash, amend or rebase.

## 10. Exact MyPy proof

Run from `apps/api` before and after:

```bash
set +e
./.venv/bin/mypy app --no-error-summary --show-error-codes \
  > /tmp/stage2-w3b1-mypy-after.log 2>&1
rc=$?
set -e
test "$rc" -eq 1
```

The command remains non-zero until W3B2/W3B3. Parse diagnostics by exact path.
Require:

```text
four W3B1 paths                   0 errors
new normalized errors globally   0
removed downstream errors         allowed and recorded
full diagnostic total             <=113
```

If total is above 113, if any new error appears, or if a diagnostic migrates
to a non-W3B path, stop for architect review. Do not fix outside allowlist.

## 11. Ruff, GRACE and targeted tests

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

PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_horizons_contract.py \
  apps/api/tests/test_contract_registry.py \
  apps/api/tests/test_horizon_canon_service.py \
  apps/api/tests/test_horizon_language_canon.py \
  apps/api/tests/test_horizon_actions_canon.py \
  apps/api/tests/test_personal_patterns_canon.py \
  apps/api/tests/test_horizon_content_canon_service.py \
  -q
```

Require Ruff zero, GRACE self-tests 13 PASS, exact four GRACE clean and exact
7 files / 139 tests PASS.

## 12. Full regression and contracts

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

Require API 1405 passed / 4 skipped, contracts no drift/additive zero breaking,
fixture clean, shared contracts 44 PASS, frontend guard PASS and diff check
PASS_ZERO.

## 13. Final scope and callback

Before callback prove:

```text
tracked changed paths             exact 4 schema files
index                             empty
W3B1 MyPy errors                  0
new global MyPy errors            0
Ruff                              clean
runtime validation/serialization  unchanged
public aliases/runtime tuples     unchanged
tests/contracts                   green
runtime/services                  unchanged
ports 3003/8001/18092             absent
commit/push                       not performed
```

Never touch/stage the frozen paths:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Required callback:

```text
READY_STAGE_2_W3B1_SCHEMA_MYPY_REVIEW
base_head: <accepted pushed W3A sha>
tracked_scope: EXACT_4_SCHEMA_FILES
mypy_before: 129_TOTAL_24_PATHS_16_W3B1_ERRORS
mypy_w3b1_after: PASS_ZERO
mypy_total_after: <N_LE_113>
mypy_new_errors: ZERO
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
