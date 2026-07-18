# R14 Phase C1A-R2 review — rejected: transaction implementation unchanged

## Verdict

C1A-R2 is **rejected**. The parser and direct harness improved: independent
direct runs now genuinely pass 73/73. However the production transaction path
is still the rejected R1 implementation, and the harness still does not execute
a commit failure or signal rollback.

No production/network/SSH/DB/Docker/systemd mutation, commit or push occurred.

## Independent baseline

```text
test-prod-env-loader.sh                  rc=0
test-prod-env-profiles.sh run 1          rc=0, 73/73
test-prod-env-profiles.sh run 2          rc=0, 73/73
test-prod-env-profiles-mutations.sh x2   rc=0, 8/8
test-prod-deploy-source-loader.sh        rc=0, 111/111
test-prod-host-offsite-routing.sh        rc=0
prod-infra-fingerprint.sh                rc=0
git diff --check                         PASS
stale temp directories                   0
```

These runs are no longer hidden by `tail`; the baseline is real. It remains
insufficient for the transaction contract.

## P0 — live profile loss is still reproducible

`scripts/prod-env-prepare.sh:59-76` still has rollback `cp/chown/chmod/rm/fsync`
with `|| true`. Lines 194-205 still call rollback directly, delete the snapshot,
then exit while `ROLLBACK_ACTIVE=1`, causing the EXIT trap to roll back a second
time with an empty snapshot.

Independent third-rename failure against the current file:

```text
current_apply_mv3_rc=1
old=0 changed=0 absent=7 mv_calls=3
```

All seven live profiles were removed. This is the same P0 as R1.

The error names the wrong failed profile because `rollback_profiles()` mutates
the global `fname` loop variable before the diagnostic is rendered.

## Why 73/73 did not catch it

The "Injected failure + rollback" section in
`scripts/tests/test-prod-env-profiles.sh:407-432` removes a required source key.
That fails before snapshot and before any live rename. It proves only that
pre-validation does not change an existing file; it does not exercise rollback.

The sandbox also mocks `stat`, `chown` and `chmod` for all arguments. Generated
files can therefore have wrong real metadata while the test reports canonical
metadata. No rename-position, fsync or HUP/INT/TERM case exists.

The mutation harness remains a direct-command behavior table, not a copied
canonical harness run. It has no prepare-script rollback or fsync mutation.

## Additional P1 issues

- `prod-env-tool.py:742-745` contains `traceback.print_exc()` left from debug.
  Unexpected exceptions may leak paths, values or internal data.
- `parse_source()` still rejects every plain `$`, although only backticks,
  `${` and `$(` are forbidden by the R2 contract.
- LLM provider is lowercased, accepting non-canonical case variants.
- `open_output_dir()` opens a safe fd, but render/verify then operate through
  the original pathname; a directory replacement race remains.
- profile reads are a single 1 MiB `os.read` without an explicit size/EOF
  contract.
- named-profile validation contains only `pass`; it does not actually perform a
  profile render/semantic check.

## Architecture decision

Do not attempt a fourth sequential seven-file rollback. C1B has not begun, so
the live path can still be corrected cleanly.

Implement immutable profile generations and one atomic `current` symlink as
specified in `105_TZ_R14_PHASE_C1A_R3_IMMUTABLE_ENV_GENERATIONS.md`. C1B will
point consumers to `/etc/solarsage/env/current/<profile>.env`.
