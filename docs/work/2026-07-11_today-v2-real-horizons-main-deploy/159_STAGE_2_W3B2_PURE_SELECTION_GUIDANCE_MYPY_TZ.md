# Stage 2.W3B2 — pure selection/guidance MyPy correction

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`1e3fe7de712619bf69fc18d504293fa93d15530f`
Parent master:
`127_STAGE_2_CORRECTIVE_RELEASE_MAIN_DEPLOY_WAVE_MASTER.md`.
Accepted predecessor:
`158_STAGE_2_W3B1_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md`.
Prepared successor:
`160_STAGE_2_W3B3_SEMANTIC_TODAY_INTEGRATION_MYPY_TZ.md`.

Статус: **AUTHORIZED W3B2 IMPLEMENTATION — NO COMMIT/PUSH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Goal and corrected ownership

W3B1 is accepted and pushed. Its explicit closed `HorizonThemeKey` repaired an
invalid alias and correctly exposed five previously hidden service-boundary
errors. Therefore W3B2 expands from the original 7 paths / 23 diagnostics to
the exact current 8 paths / 28 diagnostics:

```text
app/services/horizon_claim_policy.py             1
app/services/horizon_claim_validator.py          3
app/services/horizon_guidance_builders.py        7
app/services/horizon_guidance_formatter.py       1
app/services/horizon_guidance_service.py         7
app/services/horizon_selection_service.py        4
app/services/horizon_timing_service.py           4
app/services/personal_fact_pack_service.py       1
                                                  --
total                                            28
```

W3B2 goal: make all eight pure selection/guidance paths MyPy-clean through
truthful read-only/generic collection types, exact model types, closed theme
resolution, fixed tuple construction, and `NoReturn` control-flow narrowing.

Runtime values, ranking, selection order, error codes, public copy, validation
order and serialization must remain unchanged.

No staging, commit or push before separate architect review.

## 2. Exact edit allowlist

```text
apps/api/app/services/horizon_claim_policy.py
apps/api/app/services/horizon_claim_validator.py
apps/api/app/services/horizon_guidance_builders.py
apps/api/app/services/horizon_guidance_formatter.py
apps/api/app/services/horizon_guidance_service.py
apps/api/app/services/horizon_selection_service.py
apps/api/app/services/horizon_timing_service.py
apps/api/app/services/personal_fact_pack_service.py
```

Edit exact eight only. Do not edit schemas, tests, canons, generated contracts,
MyPy/Ruff configuration, docs, sidecar, frontend or runtime/service files
outside this list.

Docs `159` and `160` are architect-owned. Do not edit or stage them.

No `git add`, commit or push. Do not start W3B3/W3C/final RC/main/deploy.

## 3. Accepted pre-edit state

Cold canonical run from `apps/api`:

```bash
./.venv/bin/mypy app --no-incremental --no-error-summary --show-error-codes
```

Accepted state:

```text
global diagnostics                  118
global failing paths                 21
W3B2 diagnostics                     28
W3B2 failing paths                    8
future W3B3 diagnostics              10
future W3B3 failing paths             2
legacy diagnostics                   80
legacy failing paths                 11
```

Exact W3B3 paths remain frozen:

```text
app/services/semantic_v2_service.py    2
app/services/today_service.py          8
```

Required W3B2 result if no diagnostic migration occurs:

```text
global diagnostics                   90
global failing paths                 13
W3B2 diagnostics                      0
W3B3 diagnostics                     10 unchanged
legacy diagnostics                   80 unchanged
```

## 4. Absolute typing and behavior constraints

- No `Any` addition or widening.
- No `cast`, `typing.cast`, `# type: ignore`, `noqa`, file/module ignore,
  MyPy config/plugin change, untyped dict/list replacement or schema weakening.
- Do not widen `HorizonThemeKey`, `TodayV2ProductSphereKey`,
  `TodayV2HorizonId`, `HorizonSphereVerdict`, timing literals or action types
  back to plain `str` at typed boundaries.
- Use covariant/read-only collection protocols where a function only reads.
- Use a bounded generic where the function preserves an input string subtype.
- Do not change Pydantic models or generated artifacts in this wave.
- Do not change selection scoring, sort keys, loop order, truncation limits,
  action eligibility, fact ranking, timing arithmetic, labels, errors or copy.
