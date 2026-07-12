# Stage B2A — architect review R3: mutation-adequate ordering proofs

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Reviewed HEAD/origin: `3a58c581bbe010e98e78b2295a135f138d32bd88`
Parent chain: `56_...`, `57_...`, `58_...`
Решение: **B2A ещё не accepted; два R2 tests не ловят mutation production behavior**

## 0. Режим и allowlist

Не запускать субагентов. До acceptance запрещены git add/commit/push и B2B.

Разрешены только:

```text
apps/api/app/services/horizon_selection_service.py
apps/api/tests/test_horizon_selection_service.py

docs/work/2026-07-11_today-v2-real-horizons-main-deploy/59_STAGE_B2A_ARCH_REVIEW_MUTATION_ADEQUACY_R3_TZ.md
```

Плюс read-only gates по остальному репозиторию. Canon values, schemas, timing,
mapping, contracts, frontend, sidecar и runtime не менять.

## 1. Finding A — pre-bound fixture не проверяет technique priority

Independent mutation probe для текущего R2 fixture:

```text
documented sort:
  strength desc, max technique priority desc, activation id lex

mutated sort:
  strength desc, activation id lex

same_survivors: True
same_full_order: True
```

Причина: у всех элементов с одинаковой strength одна и та же technique, поэтому
secondary priority key никогда не сравнивается.

### Required correction

Изменить/дополнить `test_input_prebound_exact_survivors_and_determinism` так,
чтобы cutoff зависел именно от max technique priority.

Recommended deterministic construction:

1. 255 entries с большей strength, которые гарантированно занимают 255 мест.
2. Несколько boundary entries с **одинаковой strength**, но разными techniques:

```text
annual_profection max priority 1.00, lexically late id
firdar_major      max priority 0.96
solar_return      max priority 0.92
monthly_profection max priority 0.86, lexically early id
```

3. Остался ровно один 256-й slot.
4. Assert survivor — annual_profection despite lexically later ID.
5. Assert lexically earlier lower-priority entries dropped.

Отдельно prove tertiary ID tie:

- same strength;
- same technique/max priority;
- fewer remaining slots than entries;
- exact lexicographically smallest IDs survive.

Strength primary key также должен иметь direct cutoff assertion: stronger entry
survives over lexically earlier weaker entry.

Reverse input and prove exact same ordered 256 classification/mapping IDs.

Test expected order may calculate the documented tuple, but its fixture must be
mutation-sensitive: add an explicit assertion demonstrating that priority-free
ordering would produce a different boundary survivor/order. Это assertion над
test design, не вызов production implementation.

## 2. Finding B — family/triple tests проверяют test copy, не production

Current tests:

- manually assign `family_diversity_score` and `total_score` to typed triples;
- compare a test-local `_triple_sort_key` that duplicates the intended tuple;
- only final lex winner is exercised through `HorizonSelectionService`.

If production removes the `0.05` family bonus or swaps the first four sort-key
levels, these tests still pass. Поэтому callback claims
`family_diversity: PASS bonus` and `triple_tie_break: PASS 5 levels` are not yet
mutation-adequate.

### Required production refactor, behavior-preserving

В `horizon_selection_service.py` extract private pure helpers and make production
selection call them:

```py
def _family_diversity_score(unique_family_count: int) -> float:
    ... exact clamp((count - 1) / 2, 0, 1), round6 ...

def _triple_total_score(
    *,
    mean_impact: float,
    mean_overlap: float,
    family_diversity_score: float,
) -> float:
    ... load/use current canon triple weights, exact weighted sum, round6 ...

def _triple_sort_key(
    *,
    total_score: float,
    mean_overlap: float,
    mean_impact: float,
    unique_family_count: int,
    activation_ids: tuple[str, str, str],
) -> tuple[float, float, float, int, tuple[str, str, str]]:
    ... exact production ordering ...
```

