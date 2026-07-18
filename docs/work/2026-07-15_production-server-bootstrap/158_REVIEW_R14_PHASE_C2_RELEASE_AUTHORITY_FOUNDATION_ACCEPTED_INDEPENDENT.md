# Review R14 Phase C2 — release authority foundation accepted

## Verdict

**ACCEPTED for the source/test foundation only.** Installation and production invocation remain forbidden until the later host-integration and full promotion transaction reviews are accepted and the user explicitly commands rollout.

## Accepted files

- `scripts/prod-release-authority.py` (`0755`)
- `scripts/tests/test-prod-release-authority.sh` (`0755`)
- `infra/production/solarsage-deploy.sudoers` helper capability line

## Independent evidence

- `bash -n scripts/tests/test-prod-release-authority.sh` — rc `0`.
- `python3.12 -I -S -m py_compile scripts/prod-release-authority.py` — rc `0`.
- Two `timeout 180` harness runs — rc `0`, `34/34`, byte-identical output.
- Independent composite-failure probe — rc `78`, exactly one stderr line: `Error: switch-pointer failed`.
- `visudo -cf infra/production/solarsage-deploy.sudoers` — parsed OK.
- Fixed roots, canonical pointer targets, root:astro pointer ownership, root:root `0644` maintenance flag, `O_NOFOLLOW|O_EXCL`, no-follow directory fsync, exact argv validation, explicit unimplemented finalize/GC operations, root identity oracle, mutation self-proofs, and no-real-path gate are all covered.

## Boundary of this acceptance

The helper currently supports only pointer and maintenance-flag primitives. It is **not** yet a complete release authority: `finalize-release` and `gc-remove` are still intentionally unavailable; the builder still removes `.release-incomplete` itself; promotion still mutates pointers/flag without the installed helper. Those are the next reviewed slices.

No real `/run`, `/opt/solarsage-runtime`, sudoers installation, systemd/nginx/database action, deploy, commit, or push occurred.
