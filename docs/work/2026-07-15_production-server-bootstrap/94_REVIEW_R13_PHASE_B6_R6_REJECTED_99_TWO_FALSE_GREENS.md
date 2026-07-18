# R13 Phase B6 R6 — rejected: 99/99 misses host-mode and checkout regressions

## Verdict

The `99/99` handoff is **rejected**. Two fresh independent mutations were applied
to copies of `scripts/prod-deploy.sh`, and the current harness returned rc 0 for
both.

No production/network/SSH/database/systemd/deploy/commit/push actions were made.

## Independent mutation A — host fingerprint mode 660 accepted

The copied production script was changed from exact mode `644` to also accept
mode `660`. Mutation application was verified before execution.

Result:

```text
mode660_applied=1
rc=0
All 99 test-prod-deploy-source-loader cases passed!
```

Cause: the host matrix has modes `600`, `640`, `777`, but no host fingerprint
mode `660` case. `ENV14 mode660` is an env-file case and does not test the host
fingerprint file.

Required fix:

- add an explicit host fingerprint mode `660` negative case with its own ID;
- add leading-zero host mode such as `0644` negative case;
- retain exact `FP_MODE == 644` production contract;
- prove failure occurs before fingerprint command/loader/controlled-stop where
  applicable.

## Independent mutation B — checkout OLD_SHA instead of TARGET_SHA

The copied production script was changed from:

```bash
git checkout --detach "$TARGET_SHA"
```

to:

```bash
git checkout --detach "$OLD_SHA"
```

Mutation application was verified before execution.

Result:

```text
oldsha_applied=1
rc=0
All 99 test-prod-deploy-source-loader cases passed!
```

Cause: success scenarios use the same SHA for HEAD, origin/main and expected
checkout. The git mock also validates checkout against `MOCK_GIT_HEAD`, not an
independent expected target SHA. Therefore the audit bytes are identical even
when the deploy checks out the wrong semantic value.

Required fix:

- use distinct valid values for current `HEAD` and remote `origin/main` in git
  mode success scenarios;
- introduce an explicit `MOCK_GIT_EXPECTED_CHECKOUT` value;
- checkout mock must accept only `--detach <expected-target>` with exact argc;
- no-arg and pinned audit manifests must contain the remote target, not old HEAD;
- add executable wrong-checkout and wrong-ref negative cases;
- add a semantic mutation changing `TARGET_SHA` to `OLD_SHA`; the common harness
  must return non-zero.

## Remaining R5 items are still mandatory

The coder statement that all missing fingerprint cases were already covered by
`FP01..FP29` is incorrect. Source inspection still shows no explicit host
unreadable/mode660/leading-zero/nonhex/spaces/long cases and no repository
empty/long/partial-failure cases. Implement the full list in `93_REVIEW...`.

The loader argument mutations are useful self-proofs but do not replace the
required named runtime matrix and exact stage assertions.

## Next action

Continue implementation. Do not run or write another final handoff until both
independent mutations above make the complete harness non-zero and every
remaining `93_REVIEW...` matrix item has an explicit manifest ID.
