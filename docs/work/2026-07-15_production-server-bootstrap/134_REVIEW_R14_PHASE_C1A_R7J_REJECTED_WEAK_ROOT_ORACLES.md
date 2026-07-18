# R14 Phase C1A-R7J review — rejected: root tests and ownership mutations are not honest yet

## Verdict

R7J is not accepted. The production code now has an fd-relative symlink
ownership helper, but the new proof layer is incomplete and contains false
greens. The ordinary harness and its 12 mutations do not exercise the
root:astro path.

## Findings

### 1. Root suite is opt-in but not part of acceptance

`test-prod-env-install-transaction.sh` only runs the root section when
`ROOT_IDENTITY_TEST=1`. The direct acceptance command currently shown by the
coder does not set that variable, so the production identity proof is absent.
The handoff must include a direct root invocation (or a separate mandatory
root-identity script), not merely a gated block that was not run.

### 2. Root B/C assertions are false-green

The current B case asserts only `rc != 0`, unchanged pointer, and retry. It does
not assert the exact ordinary I/O code, no `.current-*`/staging/new-generation
artifacts, safe diagnostics, or lock state.

The current C case accepts either an unchanged pointer or `rc=16`:

```bash
[ "$CUR_AFTER3" = "$CUR_BEFORE3" ] || [ "$RC3" -eq 16 ]
```

That can pass while the pointer is new, the rollback artifact is absent, or the
diagnostic names nothing. It does not inspect `.rb-<id>` target, exact rc, or
stderr basename. This is the exact failure mode the earlier FI reviews
rejected.

### 3. The new mutation selectors do not target active code

The mutation expressions search for `os.chown.*current_tmp` and
`os.chown.*rollback_name`, but the active helper calls `os.chown(name, ...)`.
They therefore either leave bytes unchanged or produce a syntax/no-op mutation;
they do not prove removal of current or rollback ownership handling. The copied
harness is also run without `ROOT_IDENTITY_TEST=1`, so even a valid ownership
mutation would be invisible to the root oracle.

### 4. Strict helper still swallows cleanup errors

`_create_lchown_validate_symlink` contains `except OSError: pass` while removing
the just-created symlink. A failed lchown/validation can therefore leave an
artifact while the helper reports only a generic error. Recovery cleanup must
return a verified result or raise `RecoveryError` with the safe basename; it
cannot suppress unlink/proof failures.

### 5. Root setup hides source ownership failure

The root fixture uses `chown ... || true` for `source.env`. That allows the test
to proceed without establishing the documented root:astro source boundary.
Fixture setup must fail closed and clean all temporary directories with an EXIT
trap, including failure paths.

## Required continuation

Implement `135_TZ_R14_PHASE_C1A_R7K_HONEST_ROOT_ORACLES_AND_MUTATIONS.md`.
Do not declare C1A accepted on the ordinary 37/37 + 12/12 output alone.
