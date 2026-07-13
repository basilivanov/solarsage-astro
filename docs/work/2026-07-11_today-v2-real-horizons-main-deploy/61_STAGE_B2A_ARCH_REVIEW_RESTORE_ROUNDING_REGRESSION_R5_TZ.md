# Stage B2A — architect review R5: restore the lost seventh-decimal regression

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Parent: `60_STAGE_B2A_ARCH_REVIEW_TEST_FILE_SPLIT_R4_TZ.md`
Решение: **split accepted; one weakened assertion must be restored**

## 0. Exact scope

Не запускать субагентов. Git add/commit/push и B2B запрещены.

Разрешено менять только:

```text
apps/api/tests/test_horizon_selection_ordering.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/61_STAGE_B2A_ARCH_REVIEW_RESTORE_ROUNDING_REGRESSION_R5_TZ.md
```

Production code, testkit, core test module, canon/contracts/runtime не менять.

## 1. Regression lost during R4 split

До split `test_pair_overlap_rounds_before_threshold_comparison` использовал
custom typed canon:

```text
same_target weight      = 0.1000004
long_medium threshold  = 0.1000003
```

Production pair score должен сначала округлиться до `0.100000`, и только это
значение сравнивается с threshold. Поэтому:

```text
pair_score == 0.1
pair_score < 0.1000003
```

После R4 test заменён на обычный `round(0.1 + 0.2, 6) == 0.3`. Он не отличает:

- правильное сравнение rounded score;
- ошибочное сравнение raw `0.1000004`, которое прошло бы threshold.

Это нарушает R4 invariant “assertions not removed or weakened”.

## 2. Required correction

В `test_horizon_selection_ordering.py` восстановить mutation-sensitive test:

1. Test принимает `monkeypatch`.
2. Берёт `load_horizon_selection_canon().model_dump()`.
3. Устанавливает convex story weights:

```py
{
    "same_target": 0.1000004,
    "shared_theme": 0.8999996,
    "shared_product_sphere": 0.0,
    "same_planet_or_house": 0.0,
    "shared_technical_sphere": 0.0,
}
```

4. Устанавливает `min_pair_overlap.long_medium = 0.1000003`.
5. Валидирует custom data через `HorizonSelectionCanon.model_validate`.
6. Monkeypatches именно production module
   `app.services.horizon_selection_service.load_horizon_selection_canon`.
7. Builds two valid candidates where only exact target category is shared:
   no shared theme/product/technical sphere and no planet/house intersection.
8. Calls production `_pair_overlap`.
9. Asserts exactly:

```py
assert pair_score == 0.1
assert pair_score < custom_canon.min_pair_overlap.long_medium
```

Можно дополнительно оставить `0.1 + 0.2` smoke assertion, но оно не заменяет
seventh-decimal proof.

Add/retain exact GRACE function contract and normal formatting. File remains
`<=650` lines.

## 3. Gates

```bash
cd apps/api
.venv/bin/python -m pytest \
  tests/test_horizon_selection_ordering.py::test_pair_overlap_rounds_before_threshold_comparison -q
.venv/bin/python -m pytest \
  tests/test_horizon_selection_service.py \
  tests/test_horizon_selection_ordering.py -q
.venv/bin/python -m pytest \
  tests/test_canon_service.py \
  tests/test_horizon_canon_service.py \
  tests/test_horizon_timing_service.py \
  tests/test_horizon_sphere_mapping_service.py \
  tests/test_horizon_selection_service.py \
  tests/test_horizon_selection_ordering.py \
  tests/test_horizon_selection_benchmark.py -q

cd ../..
python3 scripts/grace_lint.py apps/api/tests/test_horizon_selection_ordering.py
wc -l apps/api/tests/test_horizon_selection_ordering.py
pnpm contracts:check
git diff --exit-code -- packages/contracts/src/generated apps/api/openapi.json
git diff --check

cd apps/api
.venv/bin/python -m pytest tests -q

cd ../..
git diff --cached --name-only
git status --short
```

Expected full API: exact same six baseline failures; no pass-count drop. Index
empty. No commit/push.

## 4. Callback

```text
READY_STAGE_B2A_REVIEW_R5
branch: preview/solarsage-v2-human-first-navigator-ux
head: 3a58c581bbe010e98e78b2295a135f138d32bd88
origin_feature: 3a58c581bbe010e98e78b2295a135f138d32bd88
seventh_decimal_raw: 0.1000004
stored_pair_score: 0.1
threshold: 0.1000003
rounded_before_threshold: PASS
selection_split: PASS core=<lines> ordering=<lines> testkit=<lines>
focused_selection: <passed>
focused_b2a: <passed>
grace_lint: PASS
contracts_check: PASS generated_diff=ZERO
api_full: BASELINE_RED_IDENTICAL 6 failed, <passed> passed, 5 skipped
diff_paths: apps/api/tests/test_horizon_selection_ordering.py
index: EMPTY
commit: NOT_YET
push: NOT_YET
```

Stop after callback. No B2B/commit/push.
