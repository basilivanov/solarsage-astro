# Checkpoint inventory — TZ171 stopped mid-implementation by user directive

Status: **partial, frozen by user**. TZ171 (promotion/rollback authority integration + gc-remove) is NOT complete. This document only inventories the current diff, observed check results and known unfinished places. No acceptance is claimed.

## Changed files

### 1. `scripts/deploy/prod-release-authority.py` — modified, internally consistent

- New constant: `REQUESTS_DIR = "/var/lib/solarsage/requests"` plus `REQUESTS_DIR_MODE 0o700`, `REQUEST_FILE_MODE 0o600`.
- New block `GC_OPS` with reusable helpers:
  - `read_pointer_sha(name)` — optional canonical pointer read; absent vs malformed (malformed blocks GC, rc 78).
  - `read_running_requests()` — fail-closed astro:astro 0700/0600 request registry validation; returns referenced SHAs.
  - `query_worktree_registry()` — fixed source-repo binding + isolated porcelain query.
  - `parse_worktree_registry(output)` — block parser, duplicate block rejected.
  - `op_gc_remove(sha)` — finalized-target proof, current/previous/request protection, releases enumeration (unknown entries block; exact incomplete astro candidates preserved), deterministic `(mtime_ns, sha)` two-newest protection, detached registry binding with exact HEAD, only `git worktree remove --force`, filesystem + registry absence proofs, releases-parent fsync.
- `main()` dispatch: `gc-remove` with exact arity; fixed rc 78 boundary preserved.
- Module contract/map updated: obsolete "gc-remove is not implemented" invariant removed; `GC_OPS` block and new owned test listed.
- `finalize-release`, pointer and flag operations untouched.

### 2. `scripts/deploy/lib/prod-release-promotion.sh` — fully rewritten, syntactically valid

- One authority bridge: `_prod_prm_authority()` → `/usr/bin/sudo -n -- /usr/local/libexec/solarsage/release-authority "$@"`.
- Removed: `_prod_prm_python_switch`, `_prod_prm_create_flag`, `_prod_prm_delete_flag`, direct pointer `rm`, direct `git`/`rev-parse`/worktree removal.
- New helpers: `_prod_prm_read_optional_pointer`, `_prod_prm_prove_pair`, `_prod_prm_authority_switch`, `_prod_prm_authority_remove`, `_prod_prm_restore_pair`, `_prod_prm_flag_require_state`, `_prod_prm_maintenance_on/off`, `_prod_prm_persist_phase`, `_prod_prm_mark_recovery_required`, `_prod_prm_recover_after_failure`, `_prod_prm_validate_requests`, `_prod_prm_release_order_newest_first`.
- Maintenance flag cutover to `/run/solarsage/maintenance` root:root 0644 through authority; coordinator validates state after every call (non-zero rc = outcome-unknown, re-read).
- `services_switching` persists before pointer mutation; `health_verified` then `completed` before maintenance-off.
- First-install activation failure: best-effort checked pointer removal, flag retained, `recovery_required` persisted, never reports successful rollback.
- GC coordinator: fail-closed request registry validation (astro:astro 0700/0600, one exact SHA per entry), protects current/previous/requested/two-newest (deterministic `(mtime_ns, sha)`), invokes authority `gc-remove <sha>` per eligible release, stops on first failure, increments count only after rc 0 + local absence proof. No Git in the library.
- `_prod_prm_read_pointer`, `_prod_prm_validate_candidate`, health/restart helpers, self-exec maintenance runner unchanged.

### 3. `scripts/deploy/tests/test-prod-release-promotion.sh` — PARTIAL EDIT, SUITE RED

- Updated: path/identity/command substitution block (new `/run/solarsage/maintenance`, authority-bridge mock anchor count 2, removed git/python-identity anchors) and static no-real-path gates (now also rejects `/usr/local/libexec/solarsage`, removed impl names, `rev-parse`, `worktree remove`).
- NOT updated (still on the old contract, suite fails at setup): mock `release-authority` binary missing; mock `git` and git fixtures stale; `assert_flag` still checks old `/var/lib` flag path/mode 600; CASE09/10/13 still assert git argv instead of authority argv; oracle scripts still reference old flag path and git counts; MUT01/MUT02 anchors (`_prod_prm_python_switch ...`, `worktree remove --force "$d"`) no longer exist.
- Known unfixed substitution-order issue on this host (`CURRENT_USER=astro`): anchors `"$owner" != "astro"` must be substituted BEFORE `"$owner" != "root"` → `$CURRENT_USER` replacements, otherwise pre-counts shift (observed: expected 2, got 5). Fix was forbidden by the stop directive.
- Observed result: `FAIL: replace_exact pre-count mismatch for anchor ["$owner" != "astro"] ... expected 2 got 5` (suite exits at setup).

### 4. `scripts/deploy/tests/test-prod-release-pointer-contract.sh` — counts updated, NOT re-verified

- Substitution counts updated for the new library (`/var/lib/solarsage/maintenance` anchor removed; `/run/solarsage/maintenance` 1; `"$group" != "astro"` 4; `"$owner" != "astro"` 2 placed before root→astro replacements; `"$group" != "root"` 1; authority-bridge anchor 2; static gate extended).
- `_prod_prm_read_pointer` mutation anchor untouched (function unchanged).
- Suite was red before the order fix (same astro-host issue); after the applied order fix it was NOT re-run (stop directive). Current state: expected green, unverified.

## Observed check results (raw, unmasked where applicable)

| Check | Result |
|-------|--------|
| `bash -n scripts/deploy/lib/prod-release-promotion.sh` | 0 |
| `bash -n scripts/deploy/tests/test-prod-release-promotion.sh` | 0 |
| `bash -n scripts/deploy/tests/test-prod-release-pointer-contract.sh` | 0 |
| `python3.12 -I -S -m py_compile scripts/deploy/prod-release-authority.py` | 0 |
| `prod-release-authority.py gc-remove not-a-sha` | rc 78, `Error: invalid release SHA format` |
| `prod-release-authority.py gc-remove` (missing arg) | rc 78, `Error: gc-remove requires exactly 1 argument` |
| `test-prod-release-authority.sh` | 63/63 green (run once; predates promotion-harness edits) |
| `test-prod-release-promotion.sh` | RED at setup (expected, mid-migration) |
| `test-prod-release-pointer-contract.sh` | RED before order fix; not re-run after fix |

## Explicitly not done (by stop directive)

- No new suites (`test-prod-release-promotion-authority.sh`, `test-prod-release-gc-authority.sh`) and no new files anywhere.
- No `test-prod-release-authority.sh` changes; ARGV03 case name "gc-remove is not implemented" is now semantically stale (case still returns 78 via missing runtime roots, suite green).
- No `run-deploy-matrix.sh`, `scripts/deploy/README.md`, namespace-test changes (consistent: no new files exist).
- No first-install named case, no authority failure-injection coverage, no gc-remove harness coverage.
- No production actions: no real helper install/invocation, no pointer/flag/worktree mutation, no sudoers/systemd/nginx/DB, no deploy, no commit/push/reset/checkout.

## Resume notes for the next slice

1. Finish `test-prod-release-promotion.sh` migration: mock release-authority with argv ledger, update helpers/flag/assertions/CASE09-13/oracles/MUT anchors; astro-host order rule — substitute `"$owner" != "astro"` and `"$group" != "astro"` before any `!= "root"` → `$CURRENT_*` replacements.
2. Re-run pointer-contract after order fix to confirm green.
3. Decide the fate of authority-harness ARGV03 naming and gc-remove harness coverage per the new minimal-production-contour TZ the user announced.