Acceptable alternative signatures are allowed only if semantics remain pure,
typed and obvious. No DB/network/clock/logging. Add GRACE function contracts.

Production loop must call these helpers; no duplicated inline formula/sort tuple
may remain. Do not export through a public schema/package barrel; private module
helpers are sufficient.

### Required test correction

1. Import/call the production helpers from the service module.
2. Remove test-local `_triple_sort_key` duplicate.
3. Family diversity test proves from production helpers:

```text
count=1 -> 0.0
count=2 -> 0.5
count=3 -> 1.0

same mean impact/overlap:
score(count=3) - score(count=1) == 0.05
```

Also retain the real service proof that max diversity cannot bypass pair
threshold.

4. Triple tie test calls production `_triple_sort_key` and isolates all levels:

```text
total score desc
mean overlap desc
mean impact desc
unique family count desc
activation id tuple lex
```

Retain real service lex winner as end-to-end proof.

5. Add one source-inspection-independent assertion by monkeypatching or direct
helper use sufficient to fail if production reverts to an inline different
tuple/formula. The critical requirement is that service uses the same helpers
the tests call.

## 3. No behavior changes

Expected:

- selected goldens and every serialized result byte-identical before/after;
- benchmark remains under 100 ms and combinations exactly 1728;
- no score/canon/threshold changes;
- only refactor for single-source-of-truth and mutation-sensitive fixtures.

Capture before/after JSON for all three existing story goldens inside a test or
prove existing byte-exact golden assertions still pass. Do not regenerate public
fixtures/contracts.

## 4. Gates

```bash
cd apps/api
.venv/bin/python -m pytest tests/test_horizon_selection_service.py -q
.venv/bin/python -m pytest \
  tests/test_canon_service.py \
  tests/test_horizon_canon_service.py \
  tests/test_horizon_timing_service.py \
  tests/test_horizon_sphere_mapping_service.py \
  tests/test_horizon_selection_service.py \
  tests/test_horizon_selection_benchmark.py -q
.venv/bin/python -m pytest tests/test_horizon_selection_benchmark.py -q -s

cd ../..
python3 scripts/grace_lint.py \
  apps/api/app/services/horizon_selection_service.py \
  apps/api/tests/test_horizon_selection_service.py
pnpm contracts:check
git diff --exit-code -- packages/contracts/src/generated apps/api/openapi.json
git diff --check

cd apps/api
.venv/bin/python -m pytest tests -q

cd ../..
git diff --cached --name-only
git status --short
git diff --name-only
git ls-files --others --exclude-standard
```

Expected full API: exact same six baseline failures; pass count does not drop.
Index empty; no commit/push.

## 5. Callback

```text
READY_STAGE_B2A_REVIEW_R3
branch: preview/solarsage-v2-human-first-navigator-ux
head: 3a58c581bbe010e98e78b2295a135f138d32bd88
origin_feature: 3a58c581bbe010e98e78b2295a135f138d32bd88
prebound_strength_cutoff: PASS
prebound_priority_cutoff: PASS mutation_sensitive
prebound_id_cutoff: PASS
prebound_reverse_order: PASS exact_256
family_diversity_helper: PASS 0.0/0.5/1.0 bonus=0.05
triple_total_helper_used_by_production: PASS
triple_sort_helper_used_by_production: PASS levels=5
threshold_bypass: REJECTED
service_lex_winner: PASS
goldens: PASS stories=3 BYTE_IDENTICAL
grace_lint: PASS
benchmark: p95=<ms> runs=20 combinations=1728
focused: <passed>
contracts_check: PASS generated_diff=ZERO
api_full: BASELINE_RED_IDENTICAL 6 failed, <passed> passed, 5 skipped
diff_paths: apps/api/app/services/horizon_selection_service.py, apps/api/tests/test_horizon_selection_service.py
index: EMPTY
commit: NOT_YET
push: NOT_YET
```

Stop after callback. No B2B, commit or push.
