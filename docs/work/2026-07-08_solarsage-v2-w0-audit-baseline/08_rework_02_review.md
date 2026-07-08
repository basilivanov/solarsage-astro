# Wave W0 Rework 02 Architect Review

Status: REWORK REQUIRED

Reviewed HEAD: `409421f35d8cea262e47b720386d4454ecffbc45`
Implementation commit: `886bd601e42b850d106efc819a07d3e1a88d922b`

## Passed Checks

```bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_astronomy_oracle.py \
  apps/api/tests/test_semantic_contexts.py \
  apps/api/tests/test_today_concrete_advice_consistency.py \
  apps/api/tests/test_today_concrete_advice.py \
  apps/api/tests/test_day_endpoints.py \
  apps/api/tests/test_calendar_endpoints.py \
  -q
```

Result: `36 passed, 1 warning`.

```bash
cd apps/solarsage && venv/bin/python -m pytest \
  tests/test_ephemeris_retrograde.py \
  tests/test_services.py \
  -q
```

Result: `5 passed`.

Current committed artifacts prove:

- `12_scoring_oracle_comparison.json.comparison.day_status.pass=true`
- `12_scoring_oracle_comparison.json.comparison.top_signals.pass=true`
- no failed sphere scores
- `13_astronomy_oracle_summary.json.retrograde_flag_pass=true`
- `13_astronomy_oracle_summary.json.moon_phase.pass=true`
- `11_final_today_payload.json.meta.content_version=6`
- `11_final_today_payload.json.meta.cached=false`
- lunar phase fact is `Убывающая Луна 44%`

## Findings

### P1 — dynamic claims report reads camelCase but payload is snake_case

`scripts/audit_today.py` serializes the payload with:

```python
payload_json = today_payload.model_dump(mode="json", by_alias=False)
```

So the actual keys are snake_case:

```text
day_summary
top_flags
concrete_advice
```

But the claims generator reads camelCase:

```python
payload_json.get("daySummary")
payload_json.get("topFlags")
payload_json.get("concreteAdvice")
```

The committed `14_claims_audit.md` therefore still contains placeholders instead of actual production evidence:

```text
- Moon Phase Fact: "N/A"
- Top Flags: N/A
| N/A | N/A | N/A |
```

Required:

- Fix the generator to read both snake_case and camelCase defensively, with snake_case matching the current serializer.
- Regenerate `artifacts/audit/2026-07-08/14_claims_audit.md`; it must include actual lunar phase, top flags, and all 12 concrete advice rows.
- Add a regression test or small script-level test that would fail if the claims report renders `N/A` while the payload contains those fields.

### P2 — whitespace hygiene checked only the report commit, not the final range/tree

`git show --check HEAD` is clean because HEAD is only the report commit. But the implementation commit and final diff still contain whitespace errors:

```bash
git show --check 886bd601e42b850d106efc819a07d3e1a88d922b
git diff 6cc4f16..886bd60 --check
```

Both report trailing whitespace in:

- `apps/api/tests/test_astronomy_oracle.py`
- `scripts/audit_today.py`
- `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/05_rework_01_review.md`

Required:

- Remove trailing whitespace from the final tree.
- Verify `git diff 2f9173f..HEAD --check` passes, not only `git show --check HEAD`.
- Keep `git show --check HEAD` passing too.
