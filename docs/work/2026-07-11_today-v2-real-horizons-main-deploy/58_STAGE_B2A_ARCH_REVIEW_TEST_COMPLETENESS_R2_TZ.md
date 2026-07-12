# Stage B2A — architect review R2: complete the stated invariant matrix

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Reviewed HEAD/origin: `3a58c581bbe010e98e78b2295a135f138d32bd88`
Parent: `56_STAGE_B2A_CANON_TIMING_SELECTION_TZ.md`
Previous correction: `57_STAGE_B2A_ARCH_REVIEW_CORRECTIONS_TZ.md`
Решение: **реализация R1 функционально близка к acceptance, но обязательная test matrix ещё не доказана**

## 0. Режим

Кодер выполняет только эту короткую correction wave. Не запускать субагентов.
До architect acceptance запрещены `git add`, commit, push и B2B.

Основная задача R2 — добавить недостающие изолированные proofs. Production code
не менять, если новый точный test не выявил реальный defect. Если выявил —
исправить минимально в текущем B2A allowlist и явно описать в callback.

## 1. Allowlist

Основные разрешённые файлы:

```text
apps/api/tests/test_horizon_canon_service.py
apps/api/tests/test_horizon_timing_service.py
apps/api/tests/test_horizon_sphere_mapping_service.py
apps/api/tests/test_horizon_selection_service.py
apps/api/tests/test_horizon_selection_benchmark.py
```

Только если новый test доказал реальную ошибку, разрешены:

```text
apps/api/app/schemas/horizon_canon.py
apps/api/app/schemas/horizon_selection.py
apps/api/app/services/horizon_canon_service.py
apps/api/app/services/horizon_timing_service.py
apps/api/app/services/horizon_sphere_mapping_service.py
apps/api/app/services/horizon_selection_service.py
grace/canon/horizon_selection.v1.yml
```

