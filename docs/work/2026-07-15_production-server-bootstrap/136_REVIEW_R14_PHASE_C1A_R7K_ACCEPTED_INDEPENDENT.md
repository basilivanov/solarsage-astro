# R14 Phase C1A-R7K — independent acceptance

## Verdict

**Accepted independently.** The root:astro ownership gap, strict temporary
symlink cleanup, exact rollback states, and the two ownership mutations are now
covered by executable production-identity oracles. C1A is complete for this
scope.

No C1B/C2 work was started. No commit or push was made.

## Scope reviewed

- `scripts/lib/prod-env-tool.py`
- `scripts/tests/test-prod-env-install-transaction.sh`
- `scripts/tests/test-prod-env-profiles-mutations.sh`
- `scripts/tests/test-prod-env-root-identity.sh`

The review was performed on branch `infra/production-bootstrap` in the already
dirty worktree; unrelated pre-existing changes were left untouched.

## Independent evidence

### Static gates

```text
bash -n scripts/tests/test-prod-env-install-transaction.sh       rc=0
bash -n scripts/tests/test-prod-env-profiles-mutations.sh        rc=0
bash -n scripts/tests/test-prod-env-root-identity.sh              rc=0
python3.12 -I -S -m py_compile scripts/lib/prod-env-tool.py       rc=0
git diff --check                                               rc=0
```

### Production identity and recovery

Direct command:

```text
sudo -n env TOOL_OVERRIDE=/opt/solarsage-astro/scripts/lib/prod-env-tool.py \
  bash scripts/tests/test-prod-env-root-identity.sh
```

Observed:

```text
ROOT-A  rc=0  current=root:astro  generations=2  artifacts=0
ROOT-B1 rc=13 old pointer preserved; no artifacts; retry/check rc=0
ROOT-B2 rc=16 old pointer preserved; one .current-* retained; retry not run
ROOT-C1 rc=13 old pointer restored; rb=0; retry/check rc=0
ROOT-C2 rc=16 current=new; one .rb-* -> old; child gone; lock released
All requested root identity oracles passed!
```

An additional independent mutation changed only `current` symlink ownership to
`root:root`; `check-installed` returned `rc=14` with
`Error: current owner mismatch`.

### Transaction and mutation suites

```text
bash scripts/tests/test-prod-env-install-transaction.sh       rc=0, 37/37
bash scripts/tests/test-prod-env-install-transaction.sh       rc=0, 37/37
bash scripts/tests/test-prod-env-profiles-mutations.sh         rc=0, 14/14
```

The mutation output includes a canonical green baseline, twelve ordinary
transaction mutations, a canonical root baseline, and:

```text
MUT13_NO_CURRENT_CHOWN root oracle rejected mutant (rc=1; marker=current owner=root:root)
MUT14_ROLLBACK_CWD root oracle rejected mutant (rc=1; marker=.rb artifact count=0)
```

The root mutation runner uses `sudo -n`, exact-one source selectors, compile
gates, repository `.profile.lock` snapshots, and active-failure markers; it
does not silently skip when root capability is unavailable.

### Adjacent regression suites

```text
test-prod-env-loader.sh                rc=0
test-prod-env-profiles.sh              rc=0, 75/75
test-prod-deploy-source-loader.sh      rc=0, 111/111
test-prod-host-offsite-routing.sh      rc=0
scripts/prod-infra-fingerprint.sh      2d8edb42d1ed33b5d431d87284475fdf7cfca3b11b71f6c7c12c18104123bd6a
git diff --check                       rc=0
```

The final temporary-artifact scan returned `stale_tmp_count=0`; two stale
directories from an earlier interrupted coder run were verified dead and
removed before the final scan. No production host, service, database, nginx,
Docker, auth, or network state was changed.

## Handoff

C1A-R7K is accepted and the work stops here. The next authorized phase, if
requested separately, is C1B; it is not part of this handoff.