- Do not add a runtime assertion merely to silence MyPy when an exact static
  type can be expressed.
- Preserve all GRACE markers/contracts. Update contract input wording when a
  signature becomes more precise; add a truthful contract for the one new
  shared helper.
- No formatter or broad import sorting.

## 5. `horizon_guidance_builders.py` — generic collections and closed theme boundary

### 5.1. Generic ordered intersection

The current helper accepts `list[str]`, which rejects invariant lists of
`TodayV2ProductSphereKey` even though it only reads and preserves values.

Introduce one private bounded type variable:

```python
_TStr = TypeVar("_TStr", bound=str)
```

Change the helper to the equivalent read-only generic shape:

```python
def ordered_intersection(
    ordered: Sequence[_TStr],
    candidates: Collection[_TStr],
) -> list[_TStr]:
```

Requirements:

- keep `seen = set(candidates)` and first-input order semantics;
- return the original subtype (`str` or closed string Literal);
- do not mutate either input;
- do not convert callers to `list[str]` merely for typing;
- update the existing function contract to describe read-only inputs and
  subtype-preserving output.

This removes the two builder call errors and keeps policy callers precise.

### 5.2. Shared canonical theme resolver

Add one pure public helper in the builders module:

```python
def resolve_canon_theme_key(
    value: str,
    canon: HorizonContentCanonBundle,
) -> HorizonThemeKey | None:
```

Implementation rule: iterate the already validated keys of
`canon.language.themes` in their existing order and return the typed key whose
value equals `value`; otherwise return `None`.

Do not use cast, a duplicated hard-coded tuple, regex inference or fallback to
the first theme. This helper is the explicit boundary from a legacy internal
`str` to the closed content-canon key.

Add:

- `HorizonThemeKey` import from `horizon_content_canon_types`;
- a full truthful function contract;
- the helper to module-map public entrypoints and `__all__`.

Generator, policy and validator must use this same resolver so theme lookup
semantics cannot drift.

### 5.3. Exact builder parameter types

Use precise types without changing bodies/output:

```text
build_actions.horizon_theme
  str -> HorizonThemeKey

build_actions.sphere_verdicts
  dict[TodayV2ProductSphereKey, str]
  -> Mapping[TodayV2ProductSphereKey, HorizonSphereVerdict]

build_technique_explanation.horizon_theme
  str -> HorizonThemeKey
```

`Mapping` is required because actions only read verdicts and the caller owns a
dict with closed `HorizonSphereVerdict` values.

Import `ActionTemplate` and type the nested compatibility predicate exactly:

```python
def _compatible(template: ActionTemplate) -> bool:
```

Type the nested item builder with read-only `Sequence[ActionTemplate]` and a
closed kind literal if needed to preserve `TodayV2GroundedItem.kind` precision.
Do not alter filtering, slicing, ids, provenance or action order.

`assign_claims.horizon_theme` is not a canon lookup and currently has no MyPy
diagnostic. Leave its public behavior/signature unchanged in this wave.

Expected owned removal: 7 diagnostics in this file.

## 6. `horizon_guidance_service.py` — typed anchor and theme resolution

Import exact types:

```text
HorizonThemeKey
SelectedHorizonAnchor
resolve_canon_theme_key
```

Change return/argument types:

```python
def _resolve_primary_theme(
    self,
    selection: SelectedHorizonTriple,
) -> HorizonThemeKey:

def _resolve_horizon_theme(
    self,
    anchor: SelectedHorizonAnchor,
    primary_theme: HorizonThemeKey,
) -> HorizonThemeKey:

def _build_intro(
    self,
    context: HorizonGuidanceContext,
    primary_theme: HorizonThemeKey,
) -> TodayV2HorizonIntro:
```

Resolution behavior must remain exact:

1. primary raw value is still `selection.shared_theme_keys[0]`;
2. per-anchor raw value is still primary when present in `anchor.theme_keys`,
   otherwise the first anchor theme;
3. pass that raw value through `resolve_canon_theme_key`;
4. on `None`, raise the same `HorizonGuidanceError` code and same structural
   path currently owned by the corresponding method;
5. do not silently choose another canon theme or reorder anchor themes.

The main build loop then indexes `language.themes` only with a proven
`HorizonThemeKey`, and passes exact typed values to actions/technique builders.

