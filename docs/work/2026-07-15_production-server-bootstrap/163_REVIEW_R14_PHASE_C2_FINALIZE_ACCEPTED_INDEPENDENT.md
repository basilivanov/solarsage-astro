# Review R14 Phase C2 — finalize authority correction accepted

## Verdict

**ACCEPTED for source integration.** The correction closes the blocking authority findings from review 161. It remains a source-only acceptance: no helper was installed, no real release was finalized, and no production runtime metadata or services were touched.

## Independent evidence

The focused and regression suites were run independently after the coder stopped:

- `bash -n scripts/tests/test-prod-release-authority.sh scripts/lib/prod-release-build.sh scripts/tests/test-prod-release-build.sh` — `0`.
- `python3.12 -I -S -m py_compile scripts/prod-release-authority.py scripts/lib/prod-release-manifest.py` — `0`.
- authority — `63/63`, exit `0`.
- release build — `26/26`, exit `0`.
- pinning/manifest — `40/40`, exit `0`.
- promotion — `15/15` (13 cases plus 2 mutation proofs), exit `0`.
- pointer contract — matrix green (11 cases plus mutation), exit `0`.

Each suite was also run twice by the coder with byte-identical output; the independent single runs reproduced the green result.

## Findings verified

- One canonical `root:astro 1770` releases parent is required by finalize, switch and remove.
- Pointer switching invokes a reusable complete finalized-release proof.
- Idempotent finalize uses the same full proof rather than manifest-only validation.
- Candidate transition and retry audit are descriptor-relative, no-follow and inode/entry-set checked.
- Finalized modes are deterministic (`0750` directories/executables, `0640` other regular files) and the real-root oracle proves `astro` can read/traverse the result.
- External/dangling symlinks, special files, unsafe hardlinks, wrong nested modes and post-audit mutation are covered by named cases and mutation proofs.
- Validator and Git subprocesses use fixed executables, isolated environment/cwd, `-I -S`, and an explicit Git `safe.directory` argument.
- The authority entrypoint itself uses an isolated Python shebang and preserves the fixed rc `78` error boundary.

## Follow-up prerequisite

The current host has `/usr/bin/python3.12` owned by `basil:basil`. The production host-preparation/readiness gate must fail closed unless the fixed interpreter used by the installed helper satisfies the intended ownership/type/mode contract. This is not a reason to weaken the helper’s check and is outside this source-only slice.

## Explicit non-actions

No real `/opt` or `/run` release tree, systemd, nginx, database, Git registry, sudoers installation, commit, push, reset, checkout or production deploy was performed.
