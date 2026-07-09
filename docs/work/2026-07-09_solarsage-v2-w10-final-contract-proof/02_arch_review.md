# W10 Architect Review

Status: REWORK REQUIRED
Reviewed commit: `ed2d2e6`
Date: 2026-07-09

## Findings

### P0 — Cached/schema path can still return or construct `today.v2` with `v2=None`

Evidence:

- W10 hard stop says do not accept if:
  - `payload_version=today.v2 AND payload.v2 is null`
  - `frontend_payload_version=2 AND payload.v2 is null`
- Fresh `TodayService.get_today_payload()` now checks this only after building a new payload.
- Cached path still does:

```python
payload = TodayPayload(**payload_dict)
payload.meta.cached = True
return payload
```

in `apps/api/app/services/today_service.py`.

- `apps/api/app/schemas/today.py` has no model-level invariant for this contract.
- Manual validation confirms the schema accepts an explicit bad V2 payload:

```text
accepted_bad_payload today.v2 2 True
```

Impact:

W9 could already have written cache rows with V2 meta identity and `v2=None`. W10 changed the read key to match that V2 identity, so those old bad rows can now be read instead of forcing a fresh W10-compliant payload. This violates the main W10 contract proof and the hard stop rule.

Required fix:

- Add a reusable V2 payload contract invariant.
- Prefer both:
  - schema-level `TodayPayload` validator that rejects explicit `today.v2` / frontend 2 with `v2=None`;
  - cached-read guard in `_get_cached_payload()` that treats legacy bad cached rows as cache misses instead of returning them or crashing the request.
- Add regression coverage:
  - constructing/validating `TodayPayload` with `payload_version="today.v2"`, `frontend_payload_version=2`, `v2=None` fails;
  - `_get_cached_payload()` returns `None` for a matching V2 cache row whose JSON declares V2 identity but has `v2=None`;
  - V1 cached payloads with `v2=None` still work.

### P1 — Frozen-baseline activation mapping artifact is not asserted by tests

Evidence:

W10 TZ explicitly requires:

```text
test_frozen_baseline_writes_not_live_mapping_status
```

Current `test_frozen_mode_does_not_call_today_service` checks `artifact_source.json`, claims text, and debug payload materialization, but does not assert:

- root `activation_evidence_mapping.json` exists;
- debug `activation_evidence_mapping.json` exists;
- mapping status is `frozen_baseline_not_live` or equivalent non-live status;
- frozen mode does not claim live production proof through mapping fields.

Impact:

The implementation appears to write the mapping artifact, but the required frozen-mode proof is not locked by tests. This is a proof gap, not a runtime blocker.

Required fix:

- Extend the frozen-baseline audit test to assert both mapping files exist and report non-live status.
- Keep frozen mode explicitly non-live and non-assertive.

### P2 — Alternate git index left the main working tree dirty

Evidence:

The agent report says:

```text
No .git/index deletion/repair (used GIT_INDEX_FILE alternate index only)
```

After callback, normal `git status` showed W10 files as `MM` and the report as staged deleted plus untracked. The actual working tree matched `HEAD`, but the default index was stale. The architect had to run:

```bash
git read-tree HEAD
chown -R astro:astro .git
```

Impact:

This does not affect W10 code after cleanup, but it breaks the review/push workflow and can hide real unstaged changes.

Required fix:

- Do not use alternate `GIT_INDEX_FILE` in Rework 01.
- Use normal git after the architect has fixed ownership.
- If permissions block normal git, stop and report instead of bypassing the repository index.

## Checks Run By Architect

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_today_meta_versions.py \
  tests/test_today_cache_v2_key.py \
  tests/test_audit_today_modes.py \
  tests/test_audit_activation_sidecar_artifacts.py -q
```

Result: `47 passed`.

```bash
cd apps/solarsage && source venv/bin/activate && python -m pytest tests/test_profections.py -q
```

Result: `15 passed, 1 warning`.

```bash
pnpm typecheck
git diff --check 92fa2fd..HEAD
git show --check HEAD
```

Result: passed after fixing `.git` ownership.

## Required Decision

W10 is not accepted at `ed2d2e6`.
