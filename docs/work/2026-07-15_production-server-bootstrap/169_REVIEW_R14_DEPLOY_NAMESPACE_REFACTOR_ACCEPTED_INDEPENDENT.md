# Review R14 — deployment namespace refactor accepted independently

## Verdict

**ACCEPTED.** The canonical deployment surface is consolidated under `scripts/deploy/`, active references are migrated, the privileged helper remains self-contained, and the final verification contracts no longer contain the identified false-green edges.

## Independent evidence

- Legacy repository-root discovery resolves `scripts/deploy/legacy/../../..` to the repository root for `backup.sh`, `deploy.sh` and `db-create.sh`.
- Namespace/layout contract passes independently with:
  - active workflow/infra/scripts/docs stale-reference scan;
  - exact README inventory and mechanical compatibility coverage;
  - missing-row, duplicate-row, stale-doc and stale-script mutation proofs.
- `bash -n` passes for every shell file under `scripts/deploy/`.
- isolated Python compilation passes for every Python file under `scripts/deploy/`.
- release authority/build/pinning/promotion/pointer suites pass independently with retained counts: `63`, `26`, `40`, `15`, pointer matrix plus mutation.
- independent canonical matrix run passes:
  - 24 suites green twice;
  - exact per-suite exit-code ledgers identical and every code `0`;
  - canonicalizer self-proof green;
  - canonical transcripts byte-identical;
  - raw transcripts explicitly reported non-identical only for generation IDs, anchored Bash Hangup PIDs, outer run labels and known `/tmp/solarsage-*` sandbox roots.

## Accepted layout boundary

- Canonical source, libraries, tests and legacy operator tools live under `scripts/deploy/`.
- No compatibility implementation remains at the old source paths.
- Installed privileged helper path remains `/usr/local/libexec/solarsage/release-authority`; no installation occurred.
- Historical `docs/work/**` path references remain historical by design; active docs use the canonical namespace.

## Explicit non-actions

No real production release, `/opt/solarsage-runtime` mutation, `/run` mutation, service/nginx/database operation, Git registry mutation, sudoers installation, commit, push, reset or checkout was performed.
