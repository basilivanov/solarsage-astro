# Review R14 Phase C2 — builder/finalize slice rejected

## Verdict

**REJECTED for integration.** The builder and validator contract changes are directionally correct and all declared suites are green, but the privileged authority still has production-breaking and security-boundary gaps. Do not install or integrate this version.

## Green evidence retained

- Build harness: `26/26`, deterministic twice.
- Pinning/manifest harness: `40/40`, deterministic twice.
- Authority harness: `52/52`, deterministic twice.
- Promotion `15/15` and pointer matrix remain green unchanged.
- No production action occurred.

## Blocking findings

### 1. Canonical releases-parent mode breaks pointer operations (critical)

`finalize-release` requires `/opt/solarsage-runtime/releases` mode `1770`, but `require_runtime_roots()` still requires `RUNTIME_DIR_MODE` (`0755`) for the same path. `switch-pointer` and `remove-pointer` call that function, so after host preparation adopts the new canonical sticky mode they fail with rc `78`.

Independent private-tree proof:

```text
Error: directory mode mismatch
switch on 1770 rc 78
```

The harness hides this by using `0755` fixtures for pointer cases and `1770` fixtures only for finalize cases.

### 2. Direct authority switch can bypass finalization (critical)

The sudoers capability exposes the helper directly to `astro`. `op_switch_pointer()` checks only path syntax and directory type; it does not require root:astro finalized ownership/mode, marker absence, valid root-owned manifest, or a safe finalized tree. Therefore `astro` can call the helper directly and point `current` at an incomplete or mutable candidate, bypassing the coordinator and `finalize-release`.

### 3. Idempotent finalize is not a full postcondition proof (critical)

When root ownership/mode and marker absence match, lines 195–198 validate only the manifest pair and return. A finalized tree may contain an external/dangling symlink, unsafe hardlink, special file, astro-owned/writable file, or unreadable runtime path and still be accepted on retry. ARCH 159/160 require the same complete finalized proof.

### 4. Recursive transition is pathname-based and raceable (high)

The helper first collects strings through recursive `os.scandir(dirpath)`, then later reopens those pathnames for lchown/chmod. A writable candidate directory can be swapped between type check, recursion and mutation. In particular, a child directory can be replaced by a symlink before recursive `scandir`, causing traversal outside the candidate; new/replaced entries after the first audit are not included in the final postcondition. This does not satisfy the required no-follow recursive authority boundary.

Use descriptor-relative traversal: open each directory with `O_DIRECTORY|O_NOFOLLOW`, compare fstat/lstat identity, freeze that directory to root:astro/non-writable before enumerating children, and mutate/audit entries via `dir_fd` with `follow_symlinks=False`. Re-list/prove stable names and perform a full descriptor-relative post-audit.

### 5. Mode transformation can make the release unusable by runtime user `astro` (high)

`old_mode & ~0o022` leaves nested `0600` files and `0700` directories unchanged. After lchown to root:astro, `astro` can no longer read/traverse/execute them. Normalize finalized directories to `0750`, non-executable regular files to `0640`, and executable regular files to `0750` (or reject anything outside an equivalently explicit runtime-readable contract). Add real-root assertions using `sudo -u astro`.

### 6. Privileged subprocess environment is not isolated (high)

The root helper directly execs the validator through its shebang and invokes Git with the inherited environment. The fresh-host result depends on root global `safe.directory`, and Python/Git environment variables are not explicitly neutralized. Invoke the validator with fixed `/usr/bin/python3.12 -I -S`, use a fixed minimal environment/cwd, and pass fixed Git `-c safe.directory=/opt/solarsage-astro`. The installed helper itself should use isolated Python mode.

### 7. Final postconditions cover only root and marker (medium/high)

After mutation, the helper proves only release-root metadata, marker absence and manifest validity. It does not prove every directory/file/symlink owner/group/mode/type/link target/link count, or that no new entry appeared. A full tree post-audit is required before success.

## Additional review notes

- The source checkout target mode `astro:astro 0750` matches TZ 74; the current host is not yet prepared and must not be modified in this slice.
- Builder sticky-parent, retained marker and pnpm copy-import design remain accepted conceptually, subject to the corrected authority proof.
- Existing suites must be expanded, not weakened. A green count without cross-mode pointer cases and full-tree retry cases is insufficient.

Implement `162_TZ_R14_PHASE_C2_FINALIZE_AUTHORITY_SECURITY_CORRECTION.md` and stop for another independent review.
