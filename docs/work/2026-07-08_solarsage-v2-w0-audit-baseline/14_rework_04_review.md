# Wave W0 Rework 04 Architect Review

Status: REWORK REQUIRED

Reviewed HEAD: `35c43f36724fd1a0d5ca4929fcf6a602ee5fef27`

Implementation commit: `313f114385bcf005f7c083253bd292cd350f261a`

Report: `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/13_rework_04_report.md`

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
git diff --exit-code -- artifacts/audit/2026-07-08
```

Result: clean.

## Findings

### P0 - Default `make audit-day` is warm-cache deterministic, not baseline deterministic

Evidence:

- `13_rework_04_report.md:9-11` states the default path "uses the cached TodayPayload, which is stable once generated."
- `scripts/audit_today.py:454-459` only stops invalidating cache by default, then still calls `TodayService.get_today_payload`.
- `apps/api/app/services/today_service.py:174-179` returns a cached payload only if a valid `TodayPayloadCache` row exists.
- On cache miss, `apps/api/app/services/today_service.py:264-288` calls `LLMService` for headline, reading, notes, and why sections.

Impact:

- The current determinism proof only proves repeated runs after the DB already contains a matching cached payload.
- A clean DB, missing cache row, changed profile hash, invalidated cache, or new date still goes through live LLM text generation and may rewrite canonical artifacts.
- This does not satisfy W0 DoD from `docs/15_SolarSage_v2_activation_audit_TZ.md`: generated artifacts must be deterministic except timestamps.

Required fix:

- Default `make audit-day` must not depend on live LLM generation or the accidental presence of `TodayPayloadCache`.
- Treat the default command as a baseline verifier, not a baseline refresher.
- The default command must either:
  - use a checked-in deterministic baseline/frozen projection for volatile LLM fields while recomputing and validating deterministic astrology/scoring/evidence fields; or
  - fail fast before writing canonical files if the exact required baseline payload is unavailable, with a separate explicit refresh flow.
- The preferred architecture is a stable canonical projection:
  - deterministic fields are freshly recomputed and written;
  - volatile LLM narrative text is frozen, normalized, hashed, or loaded from a committed baseline fixture;
  - the command never silently refreshes canonical LLM text.
- Add verification that proves the default command is deterministic without relying on a pre-existing DB cache row.

### P0 - `--live-llm-sample` still writes into the canonical root artifacts

Evidence:

- `scripts/audit_today.py:605-606` adds `--live-llm-sample`.
- The flag only controls cache invalidation at `scripts/audit_today.py:456-457`.
- The script still writes `debug/final_today_payload.json` at `scripts/audit_today.py:472`.
- It then always copies that live payload into canonical root `11_final_today_payload.json` at `scripts/audit_today.py:485-497`.
- It always generates root `14_claims_audit.md` from the same live payload at `scripts/audit_today.py:504-551`.
- `13_rework_04_report.md:17-21` says live sampling writes into debug and an architect must commit canonical artifacts if they are to become baseline. That is not what the code does: live mode directly clobbers canonical root files in the supplied `--out`.

Impact:

- A manual live sample can accidentally overwrite the versioned W0 baseline.
- This recreates the same failure mode that Rework 04 was meant to eliminate.

Required fix:

- Live LLM sampling must write to a separate path, for example:

```text
artifacts/audit/<DATE>/live/<timestamp>/
```

- It must not overwrite the 16 canonical root artifacts by default.
- If you keep direct `--out`, then `--live-llm-sample` must refuse to run when `--out` is the canonical `artifacts/audit/<DATE>` directory unless an explicit destructive flag is provided. Prefer a non-destructive live output path.
- Add a regression check proving live mode does not change `artifacts/audit/2026-07-08/{00..15}_*` by default.

### P0 - Current committed baseline reintroduced an advice contradiction outside `ConcreteAdvice`

Evidence:

The current committed payload has a relationship row with `avoid`:

```json
{
  "key": "relationships",
  "verdict": "avoid",
  "text": "Избегай конфликтов в отношениях, сейчас напряженные аспекты могут ухудшить ситуацию."
}
```

But the same committed `11_final_today_payload.json` contains:

```json
"Общайся с близкими — аспекты благоприятствуют отношениям."
```

Location:

- `artifacts/audit/2026-07-08/11_final_today_payload.json`
- `why_this_happens.sections[id=why-9]`

Root cause:

- `apps/api/app/services/semantic_service.py:402-410` hardcodes supportive-day practical bullets:

```python
if day_status == "supportive":
    practical_items = [
        "Действуй — сегодня энергии планет поддерживают начинания.",
        "Общайся с близкими — аспекты благоприятствуют отношениям.",
        "Заверши отложенные задачи — день даёт импульс.",
    ]
```

Impact:

- W0 trust fix only guards `ConcreteAdvice`, but the frontend payload still carries a practical advice contradiction in `WhyThisHappens`.
- This is the same class of trust bug described in `docs/15`: avoid-verdict relationship advice must not recommend relationship outreach unless it is framed as safe mitigation.

Required fix:

- `practical_meaning` must be evidence-aware.
- Do not hardcode domain-specific positive advice from only `day_status`.
- Either derive practical bullets from `concrete_advice` rows after verdict/evidence consistency, or keep them generic and non-contradictory.
- Add a regression test proving no payload-level practical advice says relationship outreach is favorable when the relationships concrete advice row is `avoid`.

## Required Rework

Create and execute:

`docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/15_rework_05_TZ.md`

Expected report:

`docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/16_rework_05_report.md`

Do not push/deploy before architect acceptance.