Documentation allowlist:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/58_STAGE_B2A_ARCH_REVIEW_TEST_COMPLETENESS_R2_TZ.md
```

Не менять `canon_service.py`, `test_canon_service.py`, public contracts,
OpenAPI, frontend, sidecar, Today/Semantic integration, env/runtime/ports.

Всегда игнорировать:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 2. Почему R1 callback пока не acceptance

R1 закрыл основные implementation defects и дал зелёные gates:

```text
focused: 42 passed
GRACE: 11 files clean
benchmark p95: 17.023 ms
full API: exact same 6 baseline failures
```

Но callback `selection_matrix: PASS 10` не соответствует exact обязательным
proof из TZ 56/57. В текущих tests отсутствуют отдельные проверки:

- пяти pair-overlap компонентов;
- family diversity как tie/bonus и невозможности обойти overlap threshold;
- candidate и triple stable tie-break;
- exact survivors при input `>256`;
- inactive evidence;
- exact tolerance/peaked transition boundaries;
- unexpected target-clock helper fault propagation;
- части canon negative matrix;
- independent lexicographic sphere tie и видимого target/source theme order.

Aggregated golden не заменяет isolated component proof. Тест, в котором
одновременно истинны несколько overlap categories, не доказывает вес каждой
категории и правило “каждый category weight используется один раз”.

## 3. Exact missing canon proofs

В `test_horizon_canon_service.py` добавить отдельные mutations/assertions:

1. Unknown horizon in a technique rule, например `allowed_horizons: [long, warp]`.
2. Unknown transit speed group `warp`.
3. Same normalized planet in two speed groups.
4. Duplicate planet member within one speed group.
5. Missing key from `technical_sphere_themes`.
6. Duplicate theme ID in technical themes.
7. Duplicate theme ID in target-planet themes.
8. Invalid theme ID pattern.
9. Product union missing one public product while all nine technical keys remain
   present (не только missing technical key/unknown Literal).
10. `nan` and `inf` in each convex group family: impact, story overlap, triple
    score; prove failure is finite/range, not only wrong sum.

Use the existing copy/mutation helper. Не создавать 10 почти одинаковых test
files; один table/loop допустим, но callback должен считать individual mutation
cases.

Also correct `START_MODULE_MAP` so `public_entrypoints` names correspond to real
functions in the file. Current map contains stale/nonexistent names.

## 4. Exact missing timing proofs

В `test_horizon_timing_service.py` добавить:

### 4.1 Instant exact tolerance boundary

For canon tolerance `3600` seconds prove:

```text
exact_at - 3600s -> exact
exact_at + 3600s -> exact
exact_at - 3601s -> building
exact_at + 3601s -> peaked (while inside peak window)
```

### 4.2 Peaked/fading exact transition

Build an instant window where computed peak tail is exactly 12 hours. Prove:

```text
exact_at + 12h       -> peaked
exact_at + 12h + 1s  -> fading
```

Both targets must still be inside `active_until`.

### 4.3 Date precision peak states

Use a `timing_mode=peak` technique with date-only evidence. Prove at least:

```text
day before exact -> building
exact day -> exact
first post-exact day within calculated peak tail -> peaked
later inside day -> fading
```

### 4.4 Target-clock programming error

Monkeypatch `_parse_target_clock` to raise unexpected `RuntimeError` and prove:

- `HorizonTimingService.classify()` propagates it;
- `HorizonSelectionService.select()` propagates it;
- neither converts it to `invalid_target_clock`.

The existing `_duration_matches` RuntimeError test remains; it does not replace
the target-clock catch proof.

Update timing test module map to include every real public test entrypoint,
including `test_no_server_clock_dependency` and the new boundary test(s).

## 5. Exact missing sphere-mapping proofs

В `test_horizon_sphere_mapping_service.py` добавить:

### 5.1 Independent lexicographic tie

At least two technical spheres have:

```text
same linked absolute amount
same final_score
different technical keys
```

Assert exact lexicographic technical order. Current test proves amount then
final_score, but not the third independent tie-break.

### 5.2 Visible target then source theme order

Choose one technical sphere and target/source planets so all three contributed
theme IDs are distinct and fit before truncation. Assert exact order:

```text
technical themes
then target planet themes
then source planet themes
```

Current test's source theme is duplicate/truncated and therefore cannot prove
source ordering.

### 5.3 Unrelated contribution isolation

Add a mismatched/non-finite or differently keyed contribution belonging to a
different `source_id`; prove it is not inspected as the selected activation's
amount and does not change result. Do not weaken outer `SphereScoreV2.key`
invariant, which is global and must still fail fast.

## 6. Exact missing selection proofs

В `test_horizon_selection_service.py` добавить isolated helpers/tests. Reuse
typed candidates from a valid selected result where practical.

### 6.1 Five pair-overlap components in isolation

For each case make exactly one category true and every other category false:

```text
same normalized target type+key       -> 0.35
shared theme                          -> 0.25
shared product sphere                 -> 0.20
planet intersection or same house     -> 0.10
shared technical sphere               -> 0.10
```

Then make multiple values overlap inside each category and prove that category
weight is still added only once. Finally prove all five categories together
clamp/sum to exactly `1.0`.

Do not infer expected values from the service result alone; assert against the
committed canon values or exact numeric intent.

### 6.2 Family diversity

Prove both:

1. With equal mean impact/overlap, a triple with three independent technique
   families gets the exact diversity bonus and ranks above a less diverse one.
2. A triple with pair overlap below threshold remains rejected even with maximum
   family diversity. Diversity cannot bypass coherence thresholds.

### 6.3 Candidate stable tie-break

Construct candidates with equal impact, timing completeness, strength and
technique priority. Assert lower `activation_id` sorts first. Also isolate one
tie level at a time where useful so the tuple order is proven, not merely ID.

### 6.4 Triple stable tie-break

Create at least two valid coherent equal-score triples and assert exact winner by:

```text
total score desc
mean overlap desc
mean impact desc
unique family count desc
(long_id, medium_id, fast_id) lex
```

It is acceptable to cover the first four using focused pure sort-key examples
and the final lex case through service selection, but every ordered level must
have a direct assertion.

### 6.5 Inactive evidence

Add an inactive evidence stronger than active candidates. Prove:

- it is not classified/mapped/candidate-selected;
- `input_count` includes it;
- `active_count` excludes it;
- selected IDs and byte-deterministic result are unchanged versus input without
  that inactive item.

### 6.6 Exact deterministic input pre-bound

For `>256` active inputs:

- record which IDs reach timing/mapping classification;
- compute expected 256 survivors from exact sort:
  strength desc, max technique priority desc, activation ID lex;
- assert exact survivor list/set;
- assert exact four or more dropped IDs;
- repeat with reversed/shuffled input and prove same survivors/result;
- assert `classified_count=256` and `input_truncated=true`.

The current count-only test is insufficient because a wrong 256-subset could
still pass it.

### 6.7 Exact diagnostics/combinations

For a small known population assert:

```text
candidate_count == sum(pre counts)
post count == min(pre count, 12) per horizon
combinations_evaluated == post_long * post_medium * post_fast
```

For the existing 12x12x12 benchmark assert exact `1728`, not only `<=1728`.

### 6.8 Module map accuracy

Update `START_MODULE_MAP` public entrypoint names. It currently contains
`test_selection_diagnostics_rounding_and_exact_fallbacks`, which does not exist,
and omits real tests.

Remove the unused `json` import while touching this test file.

## 7. Product-code policy

Expected outcome is tests-only plus module-map cleanup. If any new proof fails:

1. capture the exact failing assertion;
2. fix only the smallest B2A implementation defect;
3. add a regression assertion;
4. report the changed production path and reason in callback.

Do not change current canon numeric values/thresholds to make a test pass.

## 8. Gates

### 8.1 Focused and collection evidence

```bash
cd apps/api
.venv/bin/python -m pytest \
  tests/test_canon_service.py \
  tests/test_horizon_canon_service.py \
  tests/test_horizon_timing_service.py \
  tests/test_horizon_sphere_mapping_service.py \
  tests/test_horizon_selection_service.py \
  tests/test_horizon_selection_benchmark.py -q

