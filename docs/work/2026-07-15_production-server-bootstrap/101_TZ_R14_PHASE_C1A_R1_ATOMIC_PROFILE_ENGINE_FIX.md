# R14 Phase C1A-R1 — exact remediation for the environment profile engine

## Read first

- `99_TZ_R14_PHASE_C1A_ENV_PROFILE_ENGINE.md` — original contract;
- `100_REVIEW_R14_PHASE_C1A_REJECTED_FALSE_ATOMICITY.md` — independent reject
  evidence.

Fix only C1A. Do not start consumer cut-over (C1B), canonical DB identity (C2),
production rehearsal, network, SSH, Docker, database, systemd mutation,
commit or push.

## 1. Central exact CLI parser

Replace all hand-written pair loops in `prod-env-tool.py` with one strict parser
used by every subcommand.

For each operation require the exact option set exactly once:

```text
validate:   --source PATH --profile PROFILE --domain DOMAIN
render-set: --source PATH --output-dir PATH --domain DOMAIN
verify-set: --source PATH --output-dir PATH --domain DOMAIN
emit-nul:   --source PATH --profile PROFILE --domain DOMAIN
run:        --source PATH --profile PROFILE --domain DOMAIN -- COMMAND [ARG...]
digest:     --source PATH --domain DOMAIN
```

Order may be canonical-only or order-independent, but document and test the
choice. Unknown, duplicate, missing, odd, repeated `--`, empty value and extra
options return rc 2 before source/filesystem work. Never echo the rejected
argument or its value.

For `run`, keep command execution shell-free. Allow bare command names resolved
through the fixed PATH. If absolute binaries are needed later, introduce an
explicit code allowlist; C1A may reject all paths containing `/`.

## 2. Required/allowed key reconciliation

Keep the profile registry from `99_TZ`, and add these current API keys:

```text
CONTRACT_VERSION
SOLARSAGE_V2_FRONTEND_ENABLED
SOLARSAGE_AUDIT_ARTIFACTS_ENABLED
```

The first is allowed optional. The two rollout flags are allowed API keys and
must be exact `true|false` when present.

Require these keys to be explicitly present and non-empty in every production
source; do not provide parser defaults:

```text
APP_ENV APP_DOMAIN DEV_MODE SESSION_COOKIE_SECURE CORS_ALLOWED_ORIGINS
POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB DATABASE_URL
TELEGRAM_BOT_TOKEN BOT_USERNAME GRACE_USER_SALT LLM_PROVIDER
SOLARSAGE_EPHEMERIS_PATH OFFSITE_BACKUP_ENABLED
SOLARSAGE_V2_ENABLED SOLARSAGE_V2_DUAL_RUN
SOLARSAGE_V2_FRONTEND_ENABLED SOLARSAGE_AUDIT_ARTIFACTS_ENABLED
```

Exact fixed values:

```text
APP_ENV=production
APP_DOMAIN=astro.vasiliy-ivanov.ru
DEV_MODE=false
SESSION_COOKIE_SECURE=true
BOT_USERNAME=AstroGrace_Bot
OFFSITE_BACKUP_ENABLED=true|false
SOLARSAGE_* boolean flags=true|false
```

`CORS_ALLOWED_ORIGINS` must be non-empty here; full origin policy remains the
API runtime preflight. Provider rules remain exact mutual exclusion. Unknown
keys still fail.

Add a static registry reconciliation test that extracts aliases from
`apps/api/app/core/config.py` and requires every production-relevant alias to be
either in the API registry or in one documented deny/default-only set. This
prevents future feature flags from silently diverging from the deploy contract.

## 3. Safe source and directory opening

The Python tool must not `stat(path)` and later reopen the same pathname.

- Open source with `os.open(..., O_RDONLY|O_CLOEXEC|O_NOFOLLOW)`.
- `fstat` the descriptor: regular file, link count exactly 1.
- Decode/read from that descriptor only.
- Reject symlink-to-regular, hardlink, FIFO, directory and replacement races.
- Open output directory with `O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW`; operate by
  `dir_fd` and relative canonical filenames where Python supports it.
- `verify-set` opens each profile with `O_RDONLY|O_CLOEXEC|O_NOFOLLOW`, then
  fstats regular/link-count 1 before reading.

The production shell wrapper independently verifies before mutation:

```text
/etc/solarsage/env      real non-symlink directory root:astro 0750
source.env              real non-symlink regular root:astro 0640 nlink=1
existing profile        absent OR real regular root:astro 0640 nlink=1
```

`--check` is allowed only when real uid is 0 or the canonical `astro` uid.
Unknown users fail before profile reads. The harness may mock identity only in
an exact sandbox copy and must assert every mock argv.

## 4. Reversible canonical EnvironmentFile serializer

Source values are inert data. Reject NUL, CR, LF, BOM, ASCII controls,
backticks, `${`, `$(` and heredoc markers. Do not reject an ordinary backslash,
quote, `#`, `%`, `=`, URL punctuation or plain `>`.

Emit every value in canonical systemd double-quoted form:

```text
KEY="ENCODED_VALUE"
```

Within `ENCODED_VALUE`, escape at least `\`, `"`, `` ` `` and `$` according to
the local `systemd.exec(5)` EnvironmentFile rules. Even though source policy
rejects backticks/substitutions, the serializer itself must remain total for
its documented input domain.

