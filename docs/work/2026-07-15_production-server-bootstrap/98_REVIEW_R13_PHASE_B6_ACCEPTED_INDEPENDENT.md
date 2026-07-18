# R13 Phase B6 — accepted independently

## Verdict

The production deploy source-loader/origin/fingerprint harness is **accepted**.
Acceptance is based on independent unfiltered executions and fresh adversarial
copies, not the coder case-count claim alone.

No production deploy, network, SSH, database, systemd, commit or push action was
performed.

## Accepted files

- `scripts/prod-deploy.sh`;
- `scripts/tests/test-prod-deploy-source-loader.sh`.

## Independent baseline evidence

```text
bash -n scripts/prod-deploy.sh scripts/tests/test-prod-deploy-source-loader.sh
PASS

run 1: rc=0
All 111 test-prod-deploy-source-loader cases passed!
stderr bytes: 0

run 2: rc=0
All 111 test-prod-deploy-source-loader cases passed!
stderr bytes: 0

git diff --check
PASS
```

After both runs:

```text
stale_harness_dirs=0
stale_sig_dirs=0
```

## Independent adversarial evidence

All mutations were applied to fresh copies and their application was verified
before executing the copied harness.

### A. Host fingerprint mode 660 accepted

```text
applied=1
harness rc=1
```

Caught by the explicit host mode matrix (`FP30`).

### B. Checkout OLD_SHA instead of TARGET_SHA

```text
applied=1
harness rc=1
```

Caught because current HEAD and target SHA are distinct and checkout mock accepts
only the exact expected target.

### C. Remove clean-source temp cleanup

```text
applied=1
harness rc=1
```

Caught by the per-case temp-leak guard. No stale harness directory remained
after the failed adversarial run.

## Accepted contracts

- exact CLI modes and byte-ordered audit manifests;
- exact private origin/access/fetch/ref/checkout flow;
- no transport in current mode;
- strict env-loader boundary and direct/indirect bypass mutations;
- exact loader argv/domain/export behavior;
- strict host and repository fingerprint physical records;
- real fingerprint/env canary leak scans;
- ephemeris path validation;
- lock/temp cleanup;
- real HUP/INT/TERM handler proof with exact 129/130/143 exit codes, holder
  termination and child-directory removal;
- fail-closed semantic mutation engine through MUT22.

## Next phase

Phase B6 acceptance closes only this deploy boundary. The broader production
readiness objective remains active: perform a cross-component audit and close
remaining automation/readiness gaps before exposing the single manual production
launch command.
