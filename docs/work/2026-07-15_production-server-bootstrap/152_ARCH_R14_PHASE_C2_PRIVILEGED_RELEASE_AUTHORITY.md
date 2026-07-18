# Architecture R14 Phase C2 — privileged release authority

## Decision

Keep the deploy coordinator and build process as user `astro`, as specified by the immutable deploy architecture. Do not run repository build scripts, package managers, migrations, or application code as root.

Add one minimal root-owned release authority helper for filesystem mutations that `astro` cannot safely perform. The helper is installed outside the mutable checkout and invoked through one exact sudoers capability.

## Why this boundary is required

- `solarsage-deploy.service` target architecture uses `User=astro`.
- Immutable release directories and current/previous symlinks must be root-owned so runtime services running as `astro` cannot mutate deployed code or pointers.
- Current promotion code calls `lchown(... root:astro)` and creates a root-owned flag directly; those operations cannot succeed from a real `astro` process.
- Existing sandbox harnesses substitute root identity with the current user, so they prove transaction logic but not the production privilege boundary.

## Root helper

Canonical installed path:

```text
/usr/local/libexec/solarsage/release-authority   root:root 0755
```

Source/template remains in the repository and is installed byte-exact by host preparation. The helper contains no secret loading and never executes code from a release checkout.

Strict operations:

```text
finalize-release <40hex>
switch-pointer current|previous releases/<40hex>
remove-pointer current|previous
maintenance-on
maintenance-off
gc-remove <40hex>
```

Every operation uses compiled/fixed production roots, exact argv counts, lstat/no-follow validation, canonical SHA/path checks, fsync, and postconditions. Unknown operations or extra arguments return 78.

## Ownership contracts

```text
/opt/solarsage-runtime                     root:astro 0755
/opt/solarsage-runtime/releases            root:astro 0755
/opt/solarsage-runtime/releases/<sha>      root:astro 0750 or 0755, immutable after finalize
/opt/solarsage-runtime/current             root:astro symlink -> releases/<sha>
/opt/solarsage-runtime/previous            root:astro symlink -> releases/<sha>

/run/solarsage                             root:root 0755, tmpfiles-owned
/run/solarsage/maintenance                 root:root 0644 regular file
```

The Nginx maintenance flag is the `/run` path required by ARCH 77. Durable operation state remains separate under `/var/lib/solarsage/maintenance` as `astro:astro 0700/0600` per ARCH 79.

## Sudoers boundary

`astro` receives passwordless access only to the installed root-owned helper and the already enumerated systemctl restart commands. No shell, interpreter, wildcard executable path, arbitrary install, chmod, chown, rm, or git capability is granted.

The helper must validate all arguments itself because sudoers command matching alone is not the argument security boundary.

## Build/finalize sequence

1. `astro` creates and builds a detached candidate with `.release-incomplete`.
2. Candidate self-tests and manifest generation complete as `astro`.
3. Root authority verifies exact registered worktree/SHA, file types, manifest and incomplete marker.
4. Root authority finalizes ownership without following symlinks, publishes manifest metadata, removes the incomplete marker, fsyncs, and makes the release immutable to runtime user `astro`.
5. Promotion can switch pointers only to a finalized release.

## GC sequence

GC selection and policy remain in the unprivileged coordinator. Actual removal is performed only by `gc-remove <sha>` in the root authority, which binds to the canonical source repository, verifies exact worktree path/HEAD and protected-state preconditions passed through on-disk authority state, removes the worktree, proves absence, and fsyncs the release parent.

No caller-current-directory repository discovery is allowed.

## Testing requirement

Add a focused sandbox harness for argv validation, no-follow behavior, atomic pointer/flag operations, finalize postconditions, and GC path binding. Add a root-identity oracle using a private `/tmp` tree when passwordless sudo is available; ordinary astro tests must not be presented as proof of root ownership.

## Manual-only boundary

Installing or invoking the real helper, applying sudoers/tmpfiles/systemd, finalizing a real release, switching production pointers, or creating the real Nginx flag remains forbidden until the user explicitly orders production rollout.
