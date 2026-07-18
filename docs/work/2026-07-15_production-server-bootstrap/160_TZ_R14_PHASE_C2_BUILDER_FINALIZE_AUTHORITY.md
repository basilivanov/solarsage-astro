# TZ R14 Phase C2 — builder/finalize authority slice

Read fully before changes:

- `77_ARCH_IMMUTABLE_RELEASE_DEPLOY.md`
- `146_TZ_R14_PHASE_C2_IMMUTABLE_PROMOTION_AND_FULL_PROD_READINESS_HANDOFF.md`
- `152_ARCH_R14_PHASE_C2_PRIVILEGED_RELEASE_AUTHORITY.md`
- `158_REVIEW_R14_PHASE_C2_RELEASE_AUTHORITY_FOUNDATION_ACCEPTED_INDEPENDENT.md`
- `159_ARCH_R14_PHASE_C2_STICKY_RELEASE_STAGING_AND_FINALIZATION.md`

## Scope

Implement only the in-place candidate/finalize boundary. Do not integrate promotion/rollback/GC yet and do not install or invoke anything against real production paths.

Allowed files:

- `scripts/prod-release-authority.py`
- `scripts/tests/test-prod-release-authority.sh`
- `scripts/lib/prod-release-build.sh`
- `scripts/tests/test-prod-release-build.sh`
- `scripts/lib/prod-release-manifest.py` and `scripts/tests/test-prod-release-pinning.sh` only for the strict finalizing/candidate validator mode required by ARCH 159

Do not change promotion/pointer code or their accepted harnesses.

## Required implementation

### Builder

- Require releases parent real non-symlink `root:astro 1770`; fail if missing/wrong. In sandbox, use exact identity/path substitutions—no production override in source.
- Do not create/chmod the parent.
- Use pnpm `--package-import-method=copy` (or byte-equivalent explicit config) and assert exact argv in tests.
- On successful build, keep exact regular `.release-incomplete` owned by the build user, mode `0600`; manifest pair exists and validates as candidate; do not claim finalized/signed-off release.
- Preserve validated cleanup for failed astro-owned candidates.

### Manifest validator

- Candidate mode must require an exact regular non-symlink incomplete marker with expected candidate metadata.
- Add only the minimal finalizing mode needed to validate root-owned manifest files while the marker remains present.
- Normal validation continues to require marker absence. Preserve schema/checksum/secret guarantees and all accepted pinning cases.

### Authority helper

- Add exact argv operation `finalize-release <sha>`; `gc-remove` remains unimplemented.
- Fixed constants: runtime, releases, source repo, installed manifest validator, absolute `/usr/bin/git`.
- Bind only to canonical source repo; never discover repo from cwd. Use exact worktree registry path and HEAD SHA.
- Candidate must be real, exact SHA path, `astro:astro`, allowed mode, registered worktree, with valid candidate manifest and marker.
- No-follow recursive walk. Reject sockets/FIFOs/devices, dangling/external symlinks, and regular files with unsafe link count. Never chown through symlinks.
- Transition every accepted entry to root:astro, remove group/other write permissions, set release root to `0750`, preserve required executable bits, and prove postconditions.
- Validate root-owned finalizing manifest before removing marker; remove only the exact marker; fsync release and releases parent; normal manifest validation after removal.
- Already-finalized retry may return 0 only after full finalized proof.
- All expected failures: fixed one-line error, rc `78`, no traceback/raw path.

## Focused proof requirements

- Extend authority harness with ordinary and real-root oracle cases for finalize success and idempotent retry.
- Exact Git mock registry/argv; no real git.
- Reject: malformed SHA, missing/wrong marker, manifest mismatch, unregistered path, registry HEAD mismatch, target symlink/file, wrong parent metadata, wrong candidate owner/group/mode, external/dangling symlink, FIFO/socket/device, unsafe hardlink, validator failure, chown/chmod/unlink/fsync failure.
- Prove marker stays on every pre-finalization failure; after success it is absent and tree/manifest are root:astro/non-writable to astro.
- Mutation self-proofs for marker guard and hardlink or external-symlink guard.
- Update builder harness honestly: parent `1770`, pnpm copy import, successful marker retained, manifest candidate-valid, no false finalized claim.
- All copied scripts use exact-count substitutions with pre/post assertions and no real-path residue.

## Verification

```bash
bash -n scripts/lib/prod-release-build.sh scripts/tests/test-prod-release-build.sh scripts/tests/test-prod-release-authority.sh
python3.12 -I -S -m py_compile scripts/prod-release-authority.py scripts/lib/prod-release-manifest.py
timeout 180 bash scripts/tests/test-prod-release-build.sh
timeout 180 bash scripts/tests/test-prod-release-authority.sh
timeout 180 bash scripts/tests/test-prod-release-pinning.sh
```

Run each changed focused suite twice and prove byte-identical output. Also rerun accepted promotion/pointer suites unchanged as regression checks. No real `/opt`, `/run`, Git registry, sudoers install, service, nginx, database, deploy, commit, or push action. Stop for independent review.
