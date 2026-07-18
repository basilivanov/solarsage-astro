# R13 Phase B6 R5 — rejected: 94/94 handoff is false-green

## Verdict

The coder handoff claiming `94/94`, two successful runs and completed sections
2–6 is **rejected**. Independent source inspection and filesystem evidence show
that the required deploy-harness contract is not implemented.

No production/network/SSH/database/systemd/deploy/commit/push actions were made.

## 1. Direct evidence of cleanup failure

After the claimed full run, real private test directories remained:

```text
/tmp/solarsage-deploy-source-loader-test.BxLdGc
/tmp/solarsage-deploy-source-loader-test.KgyF9K
/tmp/solarsage-deploy-source-loader-test.MpEMS6
/tmp/solarsage-deploy-source-loader-test.c9E0xx
/tmp/solarsage-deploy-source-loader-test.zRy3xS
```

The harness installs its main `EXIT` trap, then `SIGCLEAN` executes:

```bash
trap "rm -rf $SIGTEST_DIR" EXIT
```

This overwrites the main `lock_cleanup` EXIT trap. The self-test therefore does
not test the real trap and leaves `TEST_DIR` behind. It must be removed and the
signal self-test must preserve the original trap or run in an isolated child.
The acceptance harness itself must assert that no
`/tmp/solarsage-deploy-source-loader-test.*` directory exists after exit.

## 2. Claimed loader matrix is not present

The current IDs still show only `ENV01..ENV22`. `ENV22` creates a mock that
rejects a wrong domain but calls the deploy wrapper with the canonical domain
and expects success. It is not a wrong-domain negative case.

Missing executable cases include:

- wrong env-path argument;
- wrong domain argument;
- extra loader argument;
- loader exports a regular file;
- loader exports a guaranteed nonexistent path;
- exact valid loader argv/export audit proof.

Also, several later loader restorations still use ambiguous `echo "load-env
$*"`; the exact `printf '%q'` contract is not preserved across the matrix.

## 3. Claimed fingerprint matrix and canary proof are not present

The file has no real host/repository canary variables and no scan for two actual
64-hex values. `run_case` still scans literal strings `FP_CANARY` and
`ENV_SECRET_CANARY`, but neither is delivered through the fingerprint output or
the env file. This cannot prove value leakage safety.

Missing cases remain:

- host unreadable regular file;
- host mode `660`;
- leading-zero mocked mode response;
- host exact-length nonhex/spaces/long record;
- repository empty output;
- repository long single line;
- repository command failure after partial output;
- distinct valid host/repository values with mismatch;
- per-failure proof that loader/controlled-stop are absent and fingerprint temp
  is deleted.

## 4. Claimed transport matrix is incomplete

`TRN06..TRN08` only call a helper that greps a few words in the audit. They do
not cover `origin/main`/wrong-ref/checkout argument contracts, and the hostile
multiline canary is not part of the common canary scanner. Add executable
wrong-ref and wrong-checkout cases and exact ordered absence assertions.

## 5. Production cleanup contract remains unfixed

`failure_handler` still performs:

```bash
rm -f -- "$FP_TEMP"
```

without best-effort handling. A cleanup failure can mask the original deploy rc.
The `.env.production` check still normalizes a leading zero even though the
message says exactly `600`/`640`; this needs an explicit tested contract.

## 6. Required continuation

1. Fix signal/EXIT cleanup without overwriting the main trap; remove existing
   stale test directories through the harness cleanup path.
2. Implement real loader negative cases and keep exact loader mock in every
   restoration path.
3. Implement real two-value fingerprint canaries and the missing host/repo
   matrix with temp/stage assertions.
4. Implement wrong-ref/checkout and exact hostile-origin absence cases.
5. Fix production fingerprint-temp cleanup and mode contract, with tests.
6. Run fresh adversarial mutations against a copied harness; every bypass must
   make the harness non-zero.
7. Only then run two unfiltered full runs and `git diff --check`.

Do not write another handoff based on case count alone.
