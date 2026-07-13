# Stage B2A — architect review R4: split the 998-line compressed test module

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Reviewed HEAD/origin: `3a58c581bbe010e98e78b2295a135f138d32bd88`
Parent chain: `56_...` through `59_...`
Решение: **functional behavior accepted provisionally; maintainability split required before commit**

## 0. Finding

После R3:

```text
apps/api/tests/test_horizon_selection_service.py = 998 lines
GRACE hard limit = 1000 lines
```

Чтобы остаться ниже лимита, из файла удалены обычные пустые строки между import
groups, block markers и top-level functions. Это формально зелёный lint, но
архитектурно хрупкий файл: следующий небольшой regression test сразу нарушит
лимит, а текущий код уже трудно читать/review.

Нельзя лечить size guard сжатием whitespace. Нужен semantic split.

## 1. Режим и exact allowlist

Не запускать субагентов. Git add/commit/push и B2B запрещены.

Разрешены только test paths:

```text
apps/api/tests/test_horizon_selection_service.py
apps/api/tests/test_horizon_selection_ordering.py          # new
apps/api/tests/_horizon_selection_testkit.py                # new shared non-collected helper

docs/work/2026-07-11_today-v2-real-horizons-main-deploy/60_STAGE_B2A_ARCH_REVIEW_TEST_FILE_SPLIT_R4_TZ.md
```

Read-only gates may inspect all B2A files. Production service/schema/canon files
не менять. Не менять existing test behavior/assertions кроме import/helper
relocation required by the split.

## 2. Required semantic split

### 2.1 Shared testkit

Создать:

```text
apps/api/tests/_horizon_selection_testkit.py
```

Move reusable synthetic builders only:

- activation builder;
- activation layer builder;
- scoring builder;
- three-story builder;
- control selection builder;
- candidate-from-anchor builder;
- equal-score triple population builder;
- any genuinely shared typed helper needed by both test modules.

Rules:

- filename starts `_`, pytest не должен collect it as a test module;
- no test functions inside;
- no production fixture/demo/user data import;
- no raw real user data;
- full `AI_HEADER`, module contract/map, block markers;
- function contracts for non-trivial/publicly named helpers as required by GRACE;
- side effects none;
- avoid re-export magic; explicit imports in test modules.

### 2.2 Core behavior test module

`test_horizon_selection_service.py` keeps coherent behavior/public-result tests:

- three story goldens and byte determinism;
- coherence beats raw strength and honesty fallbacks;
- exact exclusions/reasons;
- selected anchor B2B completeness/privacy;
- internal strict model validation/privacy;
- other directly service-result-oriented tests that fit this responsibility.

### 2.3 Ordering/bounds test module

Создать:

```text
apps/api/tests/test_horizon_selection_ordering.py
```

Move mechanics/invariant tests:

- pair rounding boundary;
- five pair-overlap components;
- family diversity bonus and threshold gate;
- candidate tie-break levels;
- triple tie-break levels/service lex winner;
- proof production triple helpers are used;
- inactive evidence;
- exact 256 pre-bound survivors/strength/priority/id/reverse input;
- exact diagnostics/combinations.

This module imports production helpers and shared testkit explicitly.

## 3. Formatting/size acceptance

Restore normal Python readability:

- blank line after `from __future__`;
- blank line between stdlib / third-party / local import groups;
- two blank lines between top-level functions/classes;
- blank lines around module/block markers where appropriate;
- no multiple statements per line;
- no whitespace compression to satisfy file limits.

Size targets:

```text
test_horizon_selection_service.py <= 600 lines
test_horizon_selection_ordering.py <= 650 lines
_horizon_selection_testkit.py <= 350 lines
```

If a file naturally exceeds a target, refactor helpers/parameterize repeated
cases; do not compress whitespace. Hard GRACE `<1000` alone is not acceptance.

Every module map must list real test entrypoints in that file and only semantic
blocks actually present. Remove stale block names.

## 4. Behavioral invariants

The split must be behavior-neutral:

- same production code SHA/diff before and after R4;
- all 55 focused tests still exist/pass, except pytest collection count may
  represent the same cases under the new module path;
- no test assertion removed or weakened;
- story output remains byte-identical;
- mutation-sensitive pre-bound and helper-use proofs remain intact;
- benchmark remains exact 1728 and `<100 ms`;
- no generated/public contract diff.

Run `--collect-only` before/after and prove no R3 test function disappeared.
Expected selection tests after split include all real public entrypoints from
both files.

## 5. Gates

```bash
cd apps/api
.venv/bin/python -m pytest \
  tests/test_horizon_selection_service.py \
  tests/test_horizon_selection_ordering.py \
  --collect-only -q

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

.venv/bin/python -m pytest tests/test_horizon_selection_benchmark.py -q -s

cd ../..
python3 scripts/grace_lint.py \
  apps/api/tests/_horizon_selection_testkit.py \
  apps/api/tests/test_horizon_selection_service.py \
  apps/api/tests/test_horizon_selection_ordering.py

wc -l \
  apps/api/tests/_horizon_selection_testkit.py \
  apps/api/tests/test_horizon_selection_service.py \
  apps/api/tests/test_horizon_selection_ordering.py

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

Expected full API: same exact six baseline failures, no pass-count drop caused by
lost tests. Index empty. No commit/push.

## 6. Callback

```text
READY_STAGE_B2A_REVIEW_R4
branch: preview/solarsage-v2-human-first-navigator-ux
head: 3a58c581bbe010e98e78b2295a135f138d32bd88
origin_feature: 3a58c581bbe010e98e78b2295a135f138d32bd88
production_code_changed: NO
test_split: PASS core=<lines> ordering=<lines> testkit=<lines>
whitespace_compression: REMOVED
selection_collection: PASS <cases> no_loss
mutation_proofs: PASS priority/family/triple
selection_goldens: PASS stories=3 BYTE_IDENTICAL
grace_lint: PASS 3 files maps=ACCURATE
benchmark: p95=<ms> runs=20 combinations=1728
focused_selection: <passed>
focused_b2a: <passed>
contracts_check: PASS generated_diff=ZERO
api_full: BASELINE_RED_IDENTICAL 6 failed, <passed> passed, 5 skipped
diff_paths: apps/api/tests/_horizon_selection_testkit.py, apps/api/tests/test_horizon_selection_service.py, apps/api/tests/test_horizon_selection_ordering.py
index: EMPTY
commit: NOT_YET
push: NOT_YET
```

Stop after callback. No B2B/commit/push.
