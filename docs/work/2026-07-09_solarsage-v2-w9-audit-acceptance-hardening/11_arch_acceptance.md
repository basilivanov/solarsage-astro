# W9 Architect Acceptance

Status: ACCEPTED
Date: 2026-07-09
Reviewed callback HEAD: `7383e80`

## Accepted Scope

W9 audit acceptance hardening is accepted after Rework 03.

Relevant commits:

- Initial W9 implementation: `ebb1898`
- Rework 01 final evidence tip: `eee6346`
- Rework 02 V2-selected identity code/tests: `d1dfec7`
- Rework 03 whitespace hygiene code/tests: `9d6e502`
- Final reviewed callback/evidence tip: `7383e80`

## Architect Checks

The remaining blocker from Rework 01 was fixed:

- V2-selected scoring path now emits V2 payload/cache identity even when `SOLARSAGE_V2_FRONTEND_ENABLED=false`.
- V1-selected path remains legacy V1 identity.
- Regression coverage exists for both paths.

The Rework 02 hygiene blocker was fixed:

- `apps/api/app/services/today_service.py` ends with one trailing newline.
- `apps/api/tests/test_today_meta_versions.py` ends with one trailing newline.
- No business logic changes were made in Rework 03.

## Independent Verification

Fresh commands run by architect:

```bash
runuser -u astro -- bash -lc 'cd /opt/solarsage-astro/apps/api && source .venv/bin/activate && python -m pytest tests/test_today_meta_versions.py tests/test_today_cache_v2_key.py tests/test_audit_today_modes.py tests/test_audit_activation_sidecar_artifacts.py -q'
```

Result: `38 passed`.

```bash
runuser -u astro -- bash -lc 'cd /opt/solarsage-astro && pnpm contracts:generate && git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts && pnpm typecheck'
```

Result:

- contracts regenerate: passed;
- contracts diff: zero;
- typecheck: passed.

```bash
git diff --check 92fa2fd..HEAD
git show --check HEAD
```

Result: clean.

## Notes

- Push: NOT_ATTEMPTED for W9.
- Deploy: NOT_ATTEMPTED for W9.
- Remote CI: REMOTE_CI_NOT_AVAILABLE.
- During architect verification, `pnpm contracts:generate` first hit `.git/index: Permission denied` because recent docs commits were created by root. Ownership was fixed with `chown -R astro:astro .git`, then the contract/typecheck gate was rerun successfully.
