# Stage 1.W4.R1 — architect errata: full API suite runs from repository root

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Base: `7d37acbaa31118a8545987a39a5fabe18fbb6e32`
Amends:

- `119_STAGE_1_W4_R1_REQUEST_SCOPED_FULL_ACCESS_PREVIEW_TZ.md`, section 13.3;
- final architect-doc/untracked count only.

Статус: **AUTHORIZED CONTINUATION — DO NOT CHANGE IMPLEMENTATION FOR CWD BASELINE**

## 1. Observed state

Coder completed implementation and focused backend proof:

```text
implementation/test paths: exact 8
new focused backend file: 700 lines
focused backend: 83 passed
index: empty
commit/push: not performed
services: unchanged
3003/8001/18092: absent
```

The exact full-backend command from 119 ran after `cd apps/api` and returned:

```text
1393 passed
14 skipped
2 failed
```

Both failures are existing cwd-sensitive source guards:

```text
tests/test_horizon_pipeline_service.py
  expects apps/api/app/services/horizon_pipeline_service.py from repo root

tests/test_real_today_v2_api_proof.py
  expects scripts/prove_today_v2_real_api.py from repo root
```

From `apps/api`, both paths are necessarily resolved under the wrong directory
and raise only `FileNotFoundError`. This is not a feature regression.

## 2. Correction

Do not edit either existing test, its source path, conftest or repository layout.

The canonical full API command for this wave is from repo root:

```bash
cd /opt/solarsage-astro
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
```

This replaces only section 13.3 of 119.

Zero failures are required. Record exact passed/skipped totals.

## 3. Continuation protocol

Before continuing:

1. confirm exact eight implementation/test paths;
2. confirm architect docs 117–120 are byte-unchanged;
3. confirm test file `<=700` lines;
4. confirm index empty;
5. confirm no 3003/8001/18092 and services unchanged;
6. run `git diff --check`;
7. rerun the focused backend command from 119 or at minimum the exact new
   access/transport/access-service modules to prove no drift;
8. run corrected root full API command;
9. only if green, continue frontend focused/full, typecheck, guards, contracts
   zero generated diff and isolated build from sections 13.4–13.6.

No implementation edit is authorized merely to address the two cwd failures.
If a corrected root run has a real failure, stop and report it.

## 4. Scope and prohibitions unchanged

All implementation allowlists and prohibitions in 119 remain literal:

- no path outside exact eight;
- no existing 997-line transport test edit;
- no generated contract diff;
- no service restart/reload;
- no 3003 retry;
- no git add/commit/push;
- no subagents.

The untracked architect-doc set is now exact four:

```text
117_STAGE_1_W4_STRICT_REAL_PREVIEW_EXECUTION_TZ.md
118_STAGE_1_W4_ARCH_ERRATA_NEXT_ENV_MTIME_NON_CONTRACT_TZ.md
119_STAGE_1_W4_R1_REQUEST_SCOPED_FULL_ACCESS_PREVIEW_TZ.md
120_STAGE_1_W4_R1_ARCH_ERRATA_REPO_ROOT_FULL_API_TZ.md
```

Success callback uses the 119 format with:

```text
architect_docs: UNCHANGED_117_TO_120
```

After callback stop. No commit/push/restart/3003 until architect review.
