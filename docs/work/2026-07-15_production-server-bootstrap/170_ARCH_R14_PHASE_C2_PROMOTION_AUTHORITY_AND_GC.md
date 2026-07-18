# Architecture R14 Phase C2 — promotion authority integration and fail-closed GC

## Decision

Promotion, rollback and GC remain coordinated by the unprivileged `astro` deploy process under the inherited global maintenance lease. The coordinator may select policy and orchestrate service restarts, but it must not mutate root-owned release pointers, the Nginx maintenance flag, or finalized worktrees directly.

All privileged mutations use one fixed installed helper:

```text
/usr/local/libexec/solarsage/release-authority   root:root 0755
```

The only coordinator invocation form is:

```text
/usr/bin/sudo -n -- /usr/local/libexec/solarsage/release-authority <exact operation argv>
```

The helper remains self-contained, uses fixed production roots and executes no code from the mutable checkout or a release candidate.

## Authority operations used by this slice

```text
switch-pointer current|previous releases/<40-lowercase-hex-sha>
remove-pointer current|previous
maintenance-on
maintenance-off
gc-remove <40-lowercase-hex-sha>
```

`finalize-release` retains its accepted contract. Sudoers continues to grant only the exact installed helper path; arguments are validated by the helper.

## Pointer transaction model

`current` and `previous` cannot be changed as one filesystem primitive. Safety is therefore provided by an exact snapshot, a durable phase written before mutation, the global lease, the root-owned maintenance flag and proof-driven reconciliation.

Before the first pointer mutation the coordinator records and validates the exact optional state of both pointers. Every authority return, including non-zero, is treated as an outcome-unknown boundary: an authority operation can have completed its filesystem mutation and then failed during fsync or post-verification. The coordinator must read both pointers again and compare them with the intended state.

Required rules:

1. Enable and prove the root-owned maintenance flag before the destructive pointer phase.
2. Persist `services_switching` before the first pointer mutation.
3. Normal promotion sets `previous` to the old `current`, then `current` to the candidate.
4. Explicit rollback sets `previous` to the old `current`, then `current` to the requested finalized target.
5. On any pointer-operation failure, reconcile both pointers to the exact pre-operation snapshot and prove the result. No unchecked restore and no direct `rm` are allowed.
6. If candidate services were started, a safe restore additionally requires restart and exact health identity of the restored old release.
7. If any restore, proof, restart or old-health step fails, persist `recovery_class=recovery_required`, retain maintenance mode and return non-zero.
8. Maintenance mode may be removed only after exact target health and a durable terminal phase. Any uncertain `maintenance-off` result is a failure; restore/prove maintenance mode and mark recovery required.

The unprivileged reader for `current`/`previous` remains an advisory and reconciliation oracle. The authority independently proves a finalized release before switching a pointer.

## First-install failure

There is no old stack to restart on the first promotion. If any restart or health step fails after first-install pointer activation, removal of the new pointers alone does not prove that already-started processes stopped or reverted.

Therefore first-install activation failure is always `recovery_required` after best-effort, fully checked pointer reconciliation. The maintenance flag stays present. It must never print or persist a successful rollback/failed-safe result.

## Maintenance flag

The only public traffic flag is:

```text
/run/solarsage/maintenance   root:root 0644 regular non-symlink
```

Durable journal state remains separate under `/var/lib/solarsage/maintenance`. The promotion library must remove its old direct `/var/lib/solarsage/maintenance/maintenance.flag` implementation and must not create, chown, chmod or unlink the `/run` flag itself.

The coordinator validates flag presence/absence and exact metadata after authority calls. A malformed or outcome-unknown flag state is fail-closed.

## GC authority

Selection policy remains in the coordinator, but `gc-remove <sha>` is safe when invoked directly and does not trust the caller's cwd or deletion decision.

The root helper must, using fixed paths only:

1. validate exact SHA, runtime roots and the complete finalized target;
2. validate optional `current` and `previous` pointers and reject the target if protected; malformed pointer state blocks GC;
3. validate the canonical running-request directory and every entry, and reject the target if referenced;
4. enumerate the releases parent without following symlinks; unknown entries or invalid finalized-looking trees block GC, while exact incomplete `astro` candidates are preserved;
5. prove that the target is older than at least two other completely valid finalized releases using a deterministic `(mtime_ns, sha)` order; merely leaving two arbitrary releases is insufficient;
6. bind to `/opt/solarsage-astro` with exact Git argv and prove the target is the registered detached worktree with exact HEAD;
7. remove only through `git worktree remove --force <exact canonical path>`; no raw recursive deletion;
8. prove both filesystem absence and registry absence, then fsync the releases parent;
9. return `78` on any query, validation, removal or postcondition failure.

The coordinator calls `gc-remove` once per eligible SHA, increments `deleted_count` only after an authority success plus local absence proof, and stops with non-zero on the first removal failure. It must contain no `git rev-parse`, caller-cwd discovery or direct `git worktree remove`.

## Running-request metadata

Until the asynchronous deploy control plane replaces this marker format, the canonical protection directory is:

```text
/var/lib/solarsage/requests/   astro:astro 0700, real non-symlink directory
entries                        astro:astro 0600, regular non-symlink files
content                        exactly one 40-lowercase-hex SHA, optional final LF
```

Missing, unreadable, wrongly owned/moded, symlinked, non-regular or malformed state blocks GC. The coordinator and authority enforce the same contract independently. This ownership is intentional: the deploy coordinator is `astro`; a `root:astro 0750` directory would be unwritable and cannot be its request registry.

## Test structure

Do not continue growing the already large general harnesses with unrelated blocks.

- Keep the existing promotion suite as the end-to-end transaction matrix, updating only what the authority boundary requires.
- Add a focused promotion/authority failure-injection suite for outcome-unknown and reconciliation paths.
- Add a focused `gc-remove` authority suite for direct-capability safety.
- Keep the existing authority foundation/finalize cases and change only the old `gc-remove is unimplemented` argv case plus shared contracts.
- Add new suites to the canonical deploy matrix and namespace inventory.

Every sandbox substitutes fixed anchors with exact pre/post counts. No test may invoke real sudo, Git, systemctl, curl, `/opt/solarsage-runtime`, `/run/solarsage`, `/var/lib/solarsage`, or the installed helper.

## Manual-only boundary

This architecture authorizes only repository source, documentation and isolated sandbox tests. It does not authorize installing/invoking the helper, applying sudoers, changing real runtime pointers or flags, removing a real worktree, restarting services, changing Nginx/systemd/database state, deploying, committing or pushing.
