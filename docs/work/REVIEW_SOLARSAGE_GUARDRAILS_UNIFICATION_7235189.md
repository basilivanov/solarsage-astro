# Review: SolarSage guardrails unification at 7235189

## Verdict

**REWORK REQUIRED**

Commit `7235189c6297e9f8e838336890ecbf888ac5517e` implements the right direction: backend size checks, a new frontend GRACE lint, guardrails profiles, and separation of domain-specific horary guard from universal frontend. However, the new frontend gate currently has one blocker: it can silently pass when the frontend paths file is missing or when the configured frontend slice matches no files. That weakens the previous hard-gate behavior.

Reviewed commit:

```text
7235189c6297e9f8e838336890ecbf888ac5517e
feat(guardrails): unify guardrails, implement GRC030/GRC031 size checks for python and ts/js
```

Base commit:

```text
2d0485172296f886f7b1d60483406b62bda541ff
```

Changed files:

```text
scripts/grace/check-markers.sh
scripts/grace/check-negative.sh
scripts/grace_front_lint.py
scripts/grace_lint.py
scripts/guardrails.sh
scripts/test_grace_lint.py
```

## What is good

1. `scripts/grace/check-markers.sh` is now a compatibility wrapper around `scripts/grace_front_lint.py`.
2. `scripts/grace_front_lint.py` exists and implements frontend checks for:
   - `GRC001` missing `AI_HEADER`;
   - `GRC002` module contract mismatch;
   - `GRC003` module map mismatch;
   - `GRC004` block pairing mismatch;
   - `GRC030` file too long;
   - `GRC031` frontend function/component too large.
3. `scripts/grace_lint.py` now enforces backend `GRC030/GRC031` size limits.
4. `scripts/test_grace_lint.py` has backend size-limit tests.
5. `scripts/guardrails.sh` now exposes `fast`, `normal`, `strict`, and `domain` commands.
6. `check_horary_quality.sh` is no longer part of universal `frontend`; it moved under `domain`, and `full` includes `domain`.

## Blocking finding 1: missing or empty frontend paths silently pass

### Problem

`grace_front_lint.py` treats a missing `grace/frontend.paths` as a non-blocking condition.

Current behavior:

```python
def discover_frontend_files(root: Path) -> list[Path]:
    paths_file = root / "grace" / "frontend.paths"
    if not paths_file.exists():
        print(f"Error: missing paths file at {paths_file}", file=sys.stderr)
        return []
```

Then `main()` converts an empty file list into success:

```python
if not files:
    print("grace_front_lint: no Frontend files found in active slice", file=sys.stderr)
    return 0
```

This means both cases pass:

```text
grace/frontend.paths missing -> exit 0
frontend.paths exists but matches zero files -> exit 0
```

That is weaker than the previous `check-markers.sh`, which failed when `grace/frontend.paths` was missing or when no files matched.

### Why this matters

The frontend GRACE gate is supposed to be a mandatory mechanical gate. If the config file is accidentally deleted, moved, or the glob stops matching files, the gate should fail loudly instead of treating the frontend slice as clean.

### Required fix

Make these hard failures:

```text
missing grace/frontend.paths -> exit non-zero
frontend.paths has no matched files -> exit non-zero
```

Suggested codes:

```text
GRC900 missing frontend paths file
GRC901 no frontend files matched active frontend slice
```

or keep them as CLI-level fatal errors without GRC codes.

Add tests:

```text
python3 scripts/grace_front_lint.py with missing grace/frontend.paths exits non-zero
python3 scripts/grace_front_lint.py with empty/no-match frontend.paths exits non-zero
```

## Major finding 2: no dedicated self-tests for `grace_front_lint.py`

### Problem

Backend `grace_lint.py` has `scripts/test_grace_lint.py`, including new tests for `GRC030/GRC031`.

Frontend lint currently relies on `check-negative.sh` only. That helps, but it does not pin positive/negative parser behavior in a small unit-level test suite.

### Required fix

Add `scripts/test_grace_front_lint.py` with fixtures for:

- clean frontend file passes;
- missing `AI_HEADER` -> `GRC001`;
- missing `END_MODULE_CONTRACT` -> `GRC002`;
- missing `END_MODULE_MAP` -> `GRC003`;
- missing `END_BLOCK` -> `GRC004`;
- 1000-line file passes;
- 1001-line file -> `GRC030`;
- oversized arrow component -> `GRC031`;
- normal arrow component passes.

Then include this in `guardrails.sh fast` and `frontend` or at least `fast`.

## Major finding 3: CLI help says paths can be directories, but directories are not expanded

### Problem

`grace_front_lint.py` help says:

```text
Files or directories to lint
```

But when paths are passed, the script appends the path directly and then calls `lint_file()` on it. A directory argument will be treated as a file and fail with `GRC999` / read error.

### Required fix

Either:

1. support directory expansion for `.ts/.tsx/.js/.jsx`; or
2. change help text to say only explicit files are supported.

Given orchestrator may pass allowed scopes or changed paths, supporting directories is safer.

## Minor finding 4: backend linter documentation did not mention new size checks

### Problem

`grace_lint.py` now implements `GRC030/GRC031`, but the top module docstring still lists only the previous five checks and does not document file/function size checks.

### Required fix

Update header/docstring/GRACE_ANCHORS so the linter documents:

```text
GRC030 file too long
GRC031 function too large
```

## Suggested rework patch

Minimum patch before acceptance:

1. Make missing/no-match `grace/frontend.paths` fail non-zero.
2. Add `scripts/test_grace_front_lint.py`.
3. Add `scripts/test_grace_front_lint.py` into `guardrails.sh fast`.
4. Either support directory path args in `grace_front_lint.py` or fix help text.
5. Update `grace_lint.py` docs for `GRC030/GRC031`.

## Acceptance after rework

Run and report:

```bash
python3 scripts/test_grace_lint.py
python3 scripts/test_grace_front_lint.py
python3 scripts/grace_front_lint.py
bash scripts/grace/check-negative.sh
bash scripts/guardrails.sh fast
bash scripts/guardrails.sh frontend
bash scripts/guardrails.sh normal
bash scripts/guardrails.sh strict
```

Expected final state:

- frontend marker/size gate cannot silently pass because config is missing;
- backend and frontend size limits are covered by unit tests;
- horary-specific guard stays under `domain`;
- `fast/normal/strict` are stable target-repo guardrail commands for GRACE orchestrator.

## Final decision

Do not accept `7235189` as final yet.

The implementation is close, but the frontend GRACE gate must fail closed, not pass open, when its configured enforced slice is missing or empty.
