# R14 Phase C1A-R7I review — rejected: production root:astro ownership is unproven and broken

## Verdict

R7I is rejected. The green suites run as `astro:astro` and do not exercise the
production identity required by `prod-env-prepare.sh`: `/etc/solarsage/env` is
`root:astro` and `--apply` runs as root. The active transaction creates the
temporary `current` symlink without `lchown`, and rollback calls `os.lchown`
without the environment directory fd.

No C1B/C2 work, production mutation, commit, or push is authorized.

## Independent production-identity reproduction

On a fresh isolated directory owned `root:astro`, with the same valid source
profile and the current tool:

```text
install-set rc=0
current owner=root:root
install output=install: OK ...
check-installed rc=14
check error=Error: current owner mismatch
```

The tool reports success while installing a state that its own read-only check
rejects. This is a production blocker, not a test-only discrepancy.

Two additional fresh root:astro fault probes prove the recovery path is also
broken:

```text
current-replace fault: rc=16; old current unchanged;
  .current-<id> remains root:root;
  Error: recovery symlink owner mismatch

post-switch + rollback fault: rc=16; current remains the new generation;
  .rb-<id> remains root:root -> old generation;
  Error: recovery rollback lchown failed
```

The second result comes from the active call:

```python
os.lchown(rollback_name, uid, gid)
```

which is relative to the process cwd rather than `env_fd`; the rollback
symlink lives in the env directory.

## Required continuation

Implement `133_TZ_R14_PHASE_C1A_R7J_ROOT_ASTRO_SYMLINK_OWNERSHIP.md` through the
coder in tmux. Keep all existing green transaction, FI, SIG, and mutation
coverage; add a production-identity oracle before any acceptance claim.
