# R14 Phase C1B2 — independent review rejected on CLI validation order

## Verdict

**Rejected for one correctness blocker.** The operational profile cutover is
otherwise materially implemented, but three direct maintenance/backup scripts
do not preserve their public CLI contract when called outside the installed
profile wrapper.

No production, network, service, database, Docker daemon, commit or push action
was performed during this review.

## Independently confirmed

The following C1B2 checks were green before this blocker was found:

```text
systemd-analyze verify for all five changed units                  rc=0
test-prod-profile-consumer-cutover.sh                             rc=0
backup/offsite/restore/host-offsite regression suites              rc=0
bash -n for changed scripts and new helper/test                    rc=0
static target scan: no .env.production / prod_env_load             PASS
git diff --check                                                    rc=0
```

The Gemini handoff also reported the C1A/C1B1 regression set green. Those
results remain useful, but they do not cover the invalid-argument ordering
below.

## Blocker — context bridge runs before strict CLI parsing

`prod-backup.sh`, `prod-offsite-check.sh` and
`prod-offsite-maintenance.sh` invoke `prod_profile_require` before validating
their command line. With an empty environment and an invalid option, the
scripts therefore try to locate/re-enter the installed profile wrapper first
and return profile/wrapper failure `1` instead of the documented usage error
`2`:

```text
scripts/prod-backup.sh --bad                         rc=1 (expected 2)
scripts/prod-offsite-check.sh --bad                  rc=1 (expected 2)
scripts/prod-offsite-maintenance.sh --bad            rc=1 (expected 2)
```

This violates the C1B2 TZ requirement to keep **CLI parsing and exact exit
codes**, and makes a typo depend on `/etc/solarsage/env/current` availability.
It also means the public usage contract cannot be tested or diagnosed on a
fresh/unprepared host. `prod-db-restore.sh` already has the required order and
is not part of this correction.

## Required correction

For each of the three affected scripts:

1. Parse and validate only the supported arguments first.
2. On an invalid shape/value, print the existing usage line and exit `2`.
3. Only after successful parsing, source/check the profile-context helper and
   call `prod_profile_require`.
4. Do not perform DB, Restic, filesystem, service or network side effects
   before the bridge succeeds.

The accepted profile-context behavior, argv boundaries, marker checks and
fail-closed wrapper checks must remain unchanged. Do not weaken the runtime
profile boundary or restore any checkout `.env.production` fallback.

## Required regression proof

Add or extend a test that invokes each direct script with an invalid argument
under a deliberately empty environment and asserts:

```text
backup --bad                         rc=2 and usage text
offsite-check --bad                  rc=2 and usage text
offsite-maintenance --bad            rc=2 and usage text
```

The test must prove this happens before profile lookup/re-entry. It must not
read a real profile, print a secret, contact Restic, contact PostgreSQL or
start a service. Keep the existing valid-wrapper, nested-call and safety
coverage intact.

## Scope lock

Change only the CLI-order logic and its regression proof. Do not begin C1B3 or
C2, delete the legacy loader, deploy, build, migrate, restart services, or
commit/push. Hand off the exact changed files, command output and exit codes,
then stop for independent review.