Expected owned removal: 7 diagnostics.

## 7. `horizon_claim_policy.py` — read-only anchor map and typed action theme

The policy reads the anchor map but never mutates it. Change:

```python
anchor_by_horizon: Mapping[TodayV2HorizonId, SelectedHorizonAnchor]
```

Import `Mapping`, `TodayV2HorizonId`, and `resolve_canon_theme_key`.

For each horizon preserve the raw selection exactly:

```text
shared primary when it belongs to anchor.theme_keys
otherwise anchor.theme_keys[0]
```

Resolve that raw string through the shared helper before
`canon.actions.themes.get(...)`. If it returns `None`, call the same policy
failure code `action_not_authorized` at the same horizon actions path.

Do not raise `HorizonGuidanceError` from policy and do not change validation
order.

Expected owned removal: 1 diagnostic.

## 8. `horizon_claim_validator.py` — truthful non-returning failure helper

### 8.1. Mapping compatibility

The `_anchor_map` return is already exact:

```python
dict[TodayV2HorizonId, SelectedHorizonAnchor]
```

The policy `Mapping` correction in section 7 must accept it without copying or
widening.

### 8.2. Control-flow narrowing

The module-level `_fail` always raises. Change only its return annotation:

```python
def _fail(code: str, detail: str = "") -> NoReturn:
```

Import `NoReturn`. Keep the same raised error and arguments. This truthfully
narrows `hi` and `a` after the existing null checks and removes both union
attribute diagnostics. Do not add asserts, duplicate checks or casts.

Expected owned removal: 3 diagnostics.

## 9. `horizon_guidance_formatter.py` — typed product-sphere lookup

`target_key` remains raw `str` because `target_label` supports several target
families. In the `target_type == "sphere"` branch, do not call a dict keyed by
`TodayV2ProductSphereKey` with raw `str`.

Instead iterate `canon.product_spheres.items()` in existing canonical order,
select the entry whose typed key equals `target_key`, and return the same
formatted label. If no entry matches, raise the same
`unsupported_entity_label | sphere` error.

No hard-coded sphere set, cast, TypeGuard duplication or copy change.

Expected owned removal: 1 diagnostic.

## 10. `horizon_selection_service.py` — subtype-preserving list helpers

### 10.1. Generic helper signatures

Introduce a private `TypeVar` bounded by `str` and change both pure helpers to
accept read-only nested sequences and return the same subtype:

```python
def _ordered_union_by_frequency(
    items: Sequence[Sequence[_TStr]],
) -> list[_TStr]:

def _intersection_in_first_order(
    first: Sequence[_TStr],
    others: Sequence[Sequence[_TStr]],
) -> list[_TStr]:
```

Type internal `order` and `Counter` with `_TStr`. Preserve frequency, first
occurrence, lexicographic final tie-break and exact output order.

This must support both legacy theme `str` lists and closed product-sphere
Literal lists without converting either to a weaker type.

### 10.2. Closed horizon dictionaries

Import `TodayV2HorizonId` and change only the two annotations:

```python
candidates_by_horizon: dict[TodayV2HorizonId, list[HorizonCandidate]]
bounded_by_horizon: dict[TodayV2HorizonId, list[HorizonCandidate]]
```

Keep exact three keys, iteration order, bounds and sort behavior unchanged.

Expected owned removal: 4 diagnostics.

## 11. `horizon_timing_service.py` — exact canon and timing literal types

### 11.1. Canon type

Import `HorizonSelectionCanon` and change:

```python
def _speed_group(
    canon: HorizonSelectionCanon,
    source_planet: str | None,
) -> Literal["fast", "medium", "slow"] | None:
```

Preserve normalization and the exact fast/medium/slow search order. Use an
explicitly typed tuple of `(group_name, members)` if needed; no `object`, cast
or dynamic fallback.

### 11.2. Safe assessment types

Use the aliases already owned by selection/today schemas:

```text
RelativeTargetPosition
HorizonTimingWarningCode
TodayV2TimingPrecision
TodayV2TimingState
TodayV2HorizonId
```

Make `_safe_assessment` parameters exact:

