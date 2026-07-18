# Architecture R14 Phase C2 — sticky release staging and privileged finalization

## Problem resolved

The deploy worker is `User=astro`, while finalized releases must be root-owned and the releases parent must prevent `astro` from deleting or renaming them. A parent mode of `root:astro 0755` also prevents `astro` from creating a new worktree, so ARCH 152's build/finalize sequence is otherwise impossible.

## Decision

Use one in-place Git worktree namespace with a sticky, group-writable parent:

```text
/opt/solarsage-runtime                     root:astro 0755
/opt/solarsage-runtime/releases            root:astro 1770
/opt/solarsage-runtime/releases/<sha>      astro:astro while incomplete
/opt/solarsage-runtime/releases/<sha>      root:astro 0750 after finalization
```

The sticky bit lets `astro` create and remove its own incomplete candidate directories, while preventing it from deleting or renaming finalized child directories owned by root. `current` and `previous` remain under the non-writable runtime root.

No separate movable staging worktree is introduced; this avoids Git worktree-path relocation and keeps the canonical registry path stable.

## Builder contract correction

- The builder must require the pre-created releases parent to be a real non-symlink `root:astro 1770`; it must not create or chmod that production parent itself.
- Dependency installation must avoid external hardlinks before privileged recursive ownership change. Use pnpm package import method `copy` and prove it in the build harness.
- A successful build writes and validates the manifest pair but leaves `.release-incomplete` present. It reports a built candidate awaiting privileged finalization.
- Failed incomplete candidates remain owned by `astro`, so the existing validated Git worktree cleanup can remove them under the sticky parent.

## Finalize-release authority

Add strict operation:

```text
finalize-release <40-lowercase-hex-sha>
```

The operation uses fixed paths only and:

1. validates runtime and sticky releases-parent metadata;
2. validates exact candidate path, owner/group/mode, `.release-incomplete`, and canonical Git worktree registry binding to `/opt/solarsage-astro` with exact HEAD SHA;
3. validates the candidate manifest through the fixed, root-owned installed manifest validator, never through code inside the candidate;
4. recursively inspects without following symlinks, rejects special files, external/dangling symlinks and unsafe hardlinks, then lchowns entries `root:astro` and removes group/other write bits while preserving required execute/read bits;
5. revalidates root-owned manifest metadata while the incomplete marker is still present;
6. removes the exact regular incomplete marker, fsyncs the release and parent, validates the normal finalized manifest, and proves all postconditions;
7. accepts an already-finalized release only after the same complete postcondition proof (safe retry/idempotence).

The fixed installed manifest validator path is:

```text
/usr/local/libexec/solarsage/release-manifest
```

Host preparation will install it root:root `0755` in a later slice. The authority never imports or executes code from a candidate checkout.

## Manifest validator modes

Preserve existing normal and `--candidate` behavior, and add a strict root-owned finalizing validation mode if needed. Candidate/finalizing modes require the incomplete marker to be an exact regular non-symlink file with expected ownership/mode; normal mode requires it absent.

## Safety boundary

This document authorizes only source/template and sandbox work. It does not authorize changing the real runtime parent mode, installing helpers, finalizing a real release, or invoking production Git/systemd/nginx/database operations.
