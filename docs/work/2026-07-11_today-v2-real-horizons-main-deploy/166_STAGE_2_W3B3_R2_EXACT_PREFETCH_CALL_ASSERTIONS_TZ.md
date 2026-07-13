# Stage 2.W3B3 R2 — exact prefetch child-call assertions

Дата: `2026-07-13`

Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`a0646a0b2d02f3a40c209a45286cb60d0d846a91`

Parents:

- `164_STAGE_2_W3B3_R1_PREFETCH_AND_BOUNDARY_CORRECTION_TZ.md`;
- `165_STAGE_2_W3B3_R1A_EXACT_STALE_MOCK_AND_GATE_AMENDMENT_TZ.md`.

Статус: **ARCHITECT R1A REVIEW — ONE TEST-ONLY R2 REQUIRED, NO COMMIT/PUSH**

No subagents, delegation or background coding/review agents.

## 1. Accepted result so far

Architect independently confirmed:

```text
tracked scope                 exact 7
Ruff                         PASS 7
GRACE self-tests             13 PASS
GRACE changed paths          PASS 7
cold MyPy diagnostics        80
feature production errors    0
focused tests                68 PASS
W3B3 targeted tests          226 PASS
git diff --check             PASS
```

Production implementation, schemas, semantic service, access identity,
SessionLocal prefetch, task ownership, per-day failure boundary and the two
canonical SemanticLayer test doubles are accepted and byte-frozen for R2.

## 2. Exact edit scope

Edit only:

```text
apps/api/tests/test_today_preview_transport.py
```

All other six tracked paths are byte-frozen. Final tracked scope remains exact
seven files. Do not touch architect docs, frozen unrelated paths, index,
runtime services or ports.

## 3. Missing proof

The upgraded test currently proves fresh DB-session identities and the date
set, but this loop is permissive:

```python
for _, _, kwargs in child_calls:
    assert kwargs.get("skip_prefetch") is True
    assert "selection_context" not in kwargs
```

It does not fail if:

- the wrong `user_id` is passed;
- non-`None` access state is passed;
- extra positional arguments are added;
- any extra keyword argument other than `selection_context` is added.

Doc 165 required the exact child call contract.

## 4. Exact correction

In `test_prefetch_week_never_propagates_preview_context`, replace only that
per-call loop with an exact assertion equivalent to:

```python
for child_db, args, kwargs in child_calls:
    assert child_db is not request_db
    assert args == (user_id, args[1], None)
    assert kwargs == {"skip_prefetch": True}
```

The existing date-set assertion immediately below continues to prove that
`args[1]` is exactly one of `today-3 ... today+3`; the tuple equality proves
exact arity, exact user ID and `access_state is None`. Exact kwargs equality
also proves `selection_context` and every other extra kwarg are absent.

Keep the existing `child_dbs` / `created` identity assertions. Do not weaken or
remove any lifecycle assertion.

No semicolons, helper abstraction, source-string assertion or new test.

The file is currently 999 lines. Keep it at or below 1000 with at most the
minimum blank-line-only deletion required by the one-line net growth. Do not
change any other token or assertion outside this exact test.

## 5. Required gates

Run from repo root:

```bash
apps/api/.venv/bin/python -m ruff check \
  apps/api/tests/test_today_preview_transport.py

apps/api/.venv/bin/python scripts/grace_lint.py \
  apps/api/tests/test_today_preview_transport.py

PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_preview_transport.py::test_prefetch_week_never_propagates_preview_context \
  -q

PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_day_no_birthday_fallback.py \
  apps/api/tests/test_today_preview_transport.py \
  apps/api/tests/test_wave3_day_pipeline_reuse.py \
  -q
```

Require:

```text
Ruff                         PASS
GRACE                        PASS
exact prefetch test          1 PASS
focused three-file suite     68 PASS
file lines                   <= 1000
git diff --check             PASS
tracked scope                exact 7
index                        empty
```

No need to rerun full API, contracts or cold MyPy for this assertion-only R2;
architect will run final independent release gates after callback.

## 6. Callback and stop

```text
READY_STAGE_2_W3B3_R2_ARCH_REVIEW
edit_scope: EXACT_1_TEST_FILE
prefetch_child_positional_contract: EXACT_USER_DATE_NONE
prefetch_child_keyword_contract: EXACT_SKIP_PREFETCH_TRUE_ONLY
prefetch_session_identity: PRESERVED
prefetch_date_set: PRESERVED_EXACT_7
today_preview_transport_lines: N_LE_1000
ruff: PASS
grace: PASS
prefetch_test: 1_PASS
focused_tests: 68_PASS
git_diff_check: PASS_ZERO
final_tracked_scope: EXACT_7_FILES
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
```

Then stop. No commit or push.