```text
relative_position   RelativeTargetPosition
warning_codes       Sequence[HorizonTimingWarningCode]
timing_state        TodayV2TimingState | None
precision           TodayV2TimingPrecision | None
eligible_horizons   Sequence[TodayV2HorizonId] | None
preferred_horizons  Sequence[TodayV2HorizonId] | None
```

The helper still creates fresh lists and deduplicates warnings in first order.

Give `_detect_precision` a private closed result alias containing exactly:

```text
date | instant | mixed | invalid | None
```

After the existing early returns, `precision` must narrow to date/instant.
Annotate `state` precisely if needed; do not change state-selection branches.

### 11.3. Canonical horizon iteration

Use `HORIZON_ORDER` from `horizon_selection` and declare:

```python
eligible_horizons: list[TodayV2HorizonId] = []
preferred_horizons: list[TodayV2HorizonId]
source_speed_warning: list[HorizonTimingWarningCode] = []
```

Preserve long/medium/fast order, duration comparisons and fallback copy.

Expected owned removal: 4 diagnostics.

## 12. `personal_fact_pack_service.py` — exact two-item pair

Keep all existing invalid-input guards. Replace only:

```python
return tuple(sorted((left, right), key=PLANET_ORDER.index))
```

with:

```python
first, second = sorted((left, right), key=PLANET_ORDER.index)
return first, second
```

This is the same correction pattern already accepted in W3B1. Preserve values
and ordering exactly; no cast.

Expected owned removal: 1 diagnostic.

## 13. Mandatory preflight

Before editing:

1. completely read `127`, `158`, `159`, and prepared `160`;
2. run `git fetch origin` without merge/rebase;
3. prove branch exactly
   `preview/solarsage-v2-human-first-navigator-ux`;
4. prove HEAD = tracking = remote feature =
   `1e3fe7de712619bf69fc18d504293fa93d15530f`;
5. prove `main` = `origin/main` =
   `c9bc36bd9a947566eddb1ffcf5617967c7412676`;
6. prove tracked worktree and index clean and only five frozen unrelated groups
   plus architect docs `159`/`160` are untracked;
7. run and save the cold MyPy baseline; prove 118/21 and exact W3B2 28/8;
8. snapshot/hash all eight files;
9. run exact eight-file Ruff and GRACE; require current clean baseline;
10. run the exact targeted suite in section 15; require 231 PASS;
11. prove contracts/runtime services/ports unchanged.

Accepted pre-edit hashes:

```text
9ffbc000f519af6b1c4c0679f8749194785fd21e02f94a7b428159a6785fa4f8  apps/api/app/services/horizon_claim_policy.py
345b271df66309a4a033ec6dd99317c529ae774c7d59e5091b32cc7a0047fce5  apps/api/app/services/horizon_claim_validator.py
ad3e87891a598afe2c8eaae50a22ca601766efbdd3024d38816b1fcd7262d93e  apps/api/app/services/horizon_guidance_builders.py
f518ca78bbf9be07d6f3db91a0822350e64b18f39a68f0be3f078ba27488399b  apps/api/app/services/horizon_guidance_formatter.py
882227811ff979361647313ad4f06ecc99a14fcfb830314bc19892c3220b5e82  apps/api/app/services/horizon_guidance_service.py
deeeb1aa03fb4c68b37f14cf3cce11b4737a9371725692a06385cc4f39a802e3  apps/api/app/services/horizon_selection_service.py
f77d0d2afdfda3697af0010652c3ba8ee77150f4dfa80a0f2a753a22a0fff53d  apps/api/app/services/horizon_timing_service.py
67b9dc9f2c5d38e9df7ee713d4062ac34d29c1580d9c8a37a6e664de961e33b0  apps/api/app/services/personal_fact_pack_service.py
```

Stop on mismatch. Never reset, restore, checkout paths, stash, amend, rebase or
touch architect/frozen files.

## 14. Mandatory static gates

### 14.1. Ruff and GRACE

Run exact eight-file Ruff and GRACE:

