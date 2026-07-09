# W10 Architect Acceptance

Status: ACCEPTED
Date: 2026-07-09
Accepted implementation/evidence commit: `58eef5f`

## Scope Accepted

W10 closes the final W9 proof blockers for V2 cache identity, V2 payload body consistency, and audit-side activation evidence mapping.

Accepted commits:

- `37b30ab` — initial W10 implementation.
- `ed2d2e6` — initial W10 report/evidence tip.
- `ce3c5c9` — Rework 01 code/tests for schema/cache V2 invariant and frozen mapping proof.
- `58eef5f` — Rework 01 report/evidence tip.

## Required Architect Answers

Does V2-selected cache read identity match write identity?

Yes. `expected_cache_identity()` derives identity from selected scoring version, and regression coverage proves read/write identity match for V2 selected with `SOLARSAGE_V2_FRONTEND_ENABLED=false`.

Can `TodayPayload` declare `today.v2` with `v2=None`?

No. `TodayPayload` now rejects explicit `payload_version="today.v2"` with `v2=None`, and rejects `frontend_payload_version=2` with `v2=None`. Cached legacy bad rows are treated as cache misses by `TodayService._get_cached_payload()` so old W9 rows do not get returned.

Does live audit prove sidecar activation evidence is represented in final payload?

The live audit code path now writes `activation_evidence_mapping.json`, records sidecar and payload activation id hashes/counts, and fails on missing V2 block, zero payload evidence with sidecar activations, or unmapped sidecar ids under `all_sidecar_ids_required`. This is proven by mocked live audit tests. A real DB/sidecar live audit run was not executed in this wave.

Are runtime flags visible in `artifact_source.json`?

Yes. `artifact_source.json` now includes `solarsage_v2_enabled`, `solarsage_v2_dual_run`, `solarsage_v2_frontend_enabled`, selected/final payload identity, V2 block presence, activation evidence counts, id hashes, and unmapped count.

## Independent Verification

Fresh commands run by architect:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_today_meta_versions.py \
  tests/test_today_cache_v2_key.py \
  tests/test_audit_today_modes.py \
  tests/test_audit_activation_sidecar_artifacts.py -q
```

Result: `52 passed`.

```bash
cd apps/solarsage && source venv/bin/activate && python -m pytest tests/test_profections.py -q
```

Result: `15 passed, 1 warning`.

```bash
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
```

Result:

- contracts regenerate: passed;
- contracts diff: zero;
- typecheck: passed.

```bash
git diff --check 92fa2fd..HEAD
git show --check HEAD
git status --short --branch
```

Result: whitespace gates clean; tracked working tree clean. Known untracked local files remain: `.grace/`, `grace.db`, `skills/`, and `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`.

Manual schema proof:

```text
rejected today.v2 1 1 validation error for TodayPayload
rejected today.v1 2 1 validation error for TodayPayload
```

## Notes

- Push: NOT_ATTEMPTED for W10.
- Deploy: NOT_ATTEMPTED for W10.
- Remote CI: REMOTE_CI_NOT_AVAILABLE.
- The earlier alternate-index issue from the initial W10 implementation was corrected before Rework 01. Rework 01 used the normal git index.
- Repeated `pnpm contracts:generate` checks exposed root-owned `.git/index` after architect-side git operations. Ownership was repaired with `chown -R astro:astro .git`, then the gates were rerun successfully.

## Final Verdict

Status: ACCEPTED
Accepted commit: `58eef5f`
Remote CI: NOT_AVAILABLE
Push: NOT_ATTEMPTED
Deploy: NOT_ATTEMPTED

Decision:
W10 closes the final W9 proof blockers at code and focused-test level: V2-selected cache identity is coherent, V2 identity cannot be emitted or served without a V2 body, and live audit has enforceable sidecar-to-payload activation evidence mapping. The remaining note is evidence scope: no real DB/sidecar live audit run was performed in this wave, only mocked live audit path verification.
