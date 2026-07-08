# Architect Acceptance: Wave W0 SolarSage V2 Audit Baseline

Status: ACCEPTED

Accepted commit: `0c92ba43a4e312992f22cea5d195af03d17f816c`
Implementation commit: `e920420e9e9f32c205ef80fe8281b312963bf836`
Source TZ: `docs/15_SolarSage_v2_activation_audit_TZ.md`

## Scope Accepted

Wave W0 is accepted as the independent audit harness and P0 trust-fix baseline before SolarSage V2 implementation.

Accepted deliverables:

- canonical `make audit-day USER_ID=... DATE=2026-07-08`;
- committed audit artifact tree under `artifacts/audit/2026-07-08/`;
- independent scoring oracle comparison;
- independent astronomy oracle summary;
- retrograde trust fix with strict no-silent-false validation;
- Moon illumination formula check;
- transit-to-natal evidence labels in audit/debug contexts;
- day-scored signals separated from static natal background in semantic contexts;
- advice consistency guard for avoid verdicts;
- live LLM sample isolated under `live/<timestamp>/`;
- full backend suite green from canonical `apps/api` cwd.

## Fresh Review Evidence

All commands below were run by the architect after the Rework 09 callback.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

Result:

```text
649 passed, 5 skipped, 1 warning in 46.86s
```

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

Result:

```text
43 passed, 1 warning in 31.67s
```

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/test_ephemeris_retrograde.py tests/test_services.py -q
```

Result:

```text
5 passed in 0.08s
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_astronomy_oracle.py::test_audit_resolve_output_dirs_default \
  tests/test_astronomy_oracle.py::test_audit_resolve_output_dirs_live \
  -q -vv
```

Result:

```text
2 passed in 0.02s
```

```bash
apps/api/.venv/bin/python scripts/test_audit_scoring_oracle.py
```

Result: exit code 0.

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff --exit-code -- artifacts/audit/2026-07-08
```

Result: exit code 0, no canonical artifact diff.

Audit summary:

```text
day_status: oracle=supportive, production=supportive, pass=true
top_signals: pass=true
moon_phase: oracle=43.792, production=44, delta=-0.208, pass=true
retrograde_flag_pass: true
```

```bash
apps/api/.venv/bin/python scripts/audit_today.py \
  --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \
  --date 2026-07-08 \
  --out artifacts/audit/2026-07-08 \
  --live-llm-sample
git diff --exit-code -- artifacts/audit/2026-07-08
rm -rf artifacts/audit/2026-07-08/live
```

Result: exit code 0, live output isolated under `live/<timestamp>/`, no canonical artifact diff after cleanup.

```bash
rg -n 'Moon Phase Fact: "N/A"|Top Flags: N/A|\| N/A \| N/A \| N/A \||Рекомендация временно недоступна\.|Общайся с близкими.*отнош' \
  artifacts/audit/2026-07-08/14_claims_audit.md \
  artifacts/audit/2026-07-08/11_final_today_payload.json
```

Result: exit code 1, no forbidden fallback strings.

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

Result: whitespace checks clean. Status only contains known unrelated untracked files:

```text
.grace/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## Residual Notes

- W0 intentionally does not introduce production V2 activation logic.
- `--live-llm-sample` emitted a non-fatal structured logging error: `log_event failed`. The audit command still exited 0 and preserved artifact isolation. This is not a W0 acceptance blocker, but observability can be handled in a later hardening pass if it repeats outside audit runs.
- Next wave is W1: typed activation/scoring contracts, canon, and versioning skeleton.

