# Wave W0 Rework 03 Architect Review

Status: REWORK REQUIRED

Reviewed HEAD: `2572f175905878e0d1c3f56992b9ac3ebc6a5aea`

Source TZ:
- `docs/15_SolarSage_v2_activation_audit_TZ.md`
- `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/09_rework_03_TZ.md`

## Verification Run By Architect

Passed:

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

Result: `37 passed, 1 warning`.

```bash
cd apps/solarsage && venv/bin/python -m pytest \
  tests/test_ephemeris_retrograde.py \
  tests/test_services.py \
  -q
```

Result: `5 passed`.

```bash
apps/api/.venv/bin/python scripts/test_audit_scoring_oracle.py
```

Result: exit `0`.

```bash
git diff 2f9173f..HEAD --check
git show --check HEAD
```

Result: clean.

`make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08` also exits `0` and produces passing oracle summaries:
- `content_version=6`
- `cached=false`
- `moon_phase.pass=true`
- `retrograde_flag_pass=true`
- `day_status.pass=true`
- `top_signals.pass=true`

## Findings

### P0 - `make audit-day` is not a deterministic baseline command

Evidence:

After a fresh architect run of:

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
```

`git status --short --branch` shows committed canonical artifacts are dirty:

```text
## main...origin/main [ahead 8]
 M artifacts/audit/2026-07-08/11_final_today_payload.json
 M artifacts/audit/2026-07-08/14_claims_audit.md
 M artifacts/audit/2026-07-08/debug/audit_summary.json
 M artifacts/audit/2026-07-08/debug/final_today_payload.json
?? .grace/
?? docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
?? grace.db
?? skills/
```

The diff is not limited to timestamps. It changes the headline, all concrete advice texts, reading text, notes, why-sections, planet interpretations, and the claims report.

Examples:

```diff
- **Headline**: "Сегодняшние эмоции помогут тебе достичь гармонии и уверенности в действиях."
+ **Headline**: "День для глубоких эмоций и поддержки творческих начинаний."
```

```diff
- | Работа | caution | Сохраняй осторожность в работе, избегай конфликтов и неопределенных ситуаций. |
+ | Работа | caution | Будь осторожен на работе, особенно в вопросах, связанных с долгосрочными обязательствами. |
```

Root cause in current implementation:

- `scripts/audit_today.py:454-455` always calls `TodayService(db).invalidate_cache(user.id)`.
- `scripts/audit_today.py:457-464` then regenerates a fresh production `TodayPayload`.
- `scripts/audit_today.py:477-489` copies that live payload into the canonical artifact `11_final_today_payload.json`.
- `scripts/audit_today.py:505-551` copies live LLM text into `14_claims_audit.md`.

This violates `docs/15_SolarSage_v2_activation_audit_TZ.md` W0 DoD:

```text
generated artifacts are deterministic except timestamps
```

It also contradicts `09_rework_03_TZ.md`, which required final git status after verification to show only known unrelated untracked files.

Required fix:

- The default `make audit-day` must be a repeatable baseline command. Running it against the committed Basil 2026-07-08 baseline must not dirty canonical artifacts.
- Do not let live, non-deterministic LLM text become part of committed canonical artifacts on every run.
- Keep production/live LLM sampling available only behind an explicit opt-in mode if needed, and write that output to a timestamped or ignored debug path, not to the versioned canonical baseline files.
- Preserve the important deterministic facts in canonical artifacts: input profile, raw astrology, normalized signals, day-scored signals, scoring outputs, semantic contexts, final payload shape/meta/status/facts/evidence, oracle comparisons, claims audit rows.
- Normalize or snapshot volatile fields so canonical artifacts are stable. This includes at least `meta.generated_at` and all live LLM narrative/advice fields if they are regenerated.
- Do not change runtime production behavior or introduce production mocks.

### P1 - Claims audit does not fail on production fallback advice text

Evidence:

The fresh `make audit-day` run produced this row in `artifacts/audit/2026-07-08/14_claims_audit.md`:

```text
| Поездки | avoid | Рекомендация временно недоступна. |
```

The audit still passed because the new regression checks only the literal `N/A` placeholders:

```text
Moon Phase Fact: "N/A"
Top Flags: N/A
| N/A | N/A | N/A |
```

This is too weak for a claims audit. A live LLM response that drops one of 12 advice rows should be visible as a failed or degraded audit condition, not silently accepted as a good W0 baseline.

Required fix:

- Add a claims-quality check for placeholder/fallback advice text, including `Рекомендация временно недоступна.`.
- For the committed canonical W0 baseline, the claims report must not contain fallback advice text.
- If a live opt-in audit mode is added, it may record fallback text, but it must mark the claims audit as degraded/failed instead of passing silently.
- Add regression coverage for this condition.

## Required Rework

Create and execute:

`docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/12_rework_04_TZ.md`

Expected report:

`docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/13_rework_04_report.md`

Do not push/deploy before architect acceptance.
