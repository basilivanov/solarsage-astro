# S2.W1 Acceptance — real timing truth accepted

Дата: 2026-07-12  
Ветка: `preview/solarsage-v2-human-first-navigator-ux`  
Reviewed HEAD/origin: `1f8fc1e2e0e7ddcb96706a1934f65eb5ea4f20e4`  
Implementation TZ: `36_S2_W1_REAL_TIMING_IMPLEMENTATION_TZ.md`  
Correction reviews: `39_S2_W1_ARCH_REVIEW_R1.md`,
`42_S2_W1_ARCH_REVIEW_R2.md`  
Статус: **ACCEPTED FOR SCOPED COMMIT/PUSH**.

## 1. Принятый результат

Архитектурный review подтверждает, что S2.W1 теперь корректно реализует:

- реальные transit orb-window boundaries;
- exact occurrence enumeration и consistent phase/applying;
- truthful `plus|minus` branch debug;
- successful near-miss channel отдельно от typed failure warnings;
- один request-scoped solver и position cache;
- lazy outward grids, расширяемые только до первого outside текущего window;
- annual/monthly profection local-date boundaries;
- firdar major/minor inverse fractional-age boundaries;
- current/next solar return windows;
- current/next lunar return windows со строгим `next > current`;
- одинаковый timing для всех evidence одного period/return;
- byte-for-byte preservation через API sidecar validation;
- version identity `ss-calc-1.2.0`, `al-1.1`, `ss-scoring-2.0`;
- generated OpenAPI/TypeScript/Zod default drift только `al-1.0 -> al-1.1`.

Transit IDs, existing orb/strength/polarity и unsupported-technique null timing
сохранены по контракту.

## 2. Независимые architect gates

### 2.1 Sidecar

```text
focused: 132 passed, 1 warning
full:    199 passed, 1 warning
```

Дополнительный real full-request invariant audit:

```text
transit timing checked:     101
date period timing checked: 6
return timing checked:      13
planet-in-house null timing:10
```

Все target/window/exact invariants прошли.

### 2.2 API

```text
focused S2.W1 suite: 121 passed
full suite: 6 failed, 830 passed, 5 skipped
```

Шесть full-suite failures побайтно/по traceback совпадают с detached clean
base SHA и не затрагивают S2.W1 paths:

```text
test_calendar_status_cache_duplicate_rereads_winning_row
test_semantic_v2_service_no_convergence
test_semantic_v2_service_with_convergence
test_audit_canon_versions_only_contains_strings
test_techniques_list_is_sorted
test_today_payload_v2_block_included_when_flag_enabled
```

Для этой волны принят differential gate `BASELINE_RED_IDENTICAL`. Перед
финальным merge/deploy эти baseline failures обязательны к исправлению отдельной
scoped wave; release gate `all tests green` не ослабляется.

### 2.3 Contracts/frontend static

```text
contract Vitest: 128 passed
TypeScript typecheck: PASS
git diff --check: PASS
index: EMPTY
binary diff paths: none
```

Double generation hashes совпали:

```text
openapi.json:
bc4c9f93cee4c45e67cc568ea35c13716079ac818bbd2a558b1d23f7859e98ff

_generated.ts:
8027ad45c4077318b2c5eafc4b0f1ec1cb61fc9dd319cd106195a03a21d2163f

_generated.zod.ts:
bed54dd3c09adfe502538747a8c18fd8b059855a43a98783dd385755fb8b33f6
```

Generated diff содержит ровно три default replacements и не переобъявляет
timing fields.

### 2.4 Independent performance run

Protocol: 3 warm-up + 20 measured builds, один Python process.

```text
runs:               20
p50:                299.72 ms
p95:                352.91 ms
max:                367.76 ms
activations:        144
transit aspects:    101
cache misses:       7253
cache hits:         58339
unique cache keys:  7253
```

Acceptance `p95 < 2000 ms` выполнен с большим запасом. Lazy-grid уменьшил
cache misses с `29335` до `7253` без изменения real timing output.

## 3. Review conclusions

Blocking findings R1/R2 закрыты:

- ложный always-plus debug удалён;
- success/fallback debug channels разделены;
- mandatory integration matrix добавлена;
- full-horizon grid precompute заменён lazy expansion;
- lunar helper явно отклоняет `jd <= after_jd`;
- builder проверяет `current <= target < next`;
- solar pre/post birthday tests используют полные UTC-Z timestamps;
- Feb-29 current/next pair и one-full-chart reuse доказаны;
- firdar integer boundary доказан;
- новые imports и GRACE side-effect descriptions приведены в порядок.

Новых blocking defects в S2.W1 diff не найдено.

## 4. Разрешение и ограничения следующего шага

Разрешён только отдельный scoped commit/push по последующему commit TZ.

До него и во время него запрещено:

- добавлять Stage A/Stage B product implementation;
- исправлять baseline API failures;
- включать unrelated untracked paths;
- менять runtime/systemd/nginx/ports;
- squash/rebase/merge;
- отправлять неописанные файлы.

После accepted commit из чистого worktree обязателен:

```bash
pnpm contracts:check
```

Он должен вернуть `0`. Pre-commit expected drift больше не является допустимым
после commit.

## 5. Unrelated paths, которые обязаны остаться вне commit

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Acceptance не является разрешением на merge в `main` или production deploy.
