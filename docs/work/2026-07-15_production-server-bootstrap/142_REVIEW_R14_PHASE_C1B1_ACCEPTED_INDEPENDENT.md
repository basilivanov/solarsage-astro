# R14 Phase C1B1 — accepted independently

## Verdict

**Accepted independently.** The installed-profile runtime and clean runner now
meet the bounded C1B1 contract. The phase adds a trusted runtime primitive only;
production consumers remain intentionally unchanged for C1B2.

No production/network/service/database/SSH/Docker action, commit or push was
performed.

## Accepted scope

- `scripts/lib/prod-env-tool.py`
  - `run-installed`;
  - `run-clean`;
  - fd-relative current-generation/profile loading;
  - exact profile validation and isolated child environment.
- `scripts/prod-env-run.sh`
  - canonical production wrapper with trusted preflight PATH;
  - root/astro identity and root:astro env-dir guard.
- `scripts/tests/test-prod-env-runtime.sh`
- `scripts/tests/test-prod-env-runtime-root.sh`
- `scripts/tests/test-prod-env-runtime-mutations.sh`
- fingerprint/inventory additions in host tooling.

## Independent blocker probes

```text
FIFO .profile.lock (no writer, external timeout)  rc=14, no hang
TAB 0x09 in installed optional value              rc=14
VT  0x0B in installed optional value              rc=14
FF  0x0C in installed optional value              rc=14
invalid UTF-8 / NUL / CR / DEL / U+0001           covered, rc=14
hostile wrapper PATH                              PASS
module contract/map marker counts                 1 / 1 / 1 / 1
```

## Independent runtime evidence

```text
bash -n new runtime/wrapper harnesses                           rc=0
python3.12 -I -S compile(prod-env-tool.py)                      rc=0
bash scripts/tests/test-prod-env-runtime.sh                     rc=0
sudo -n bash scripts/tests/test-prod-env-runtime-root.sh        rc=0
bash scripts/tests/test-prod-env-runtime-mutations.sh           rc=0
```

Mutation output independently contained:

```text
[MUTATION EXECUTION] Ran root oracle for MUT12_WEAKEN_WRAPPER_METADATA
PASS: MUT12_WEAKEN_WRAPPER_METADATA
All 12 mutation cases passed!
```

The mutation harness now requires both `sudo -n` and a working `strace` before
any green baseline, rejects empty/failed trace logs and executes the real root
wrapper oracle when invoked as user `astro`.

## Independent adjacent regression evidence

```text
test-prod-env-loader.sh                    rc=0
test-prod-env-profiles.sh                  rc=0, 75/75
test-prod-env-install-transaction.sh       rc=0, 37/37
test-prod-env-profiles-mutations.sh         rc=0, 14/14
test-prod-env-root-identity.sh              rc=0
test-prod-deploy-source-loader.sh           rc=0, 111/111
test-prod-host-offsite-routing.sh           rc=0
prod-infra-fingerprint.sh                   4d878d5b707e98e82fc957891e15f24c8ba42cbd971cacc2076138a40427eaad
git diff --check                            rc=0
```

Final synthetic sandbox/process scans were clean. No real secret or canonical
production env path was read by the acceptance probes.

## Remaining work

- C1B2: switch systemd/Compose/backup/restore/offsite/deploy/host checks to
  `/etc/solarsage/env/current/*.env` or `prod-env-run.sh`; fail checkout
  `.env.production`; remove deprecated loader after the last caller is gone.
- C2: canonical database identity and SQLAlchemy parity.

C1B1 is closed. Any next task must be separately scoped; production launch
remains an explicit manual user command.
