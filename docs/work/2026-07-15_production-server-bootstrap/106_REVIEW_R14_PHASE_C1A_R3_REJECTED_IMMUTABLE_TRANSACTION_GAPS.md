# R14 Phase C1A-R3 review — rejected: immutable switch exists, recovery does not

## Verdict

The immutable-generation direction is accepted architecturally, but C1A-R3 is
**rejected**. Basic install/check works and direct suites are green; fault paths,
locking and read-only behavior violate the contract.

No production/network/SSH/DB/Docker/systemd mutation, commit or push occurred.

## Genuine baseline

```text
test-prod-env-loader.sh                  rc=0
test-prod-env-profiles.sh x2             rc=0, 73/73
test-prod-env-profiles-mutations.sh x2   rc=0, 8/8
test-prod-deploy-source-loader.sh        rc=0, 111/111
test-prod-host-offsite-routing.sh        rc=0
prod-infra-fingerprint.sh                rc=0
git diff --check                         PASS
stale harness directories                0
```

## P0/P1 executable findings

### 1. Lock is outside the canonical env directory

`cmd_install_set` and `cmd_check_installed` call `os.open(".profile.lock", ...)`
without `dir_fd` and without a mode argument. It is created in process cwd.

```text
lock_in_cwd=yes lock_in_env=no lock_mode=775
```

The lock therefore does not protect a canonical resource and may dirty the
checkout.

### 2. Check ignores lock contention

On `BlockingIOError`, check executes `pass` and continues unlocked
(`prod-env-tool.py:1035-1039`).

```text
check_while_exclusive_lock_held_rc=0
```

### 3. Read-only check mutates a fresh directory

`_open_generations_fd` always creates the directory when missing, and check opens
the lock with `O_CREAT`.

```text
fresh_check_rc=14 generations_created=yes cwd_lock_created=yes
```

### 4. Post-switch verification failure does not restore current

The final `_validate_current_generation` failure is caught only to close fds and
re-raised; no pointer rollback occurs (`prod-env-tool.py:1006-1011`).

Injected failure:

```text
injected_post_switch_verify_rc=14
current_after_failure=generations/gen-<new-id>
```

On first install, failed verification must restore `current` to absent.

### 5. Internal `_fail` bypasses staging cleanup

Helpers call `sys.exit` (`SystemExit`), while the staging block catches only
`Exception`. An injected write failure leaves the staging directory:

```text
injected_write_fail_rc=13 staging_left=1 current=absent
```

The cleanup code also contains an explicit placeholder
`dir_fd=gfd if False else None`, so it tries to unlink profile basenames from
cwd rather than from staging and swallows the failure.

### 6. Installed-generation physical contract is incomplete

Check verifies only the seven expected profile paths. It does not validate
generation directory owner/mode or reject extra entries.

```text
check_extra_file_and_gen_mode_777_rc=0
```

### 7. No signal implementation/proof

The handoff claims Python signal safety, but no HUP/INT/TERM handlers exist in
the implementation or harness.

## Further code blockers

- existing current generation is marked "best-effort" and not validated before
  it becomes the rollback target;
- rollback errors and fsync failures are swallowed with `pass`;
- rollback result is never verified;
- current regular-file/permission errors are treated as "absent" because every
  `readlink` error maps to `None`;
- generation directory is not fchowned to env uid/gid;
- profile files are fsynced before fchown/fchmod and not fsynced afterward;
- `_write_and_fsync` uses one `os.write`, not a complete-write loop;
- stale `.staging-*`/`.current-*` artifacts are not rejected;
- direct legacy profiles and extra generation files are not rejected;
- current symlink ownership is not validated;
- mutation harness is still the old eight-row direct behavior table and has no
  pointer, fsync, lock, recovery or signal mutation.

## Required correction

Implement only `107_TZ_R14_PHASE_C1A_R4_IMMUTABLE_TRANSACTION_HARDENING.md`.
Do not start C1B/C2.
