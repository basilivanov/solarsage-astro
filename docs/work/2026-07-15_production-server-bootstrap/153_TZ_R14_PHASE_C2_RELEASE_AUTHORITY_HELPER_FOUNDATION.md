# TZ R14 Phase C2 — release authority helper foundation

## Scope

Implement the source/template and isolated tests for the root-owned release authority described by ARCH 152. Do not install it, invoke it against real paths, or integrate production promotion yet.

Files allowed in this slice:

- `scripts/prod-release-authority.py` (new source helper);
- `scripts/tests/test-prod-release-authority.sh` (new focused harness);
- `infra/production/solarsage-deploy.sudoers` only to add the exact installed helper command if the template can remain syntactically and capability-safe.

Do not modify the accepted promotion/pointer harnesses or the production promotion library in this slice.

## Helper contract

The source helper is a strict Python CLI with GRACE module/function contracts and fixed production constants. It must reject unknown operations, extra arguments, non-canonical paths, symlinks, and malformed metadata.

Implement and test these operations now:

```text
switch-pointer current|previous releases/<40-lowercase-hex-sha>
remove-pointer current|previous
maintenance-on
maintenance-off
```

`finalize-release` and `gc-remove` remain explicit follow-up operations; do not stub them as successful commands.

## Security/atomicity requirements

- Fixed roots: `/opt/solarsage-runtime` and `/run/solarsage`; no caller cwd or user-supplied root.
- `switch-pointer`: only `current`/`previous`, only raw `releases/<40hex>`, target directory must exist and be a real non-symlink; create a unique same-directory temporary symlink without unlink races; lchown symlink `root:astro`; atomic replace; fsync directory; postverify raw target, resolved path, symlink type and uid/gid.
- `remove-pointer`: reject non-symlink entries and wrong owner/group; unlink only the exact named pointer; fsync directory; prove absence.
- `maintenance-on`: parent `/run/solarsage` must be a real directory with safe metadata; create `/run/solarsage/maintenance` with `O_NOFOLLOW|O_EXCL`, mode `0644`, owner `root:root`; fsync file and parent directory; existing entry is a failure, not an idempotent success.
- `maintenance-off`: only remove a regular non-symlink `root:root 0644` flag; fsync parent; wrong type/owner/mode is a failure.
- No raw `rm -rf`, shell interpolation, repository code execution, or silent exception swallowing.

## Focused harness

The test must run only in a private `/tmp` tree made by exact substitutions in a copied helper. It must include:

- ordinary unprivileged/sandbox contract cases;
- a root-identity oracle through `sudo -n` against only the private tree when available;
- exact argv/operation validation;
- symlink traversal, wrong type, dangling, wrong owner/group/mode, existing flag, and fsync-failure mutation cases;
- a mutation self-proof that removing `O_NOFOLLOW|O_EXCL` or postverify makes the same oracle non-zero;
- deterministic two-run output and a no-real-path/no-production-action gate.

If passwordless sudo is unavailable, the root-identity portion must fail as an explicitly reported unmet acceptance gate; it must not be silently skipped or reported green.

## Verification

```bash
bash -n scripts/tests/test-prod-release-authority.sh
python3.12 -I -S -m py_compile scripts/prod-release-authority.py
timeout 180 bash scripts/tests/test-prod-release-authority.sh
visudo -cf infra/production/solarsage-deploy.sudoers   # only if sudoers template changed
```

No real `/run`, `/opt/solarsage-runtime`, systemd, nginx, sudoers installation, deploy, or production service action is allowed. Stop after this helper foundation for independent review.
