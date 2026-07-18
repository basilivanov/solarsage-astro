# R13 Phase B6 R8 — rejected: SIGCLEAN does not exercise lock_cleanup

## Verdict

The current `SIGCLEAN` proof is still tautological. The rest of the R7 temp and
mutation separation fixes are present, but Phase B6 is not accepted until the
actual cleanup handlers are exercised.

## Current false proof

The test creates a directory, then runs a child containing only:

```bash
trap 'exit 129' HUP
```

and equivalent INT/TERM traps. The parent later removes the directory itself.
The child never calls the harness `lock_cleanup`, never starts/tracks a holder,
and never removes the directory. Therefore exact signal rc is tested, but the
cleanup behavior is not.

## Required implementation

Refactor the harness signal wiring into reusable test-harness functions, for
example:

- `lock_cleanup` — kill/wait exact `LOCK_PID`, clear it, remove exact `TEST_DIR`;
- `on_hup` — call cleanup, exit 129;
- `on_int` — call cleanup, exit 130;
- `on_term` — call cleanup, exit 143;
- `install_harness_traps` — install those functions plus EXIT cleanup.

Normal harness startup must call the same `install_harness_traps` used by the
signal self-test.

For each HUP/INT/TERM self-test:

1. create a unique child test directory;
2. start a child Bash using the actual exported/function definitions;
3. in that child, set `TEST_DIR`, start a long-lived holder, set `LOCK_PID`,
   report the holder PID to a parent-owned report file, install the actual
   handlers, and wait;
4. parent waits boundedly until the PID report exists;
5. parent sends the real signal to the child shell;
6. parent `wait`s and asserts exact rc 129/130/143;
7. assert the reported holder PID is not alive;
8. assert the exact child test directory no longer exists.

Do not let the parent manually remove the child directory before asserting it.
Parent may perform best-effort cleanup only after a failed assertion.

Do not globally scan/delete other harness directories; the test must be safe if
two harness instances run concurrently.

## Mutation audit stages

Extend `check_loader_mutation` (or split it by semantic type) so PASS requires
the expected attempted audit record and stop stage:

- MUT17–19: fingerprint reached, exact mutated `load-env` argv attempted,
  controlled-stop absent;
- MUT20: `git rev-parse origin/bad` attempted, checkout/fingerprint/loader absent;
- MUT21: valid ref resolution then exact wrong checkout argv attempted,
  fingerprint/loader absent;
- MUT22: exact checkout of `OLD_HEAD` attempted, fingerprint/loader absent.

Before each mutation run assert no pre-existing `untracked.*`; after each run
assert none were created. Do not clean a leak before failing.

## Completion

Run two unfiltered full harness executions and the three adversarial mutations.
Then the architect will independently rerun acceptance. No production, commit or
push.
