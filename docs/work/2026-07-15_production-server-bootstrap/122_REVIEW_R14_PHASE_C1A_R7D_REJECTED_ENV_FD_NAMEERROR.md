# R14 Phase C1A-R7D review — rejected: FI08 cleanup calls undefined fd

## Verdict

R7D is **rejected**. The latest direct transaction run is green only because
the harness accepts any nonzero FI result. The normal current-replace recovery
is broken by a runtime variable error.

## Independent reproduction

On a fresh valid environment, I copied the current tool and changed only the
current `os.replace(current_tmp, "current", ...)` call to raise `OSError`.

Observed:

```text
rc=16
stderr=Error: recovery failed
leftover=.current-<id> -> generations/gen-<new>
leftover=generations/gen-<new>
current remains old
```

The active recovery line is:

```python
_unlink_temp_symlink_strict(env_fd, current_tmp, exp_target, uid, gid)
```

but `cmd_install_set` defines `env_dir_fd`, not `env_fd`. The resulting
`NameError` is caught by the broad recovery `except Exception` and reported as a
generic recovery failure. This violates the core retry invariant and leaves
the exact artifacts that FI08 must remove.

The handoff's FI table did not include this runtime path; its 37-case count is
therefore not acceptance.

## Required next step

Implement `123_TZ_R14_PHASE_C1A_R7E_FIX_ENV_FD_AND_PROVE_RETRY.md`. Do not
declare any FI result green until the harness asserts exact rc/artifacts and a
canonical retry.
