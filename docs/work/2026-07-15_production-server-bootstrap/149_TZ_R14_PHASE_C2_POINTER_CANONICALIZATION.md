# TZ R14 Phase C2 — canonical current/previous pointer parsing

## Scope

Change only:

- `scripts/lib/prod-release-promotion.sh`;
- `scripts/prod-release-promote.sh` only if the library contract strictly requires it.

Do not modify the accepted harness `scripts/tests/test-prod-release-promotion.sh` in this slice. Do not modify accepted env/source/maintenance/release-builder dependencies.

## Problem

The architecture requires relative links:

```text
current  -> releases/<40-lowercase-hex-sha>
previous -> releases/<40-lowercase-hex-sha>
```

The writer already emits that form, but `prod_rel_promote` validates old current as if the raw link target dirname were the absolute `$PROD_PRM_RELEASES_DIR`. This makes every second promotion fail before maintenance mode.

## Required implementation

1. Add one internal GRACE-contracted helper for reading/validating a release pointer.
2. The raw `readlink` value must be exactly `releases/<40 lowercase hex>`; reject absolute paths, traversal, extra components, empty targets, dangling links, and non-symlink entries.
3. Verify the symlink lstat owner/group against production `root:astro` (the sandbox substitutions in the accepted harness must continue to work).
4. Derive the SHA from the validated raw target and prove the resolved target equals `$PROD_PRM_RELEASES_DIR/<sha>` and is a real non-symlink release directory.
5. Use the same helper consistently for old current/previous in promote, current/previous in rollback, and protected current/previous in GC. Do not interpolate filesystem paths into unescaped regexes.
6. Keep the canonical writer form relative (`releases/<sha>`). Do not switch writers to absolute symlinks.
7. Preserve first-install semantics where current/previous may be absent. A dangling or non-symlink entry is never treated as absent.
8. Do not weaken candidate/manifest validation and do not change expected test rc values.

## Restrictions

- No production deploy, service restart, nginx/systemd action, DB action, commit, or push.
- No `git checkout`, `git restore`, or `git reset`.
- No internal subagents.
- No reasoning/debug comments.
- No changes to real `/opt/solarsage-runtime`, `/run`, or `/var/lib`.

## Verification

Run from a fresh shell:

```bash
bash -n scripts/lib/prod-release-promotion.sh scripts/prod-release-promote.sh \
  scripts/tests/test-prod-release-promotion.sh
timeout 180 bash scripts/tests/test-prod-release-promotion.sh
```

Report the exact new pass/fail set. Stop after this pointer slice even if the harness exposes later transaction defects; those will receive a separate review/TZ. Production files must be the only code files changed.
