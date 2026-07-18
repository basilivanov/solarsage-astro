# R13 Phase B6 R4 — in-progress architect review: deploy harness is not complete

## Verdict

Phase B6 remains **in progress**. Do not write a handoff and do not start the two
acceptance runs merely because the current implemented cases are green.

The deliverable is the automated production deploy harness around
`scripts/prod-deploy.sh`. No production deploy, SSH, network, database, systemd,
commit or push is allowed in this phase.

This document is a delta over `90_REVIEW...` and `91_REVIEW...`. Every item below
must be closed with executable proof.

## 1. Foundation and common guards

### 1.1 Structural env-loader boundary is still false-green

The current baseline check is a direct grep for an executable line containing
both `source`/`.` and `.env.production`. It does not catch an indirect bypass:

```bash
ENV_PATH=.env.production
source "$ENV_PATH"
```

Implement one common structural validator and run it against:

- the sandbox baseline wrapper;
- a direct-source mutation copy;
- a dot-source mutation copy;
- an indirect variable + source mutation copy;
- an eval/set-a loading mutation copy.

The common validator must return non-zero for each mutation for a symbolic
loader-boundary reason. It must not print the matched source line or raw value.
Comments containing the words must not trigger the validator.

### 1.2 Common post-substitution validator

`MUT09` must use the same post-substitution validator used by the baseline. The
validator must check all substituted production paths and their exact expected
counts, not only `LOCKFILE`:

- sandbox app root;
- sandbox lock file;
- sandbox access helper;
- sandbox env loader;
- sandbox fingerprint script and host fingerprint file;
- sandbox ephemeris fallback;
- absence of every canonical production path.

The mutation must first pass the validator, then reintroduce exactly one
canonical lock path, then fail the validator specifically because the sandbox
lock path count becomes zero and canonical lock path count becomes one.

### 1.3 Exact safe audit records

Loader records still use `echo "$*"`. Replace them with exact argc checking and
byte-stable `printf` records. The normal loader mock must require exactly two
arguments:

1. `.env.production`;
2. `astro.vasiliy-ivanov.ru`.

No extra arguments are accepted. Do not put env contents or secrets in audit.

The `stat` mock must reject unknown argv/format/path without delegating to the
real command. Its comments and implementation must agree on argc.

### 1.4 Per-case common assertions

After every case, including expected failures, the common runner must verify:

- forbidden log empty;
- no unexpected safe-rejection marker;
- no controlled-stop for cases expected to fail before it;
- no wrapper temp files, including repository fingerprint temp;
- no origin, env-secret or either fingerprint canary in stdout/stderr/audit;
- invalid CLI rc=2 cases have a byte-empty audit;
- diagnostics remain symbolic and do not dump raw stdout/stderr/audit.

Do not special-case these only after selected cases when a common assertion can
enforce them.

## 2. Loader/runtime matrix still missing executable cases

Add separate manifest IDs and actual negative executions for:

- wrong env-path argv passed by a deploy mutation;
- wrong domain argv passed by a deploy mutation;
- extra loader argument;
- loader returns zero but exports no ephemeris path;
- loader exports a guaranteed nonexistent path;
- loader exports a regular file;
- valid exact argv/export reaches controlled-stop.

Current `ENV22 loader valid` does not test a wrong domain. Creating a mock that
would reject a wrong domain and then calling it with the canonical domain is
only a positive case.

For loader failure/removal, prove the exact stage ordering: fingerprint reached,
loader absent or rejected as appropriate, controlled-stop absent.

## 3. Fingerprint matrix and real leak canaries

Add the still missing host-file cases:

- unreadable regular file;
- mode `660`;
- leading-zero mode response such as `0644` (must reject; only exact `644` is
  accepted);
- exact-length lowercase/other nonhex record;
- spaces in/around the record;
- long record.

Add the still missing repository-output cases:

- empty output;
- long single line;
- command failure after writing partial output;
- valid repository record distinct from a valid host record, producing a pure
  mismatch.

Use two distinct valid lowercase 64-hex values as real host/repository canaries.
They must actually flow through the scenario. The common scanner must prove that
neither value appears in stdout, stderr or audit. Literal `FP_CANARY` without
such a value in the scenario is not evidence.

Every fingerprint failure must prove that loader and controlled-stop were not
reached and that the private fingerprint temp was deleted.

## 4. Transport/mode negative contracts

For empty, wrong, credential-like and multiline origin, assert exact stop:

- origin lookup may occur;
- access, fetch, origin/main, checkout, fingerprint, loader and controlled-stop
  must all be absent;
- set-url must be absent;
- hostile origin bytes/canaries must not appear in stdout/stderr/audit.

Add executable wrong-ref and wrong-checkout argv cases. A mutation-only mock
rejection is not a replacement for the required runtime matrix.

The checkout mock must compare against an explicit expected target SHA for the
scenario. Tying accepted checkout only to `MOCK_GIT_HEAD` can accidentally allow
the deploy script to checkout the wrong ref/value.

Retain byte-exact manifests for `--current`, no-arg and pinned modes. Any extra,
missing or reordered audit line must fail.

## 5. Mutation engine completion

- All `mutate_and_check_tailored` calls must pass a numeric `post_exp`; verify
  `MUT01` and `MUT02` explicitly.
- `MUT06`: two different valid fingerprints, remove only the exact comparison
  `if` block, pre-count 1/post-count 0, prove loader and controlled-stop reached.
- `MUT08`: baseline with invalid ephemeris fails before controlled-stop; mutation
  of only the validation reaches exactly one controlled-stop.
- `MUT09`: use the complete common post-substitution validator described above.
- `MUT10`: assert rc=0, exactly one controlled-stop, forbidden/canary scanner
  clean, and exact leftover; clean all leftovers with safe quoted iteration.
- `MUT11`: inject a raw-origin diagnostic, run the common scanner, and count PASS
  only when the scanner rejects it for the expected canary reason. Prove the
  mutation bytes changed and syntax remains valid.
- Remove duplicate comments, duplicate `leftovers=` and debug remnants.

## 6. Signal and cleanup proof

Harness cleanup must be idempotent and track the background lock-holder PID.
HUP/INT/TERM must kill/wait the holder, remove the private directory and exit
129/130/143 respectively. EXIT cleanup must not overwrite those codes.

Add an executable signal proof or an isolated self-test that confirms no
background holder and no `solarsage-deploy-source-loader-test.*` directory is
left behind.

## 7. Completion sequence

Only after all items above are implemented:

```bash
bash -n scripts/prod-deploy.sh scripts/tests/test-prod-deploy-source-loader.sh
timeout 300 bash scripts/tests/test-prod-deploy-source-loader.sh
timeout 300 bash scripts/tests/test-prod-deploy-source-loader.sh
git diff --check
```

Run both harness executions unfiltered and preserve their exact rc. Then provide
the ordered manifest, all 11 mutation results, cleanup/canary proof and changed
file list.

Do not commit or push. Do not touch production.