.venv/bin/python -m pytest \
  tests/test_horizon_canon_service.py \
  tests/test_horizon_timing_service.py \
  tests/test_horizon_sphere_mapping_service.py \
  tests/test_horizon_selection_service.py \
  --collect-only -q
```

### 8.2 GRACE

```bash
python3 scripts/grace_lint.py \
  apps/api/app/schemas/horizon_canon.py \
  apps/api/app/schemas/horizon_selection.py \
  apps/api/app/services/horizon_canon_service.py \
  apps/api/app/services/horizon_timing_service.py \
  apps/api/app/services/horizon_sphere_mapping_service.py \
  apps/api/app/services/horizon_selection_service.py \
  apps/api/tests/test_horizon_canon_service.py \
  apps/api/tests/test_horizon_timing_service.py \
  apps/api/tests/test_horizon_sphere_mapping_service.py \
  apps/api/tests/test_horizon_selection_service.py \
  apps/api/tests/test_horizon_selection_benchmark.py
```

Expected: zero violations and accurate module maps by review.

### 8.3 Benchmark

```bash
cd apps/api
.venv/bin/python -m pytest tests/test_horizon_selection_benchmark.py -q -s
```

Expected: p95 `<100 ms`, runs=20, combinations exactly `1728`.

### 8.4 Contract/full regression/scope

```bash
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

Expected full API: same exact six baseline failures only; pass count increases.
Index empty. No commit/push.

## 9. Callback

```text
READY_STAGE_B2A_REVIEW_R2
branch: preview/solarsage-v2-human-first-navigator-ux
head: 3a58c581bbe010e98e78b2295a135f138d32bd88
origin_feature: 3a58c581bbe010e98e78b2295a135f138d32bd88
production_code_changed: NO | YES <exact path/reason>
canon_negative_matrix: PASS <individual cases>
timing_boundary_matrix: PASS <individual cases>
mapping_order_matrix: PASS <individual cases>
pair_components: PASS 5 isolated + once-only + all
family_diversity: PASS bonus + no-threshold-bypass
candidate_tie_break: PASS <levels>
triple_tie_break: PASS <levels>
inactive_evidence: PASS
input_prebound: PASS exact_survivors=256 deterministic
diagnostics: PASS exact counts combinations=1728
selection_goldens: PASS stories=3 BYTE_IDENTICAL
privacy: PASS
grace_lint: PASS app=6 tests=5 maps=ACCURATE
benchmark: p95=<ms> runs=20 combinations=1728
focused: <passed>
contracts_check: PASS generated_diff=ZERO
api_full: BASELINE_RED_IDENTICAL 6 failed, <passed> passed, 5 skipped
diff_paths: <exact paths>
index: EMPTY
commit: NOT_YET
push: NOT_YET
```

Stop after callback. Do not begin B2B and do not commit/push.
