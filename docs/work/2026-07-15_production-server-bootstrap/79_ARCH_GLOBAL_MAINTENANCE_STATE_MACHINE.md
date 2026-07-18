# Architecture — global maintenance lock and durable operation state

## Decision

Deploy, backup, restore and offsite maintenance must share one authority lock and one durable state machine. Current independent locks cannot prevent cross-operation corruption, and restore ignores backup-maintenance activity.

## Lock authority

Canonical path:

```text
/run/solarsage-maintenance.lock   root:astro 0660
```

Created by tmpfiles/root bootstrap. `/run` prevents `astro` from replacing/unlinking the inode. Lock file contains no PID/state/secrets and is never truncated or removed for recovery.

Before `flock`:

1. `lstat` exact regular non-symlink owner/mode;
2. open once without truncation;
3. verify `/proc/self/fd/N` regular target;
4. compare path/fd dev+inode and owner/mode;
5. exclusive kernel flock.

Busy returns `75` (`EX_TEMPFAIL`); malformed/missing lock or unresolved state returns `78`. Manual deploy/restore do not wait. Systemd scheduled jobs may use bounded wait.

Remove legacy deploy/backup/restore locks after migration. During one transition release, acquire global then legacy in fixed order only.

## Coordinator and nested operations

Add root-owned/common `prod-maintenance-run` plus helper library. Coordinator holds FD through the child, forwards signals to child process group, waits and writes durable state.

Nested deploy→backup and restore→backup reuse inherited lease:

```text
SOLARSAGE_MAINTENANCE_FD
SOLARSAGE_MAINTENANCE_OPERATION_ID
```

These values are non-secret but not trusted alone. Child verifies numeric open FD, canonical dev/inode/owner/mode and inherited flock. Internal child flag without verified FD is fatal. Direct script invocation self-reexecs through coordinator.

Lock is acquired before env/secrets, checkout/live mutation, DB or Restic calls. Read-only prechecks may run before for UX, but are repeated under lock.

## Durable state

```text
/var/lib/solarsage/maintenance/       astro:astro 0700
active.json                           astro:astro 0600
history/*.json                        astro:astro 0600
restore.guard                         astro:astro 0600
```

Atomic stdlib writer: same-dir O_EXCL temp → write/flush/fsync → rename → fsync directory. State never contains DSN/password/token/repository URL/raw env/commands.

Required fields:

```text
schema operation_id kind status phase recovery_class
boot_id uid pid proc_start_ticks started_at updated_at
safe target identity runtime snapshot backup manifest basename/digest
```

Phases are enumerated and monotonic. State transition is fsynced **before** every destructive boundary. Completion archives record and removes active only while lock is held.

Statuses:

```text
running succeeded failed_safe interrupted recovery_required
```

## Operation phases

### Backup

```text
preflight → dump_writing → local_published → offsite_uploading
→ offsite_verified → local_retention_started → completed
```

Before publish, temp may be cleaned. After publish, preserve dump+checksum. Offsite failure means failed_safe, local pair preserved, no retention.

### Deploy

```text
preflight/build → safety_backup → migration_started
→ services_switching → health_verified → completed
```

At/after migration_started failure becomes recovery_required unless immutable expand-compatible rollback policy proves safe.

### Restore

```text
target_verified → runtime_snapshotted → guard_installed → services_stopped
→ safety_backup_verified → db_destructive_started → db_restored
→ migrations_verified → services_starting → health_verified
→ timers_restored → completed
```

### Offsite maintenance

```text
preflight → restic_prune_started → prune_finished → restic_check → completed
```

Prune start is a remote mutation boundary.

## Stale/signal recovery

If flock succeeds while `active.json` exists, prior journal is stale; never overwrite blindly.