```bash
apps/api/.venv/bin/python -m ruff check \
  apps/api/app/services/horizon_claim_policy.py \
  apps/api/app/services/horizon_claim_validator.py \
  apps/api/app/services/horizon_guidance_builders.py \
  apps/api/app/services/horizon_guidance_formatter.py \
  apps/api/app/services/horizon_guidance_service.py \
  apps/api/app/services/horizon_selection_service.py \
  apps/api/app/services/horizon_timing_service.py \
  apps/api/app/services/personal_fact_pack_service.py

apps/api/.venv/bin/python scripts/test_grace_lint.py
apps/api/.venv/bin/python scripts/grace_lint.py \
  apps/api/app/services/horizon_claim_policy.py \
  apps/api/app/services/horizon_claim_validator.py \
  apps/api/app/services/horizon_guidance_builders.py \
  apps/api/app/services/horizon_guidance_formatter.py \
  apps/api/app/services/horizon_guidance_service.py \
  apps/api/app/services/horizon_selection_service.py \
  apps/api/app/services/horizon_timing_service.py \
  apps/api/app/services/personal_fact_pack_service.py
```

Require Ruff zero, GRACE self-tests 13 PASS, exact eight files clean.

### 14.2. Cold MyPy proof

```bash
cd apps/api
set +e
./.venv/bin/mypy app --no-incremental --no-error-summary --show-error-codes \
  > /tmp/stage2-w3b2-mypy-after.log 2>&1
rc=$?
set -e
test "$rc" -eq 1
```

Require:

```text
global diagnostics                  90
global failing paths                13
exact eight W3B2 paths               0
future W3B3 paths                   10 diagnostics / 2 paths unchanged
legacy baseline                     80 diagnostics / 11 paths unchanged
new or migrated diagnostics          0
```

Compare normalized diagnostics outside the exact eight edit paths against the
pre-edit cold baseline. Line shifts inside W3B2 are irrelevant only when those
diagnostics are removed; every outside-path diagnostic must remain identical.

## 15. Mandatory regression gates

### 15.1. Targeted pure-pipeline suite

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_timing_service.py \
  apps/api/tests/test_horizon_selection_service.py \
  apps/api/tests/test_horizon_selection_ordering.py \
  apps/api/tests/test_horizon_selection_benchmark.py \
  apps/api/tests/test_personal_fact_pack_service.py \
  apps/api/tests/test_horizon_guidance_formatter.py \
  apps/api/tests/test_horizon_guidance_service.py \
  apps/api/tests/test_horizon_claim_validator.py \
  apps/api/tests/test_horizon_actions_canon.py \
  apps/api/tests/test_horizon_coverage.py \
  -q
```

Require exact 10 files / 231 PASS.

### 15.2. Full API and contracts

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

Require:

```text
API full                 1405 passed / 4 skipped
contracts check          PASS_NO_DRIFT
contracts compatibility additive / zero breaking
fixture                  PASS
py-contracts             44 PASS
frontend guard           PASS
git diff check           PASS_ZERO
```

## 16. Final scope/integrity proof

Before callback require:

```text
tracked changed paths       exact 8 W3B2 service files
index                       empty
architect docs              untracked and unchanged
frozen unrelated paths      untouched/un-staged
W3B2 MyPy                   zero
global MyPy                 90 diagnostics / 13 paths
runtime behavior            unchanged
tests/contracts             green
HEAD/tracking/remote        still base SHA
main/origin-main            untouched
services                    unchanged
ports 3003/8001/18092       absent
commit/push                 not performed
```

Never touch/stage:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 17. Required callback

```text
READY_STAGE_2_W3B2_PURE_SELECTION_GUIDANCE_MYPY_REVIEW
base_head: 1e3fe7de712619bf69fc18d504293fa93d15530f
tracked_scope: EXACT_8_SERVICE_FILES
mypy_before: 118_TOTAL_21_PATHS_28_W3B2_ERRORS
mypy_w3b2_after: PASS_ZERO
mypy_total_after: 90_DIAGNOSTICS_13_PATHS
mypy_w3b3_frozen: 10_DIAGNOSTICS_2_PATHS
mypy_legacy_frozen: 80_DIAGNOSTICS_11_PATHS
mypy_new_migrated: ZERO
theme_boundary: CLOSED_RESOLVER_NO_CAST
collection_typing: GENERIC_READ_ONLY
runtime_equivalence: PASS
ruff: PASS_ZERO
grace_selftests: 13_PASS
authorized_grace: PASS_8
targeted_tests: 10_FILES_231_PASS
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

Then stop. W3B3/W3C/final RC/main/deploy remain forbidden.
