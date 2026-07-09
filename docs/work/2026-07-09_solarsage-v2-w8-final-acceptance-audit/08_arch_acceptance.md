# W8 Architect Acceptance

Status: ACCEPTED
Accepted implementation head: `31b64d8`
Date: 2026-07-09
Master TZ: `docs/15_SolarSage_v2_activation_audit_TZ.md`
Audit base: `2f9173fbe9a9e20e97891e9789db6de57a2afaef`

## Scope Accepted

The SolarSage V2 implementation and its final W8 acceptance evidence are accepted.
All 49 acceptance checklist items are proven by executable gates, tests, generated
contract checks, audit artifacts, or explicit rollout documentation.

W8 is an audit and evidence-closing wave. The final rework changed no product code.
The only environment correction was restoring `astro:astro` ownership for generated
contracts and Playwright output directories so the canonical commands could run
without `sudo`.

## Independent Verification

The architect independently reran:

```bash
python3 scripts/check_audit_golden.py
python3 scripts/check_v2_performance_budgets.py
python3 scripts/check_solarsage_v2_rollout_gates.py
python3 scripts/check_logging_guardrails.py
```

Result: all four gates passed.

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff -- artifacts/audit/2026-07-08
```

Result: production and oracle statuses matched, all sphere deltas were `0.0`,
astronomy checks passed, and the audit command left no tracked artifact diff.

```bash
cd apps/api
source .venv/bin/activate
python -m pytest \
  tests/test_astronomy_oracle.py \
  tests/test_semantic_contexts.py \
  tests/test_today_concrete_advice_consistency.py \
  tests/test_activation_layer_contract.py \
  tests/test_activation_layer_transits.py \
  tests/test_activation_layer_profections.py \
  tests/test_activation_layer_firdar.py \
  tests/test_activation_layer_returns.py \
  tests/test_activation_layer_progressions.py \
  tests/test_activation_layer_eclipse.py \
  tests/test_scoring_v2_contracts.py \
  tests/test_scoring_v2_convergence.py \
  tests/test_scoring_v2_antidominance.py \
  tests/test_scoring_v2_thresholds.py \
  tests/test_scoring_v2_family_dedup.py \
  tests/test_scoring_v2_breakdown_contract.py \
  tests/test_scoring_v2_runtime_flags.py \
  tests/test_today_cache_v2_key.py \
  tests/test_today_service_v2_dual_run.py \
  tests/test_calendar_v2_dual_run.py \
  tests/test_today_v2_payload.py \
  tests/test_semantic_v2_service.py \
  tests/test_llm_claim_validator.py \
  tests/test_today_meta_versions.py \
  tests/test_day_endpoints.py \
  tests/test_calendar_endpoints.py -q
```

Result: `139 passed, 1 skipped, 1 warning`.

```bash
cd apps/solarsage
source venv/bin/activate
python -m pytest tests -q
```

Result: `159 passed, 1 warning`.

```bash
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
npx vitest run \
  __tests__/contracts/today.test.ts \
  __tests__/lib/adapt-payload.test.ts \
  __tests__/components/TodayScreen.test.tsx
E2E_BASE_URL=http://localhost:3002 \
  npx playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile
```

Result: generated contracts had zero diff, typecheck passed, Vitest reported
`60 passed`, and the mobile Playwright smoke reported `1 passed`.

## Known-Issue Review

The AGENTS.md note about raw `Transit_` / `Natal_` prefixes is not present in
user-facing `topFlags`:

- `TodayService._build_top_flag()` applies `strip_prefix()` to titles and icon names.
- `test_today_service_formats_top_flags_for_users` verifies localized titles and
  rejects both prefixes.
- The remote pipeline smoke contains the same prefix guard for `title` and `iconName`;
  it remains opt-in because it requires remote Telegram credentials.

Raw prefixes intentionally remain in internal signal and audit data where they carry
the transit/natal frame. This is not a UI or LLM contract leak.

SolarSage still does not return `planet.house` directly. The API mapping remains a
documented technical-debt item, not an acceptance blocker: current house placement is
covered by the astronomy oracle and the accepted sidecar/API test suites.

## Process Notes

- The initial W8 attempt used `sudo rm -rf` and deleted its own TZ. The reworks
  restored the TZ and reran all evidence without `sudo`.
- The agent report contains a pre-commit `git status` snapshot with modified review
  documents. The accepted repository state has no tracked modifications.
- Untracked local `.grace/`, `grace.db`, `skills/`, and the pre-existing
  `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md` are outside W8.

## Push / Deploy

Push: NOT_ATTEMPTED
Deploy: NOT_ATTEMPTED