- validate JSON/schema/owner/mode/boot ID/PID+start_ticks;
- free lock plus exact live PID is corruption/lost lease → block;
- backup before publish: explicit recovery may delete only state-recorded exact temps after inode/type checks;
- after publish: preserve pair, never retention;
- restore before DB boundary: explicit runtime-state recovery;
- restore at/after DB boundary: guard remains, apps/timers stopped, operator chooses resume/rollback from recorded safety dump;
- deploy after migration boundary: block until schema/release reconciliation;
- prune started: no automatic `restic unlock`; manual proof/repository check;
- malformed/unknown state fail closed.

INT/TERM/HUP: forward, wait, persist interrupted/recovery class, exit `128+signal`, then release. SIGKILL may leave durable active state; inherited child FD still excludes peers. Units use `KillMode=control-group`. Generic EXIT trap must not erase unresolved state.

## Restore runtime snapshot

Under lock snapshot exact state for:

- frontend, API, sidecar;
- backup timer and backup-maintenance timer;
- backup and maintenance oneshot services;
- DB load/active proof (DB is not stopped).

Record LoadState/ActiveState/SubState/UnitFileState/MainPID where relevant. Masked/unknown/activating/deactivating/reloading is fatal. Never change enablement during restore.

Sequence:

1. verify target/DB identity, lock/reverify, confirmation;
2. fsync snapshot and create `restore.guard`;
3. stop maintenance timer, backup timer; prove oneshots inactive;
4. stop frontend→API→sidecar and prove inactive;
5. nested `pre-restore` local backup under inherited lease, no Restic/retention;
6. fsync DB destructive phase, restore;
7. verify DB/Alembic;
8. remove guard only immediately before controlled start; start only units previously active: sidecar→API→frontend with health;
9. on start/health failure recreate guard before stopping started apps;
10. restore previously-active timers last and verify.

Failure before DB boundary may restore prior runtime. At/after boundary, no automatic app/timer start.

Add `ConditionPathExists=!/var/lib/solarsage/maintenance/restore.guard` to app units and both backup/maintenance timer/service paths, so reboot mid-restore cannot resume writers. DB remains available for recovery.

## Retention correction

Replace ambiguous `--local-only` internal behavior with purpose:

```text
scheduled       retention only after local verification and exact offsite proof
pre-deploy      no local retention
pre-restore     local only, no Restic, no retention
manual-safety   no retention
```

Best implementation: retention is a separate helper invoked only by scheduled workflow after proof. If offsite is disabled, default no deletion unless explicit reviewed local-only retention policy exists.

## Systemd integration

Units invoke coordinator, not bare flock. Scheduled backup/maintenance may wait up to 6h; unit timeout must include wait + operation. Wait expiry rc75 triggers alert.

Common properties:

```text
KillMode=control-group
TimeoutStopSec>=90s
UMask=0077
ReadWritePaths=/var/backups/solarsage /var/lib/solarsage/maintenance
```

Timer ordering is not correctness authority; global lock is.

Sudoers contains enumerated exact systemctl verbs only, never wildcard.

## Implementation order

1. tmpfiles/lock/state helpers + isolated tests;
2. coordinator/inherited FD;
3. backup + maintenance and retention split;
4. deploy nested safety backup;
5. restore guard/runtime snapshot;
6. remove legacy locks;
7. stale recovery tooling/runbook.

## Acceptance tests

- all pairwise operation conflicts both start orders;
- nested backup reuses lease; third process gets 75;
- path type/owner/mode/inode swap/wrong FD fail before child;
- no lock inode/bytes truncation/replacement;
- atomic state old-or-new, never partial, no secret canary;
- phase persisted before destructive marker;
- boot/PID reuse/corrupt/live-PID branches;
- exact mixed active/inactive restore; never start previously inactive/failed;
- pre-boundary recovery vs post-boundary guard/stopped state;
- reboot guard blocks units;
- health failure recreates guard before stop; timers last;
- no enable/disable calls;
- pre-restore/pre-deploy/manual modes never delete backups;
- scheduled retention only after proof;
- backup upload and prune serialized; prune interruption recovery_required;
- static unit/tmpfiles/sudoers/runbook checks.
