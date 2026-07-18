# R13 Phase B5 — workflow deploy guard accepted independently

## Verdict

**ACCEPTED** for the production-preparation branch.

This acceptance covers the bounded validator and mutation harness for:

- `.github/workflows/source-readiness.yml`;
- `.github/workflows/deploy-production.yml`;
- exact manual-only trigger and repository/SHA/private gate;
- exact secret locations and secret-expression syntax;
- exact Configure SSH commands and redirects;
- exact ordered SSH argv and forced command;
- exact cleanup contract;
- restricted YAML/parser fail-closed behavior;
- safe symbolic diagnostics;
- static full-tuple mutation manifest.

It does **not** authorize production launch, real GitHub Actions, SSH, deploy, commit, or push.

## Independent baseline

Run by the architect after the coder stopped:

```text
bash -n harness                         rc 0
py_compile via /tmp                     rc 0
canonical source-readiness              rc 0
canonical deploy                        rc 0
harness independent run 1               73/73, rc 0, stderr empty
harness independent run 2               73/73, rc 0, stderr empty
git diff --check                        rc 0
repo-local __pycache__ / *.pyc          absent
workflow test temp directories          absent
```

The harness uses a static manifest of exact tuples:

```text
case_id|workflow_type|symbolic_code|numeric_code
```

Sorted full tuples are compared with `cmp -s`; expected tuples are not generated from runtime case arguments.

## Independent adversarial proof

The architect created only temporary copies outside the repository. All tested unsafe forms now return nonzero with exactly one sanitized symbolic diagnostic line.

Rejected categories:

- scalar or nonempty `on.workflow_dispatch`;
- scalar concurrency;
- timeout zero;
- scalar `run` for gate, Configure SSH, trigger, and cleanup;
- gate condition prefix/suffix bypass;
- command substitution in a gate diagnostic;
- YAML tags and structural inline comments;
- secret expression in top-level scalar;
- malformed and dynamic/bracket secret expressions;
- `continue-on-error` on SSH/cleanup;
- extra Configure SSH command and unsafe mode override;
- extra `-F`, unsafe duplicate known-hosts option, extra positional SSH argv;
- wrong remote command with expected text only in a comment;
- cleanup echo-only, extra path, substitution, redirect, and extra field;
- duplicate cleanup key;
- blank/comment inside active SSH continuation.

The final independent matrix produced no false-green after the last correction.

## Diagnostic canary proof

Synthetic `B5_SECRET_CANARY` values were inserted into rejected structural fields and cleanup argv on temporary copies.

Observed diagnostics:

```text
E_JOB_FIELDS: job.extra.fields
E_CLEANUP_ARGV: cleanup.argv
```

The canary and rejected argv did not appear in stderr. No real secret was read or printed.

## Accepted hashes

```text
86e90ec261ce29a0fd8474189346017ee028b4bca6cd6b3d3c9600e21c38d631  .github/workflows/source-readiness.yml
e7cb62b5fb38664200bf737247f6e4dcd8b1258af53b0a4e08eafdd871368374  .github/workflows/deploy-production.yml
e78b00b6beccd366dcd9af1f62cebffa51899fe54eec72fff1c455317ccfcb7a  scripts/tests/lib/prod_workflow_validator.py
d2dbf73f544d01480673ed9f23656f3e6a4d7beaf61b8201c0daf7b196c13d68  scripts/tests/lib/swap_workflow_steps.py
fb5e272783f49f00ab40a72eb263290bbd55f6a350c652addf7a15973c2e008c  scripts/tests/test-prod-source-readiness-workflow.sh
```

Line counts at acceptance:

```text
691  prod_workflow_validator.py
 96  swap_workflow_steps.py
853  test-prod-source-readiness-workflow.sh
```

## Safety confirmation

- no production runtime/service was started or changed;
- no network, SSH, GitHub API, or Actions run was used;
- no real secret value was read or printed;
- no commit or push was performed;
- canonical application runtime was not changed in this phase.

## Next phase

Proceed to `76_TZ_R13_PHASE_B6_DEPLOY_SOURCE_LOADER_AND_FINGERPRINT.md`: harden the source loader and infrastructure fingerprint used by the actual production deploy script. Production launch remains manual-only and requires a later explicit user command.