Requirements:

- exactly one assignment per line and final LF;
- stable sorted key order;
- verifier accepts only this canonical form, not arbitrary raw assignments;
- independent reference decoder in the shell harness checks byte-exact values;
- static `systemd-analyze verify` uses a disposable unit only; never install,
  start or reload it;
- cases: empty optional value, interior spaces, value beginning with quote,
  both quote kinds, backslash, `#`, `%`, `=`, Unicode and URL punctuation;
- mutated/truncated/unclosed/duplicate/extra profile lines fail.

## 5. Real all-profile transaction

The live profile set must be all-old or all-new after every returned outcome.

Before the first live rename:

1. Validate the canonical directory/source/existing destinations physically.
2. Render all new profiles into a private same-filesystem generation directory.
3. Set and verify exact metadata and contents.
4. Create a private same-filesystem rollback snapshot describing for each
   profile whether it was absent or containing exact old bytes and metadata.
5. Verify the complete rollback snapshot before mutation.

Commit profiles in canonical order. After every file write/rename, treat any
failure as transaction failure. Directory/file fsync errors are fatal; remove
all `|| true` from durability steps.

On command failure or HUP/INT/TERM after mutation begins:

- restore every pre-existing profile byte- and metadata-exact from snapshot;
- remove only profiles recorded as previously absent;
- fsync restored files and directory;
- re-verify all-old state before returning original failure/signal rc;
- if rollback itself fails, preserve the root-only snapshot and report only its
  safe canonical path plus symbolic codes; never delete it automatically.

Before mutation, signals only clean the generation directory. Exact signal
codes remain HUP=129, INT=130, TERM=143. Do not use the current no-op rollback
loop.

First apply (all profiles absent), repeat apply, and partial existing-set states
must all have explicit policy and tests. Prefer rejecting a partially existing
pre-state rather than guessing; an all-absent first apply and all-present update
are the canonical states.

## 6. `run` profile correctness

Build a fresh environment from `FIXED_ENV_BASE` plus exact profile keys.

- For migration, inject command-owned `PGSSLMODE=disable` exactly as render does.
- Parent `BASH_ENV`, `PATH`, `PYTHONPATH`, `NODE_OPTIONS`, `PGPASSWORD`,
  `HTTP_PROXY` and another random canary must not survive.
- Child success and failure must preserve the child exit status; exec failure is
  the stable tool rc.
- No source value in argv, stdout or stderr produced by the tool itself.

## 7. Safe diagnostics

All errors use centralized symbolic identifiers. Allowed dynamic fields are
profile name, source line number, canonical path and key name. Never include
source values, provider values, URL, token, password, value length, repr or raw
exception text.

Add an all-error-path synthetic secret canary scan. Specifically prove unknown
`LLM_PROVIDER` does not echo its value.

## 8. Replace the false-green harness

The harness must execute the actual engine paths. At minimum add these sections:

1. exact CLI mutations for every subcommand;
2. explicit required-key deletion matrix;
3. source valid-target symlink and hardlink rejection;
4. output directory symlink and profile symlink/hardlink rejection;
5. directory/source/profile owner and mode matrices;
6. all profile membership and current API alias reconciliation;
7. serializer special-character round trip and static systemd fixture;
8. `run` fixed env, migration PGSSLMODE, child rc and exec failure;
9. sandbox-copy `prod-env-prepare.sh --apply` first install and repeat update;
10. injected failure on each commit position, chown/chmod/write/rename/fsync;
11. for every injected failure, byte+metadata proof that no mixed generation is
    visible after return;
12. HUP/INT/TERM before and during commit, exact rc, rollback and no survivors;
13. `--check` before/after filesystem snapshot proving read-only behavior;
14. stdout/stderr/temp/snapshot secret-canary scan;
15. stale temp/process scan.

Add a reproducible mutation harness (same file or
`scripts/tests/test-prod-env-profiles-mutations.sh`) that copies the canonical
implementation, verifies each mutation applied exactly once, and becomes red
for at least:

- removing one required-key check;
- following source symlinks;
- accepting unknown CLI option;
- removing migration PGSSLMODE;
- weakening serializer escaping;
- removing live rollback;
- swallowing fsync failure;
- leaking provider value.

Do not claim manual adversarial mutations that are absent from executable
evidence.

## Acceptance

Run unfiltered from fresh shells:

```bash
bash -n scripts/lib/prod-env-loader.sh \
  scripts/prod-env-prepare.sh \
  scripts/tests/test-prod-env-loader.sh \
  scripts/tests/test-prod-env-profiles.sh \
  scripts/tests/test-prod-env-profiles-mutations.sh

python3.12 -I -S -c 'compile(open("scripts/lib/prod-env-tool.py", "rb").read(), "scripts/lib/prod-env-tool.py", "exec")'

scripts/tests/test-prod-env-loader.sh
scripts/tests/test-prod-env-profiles.sh
scripts/tests/test-prod-env-profiles.sh
scripts/tests/test-prod-env-profiles-mutations.sh
scripts/tests/test-prod-deploy-source-loader.sh
scripts/tests/test-prod-host-offsite-routing.sh
scripts/prod-infra-fingerprint.sh
git diff --check
```

Handoff must include exact rc/stdout/stderr byte counts, final lines, stale path
count and mutation IDs. Stop after C1A-R1; no C1B/C2/commit/push.
