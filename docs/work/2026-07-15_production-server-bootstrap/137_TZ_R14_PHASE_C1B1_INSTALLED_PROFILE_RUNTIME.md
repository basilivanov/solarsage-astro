# R14 Phase C1B1 — trusted runtime for installed env profiles

## Status and dependency

C1A is accepted independently in
`136_REVIEW_R14_PHASE_C1A_R7K_ACCEPTED_INDEPENDENT.md`.

This task is the first, deliberately bounded part of C1B. It adds the runtime
primitive that later consumer cut-over will use. It does **not** yet change API,
sidecar, database, backup, restore, offsite, deploy, systemd or Docker consumers.
Those changes are C1B2 after architect acceptance of this runtime.

Read completely before editing:

- `AGENTS.md`;
- `70_TZ_ENV_PROFILES_AND_SECRET_BOUNDARY.md`;
- `99_TZ_R14_PHASE_C1A_ENV_PROFILE_ENGINE.md`;
- `105_TZ_R14_PHASE_C1A_R3_IMMUTABLE_ENV_GENERATIONS.md`;
- `135_TZ_R14_PHASE_C1A_R7K_HONEST_ROOT_ORACLES_AND_MUTATIONS.md`;
- `136_REVIEW_R14_PHASE_C1A_R7K_ACCEPTED_INDEPENDENT.md`;
- current `scripts/lib/prod-env-tool.py` and all C1A env harnesses.

Do not simplify or reopen accepted C1A transaction behavior. Reuse its
dir-fd/current/generation/lock validators instead of writing a second weaker
implementation.

## Mandatory working protocol

- Work directly in the current interactive coding session.
- **Do not create or use subagents, Task, explorer, delegation or parallel
  agents.** All inspection, implementation and tests are done by this coder.
- Do not commit or push.
- Do not deploy or apply anything to production.
- Do not use SSH, network, GitHub API, Docker daemon, database, systemd
  start/restart/reload, Nginx, Certbot, Restic repository or real Telegram API.
- Do not read `.env`, `.env.production`, `/etc/solarsage/env/source.env`, real
  profile values, tokens, passwords, private keys or production credentials.
- All executable tests use synthetic values in private `/tmp` sandboxes.
- Preserve the dirty worktree and unrelated user changes.
- If a command appears stuck, stop it, inspect the exact cause and continue;
  do not sit indefinitely in `grep`, `rg`, a test loop or a child process.
- New/substantially changed code must retain the GRACE module/function/block
  contracts required by `AGENTS.md`.

## Why C1B1 exists

C1A can atomically install one immutable profile generation:

```text
/etc/solarsage/env/
  source.env
  generations/gen-<32hex>/
    api.env
    sidecar.env
    db.env
    backup.env
    migration.env
    frontend-build.env
    deploy-control.env
  current -> generations/gen-<32hex>
  .profile.lock
```

The existing `prod-env-tool.py run` still reads `source.env`, while production
consumers must consume only their installed profile. A caller must also be able
to launch install/build commands in a completely clean environment with no
profile secrets. C1B1 supplies these two primitives before any consumer is
switched.

## Exact scope

Create:

1. `scripts/prod-env-run.sh`
2. `scripts/tests/test-prod-env-runtime.sh`
3. `scripts/tests/test-prod-env-runtime-mutations.sh`
4. `scripts/tests/test-prod-env-runtime-root.sh`

Modify only as required:

5. `scripts/lib/prod-env-tool.py`
6. `scripts/prod-infra-fingerprint.sh`
7. repository inventory/syntax lists in `scripts/prod-host-prepare.sh`
8. an existing C1A harness only if a real regression from the new public CLI
   requires an additive assertion; do not remove or weaken old cases.

Do **not** modify in C1B1:

- `scripts/lib/prod-env-loader.sh`;
- `scripts/prod-deploy.sh`;
- backup/restore/offsite scripts;
- systemd units;
- Docker Compose;
- `scripts/check_prod_guard.sh`;
- Telegram initData generator;
- production runbook;
- application/frontend/backend code.

The deprecated loader remains temporarily because the consumers still use it.
It will be removed only in C1B2 after all callers are cut over.

## Public runtime CLI in `prod-env-tool.py`

Add exactly two operations:

```text
/usr/bin/python3.12 -I -S scripts/lib/prod-env-tool.py \
  run-installed --env-dir PATH --profile PROFILE -- COMMAND [ARG...]

/usr/bin/python3.12 -I -S scripts/lib/prod-env-tool.py \
  run-clean -- COMMAND [ARG...]
```

No aliases, implicit default profile, source path, domain argument, `--root`,
`--set`, arbitrary extra environment keys or environment-variable path
overrides.

### CLI failure ordering

For both operations, validate the complete CLI before filesystem access:

- missing `--`, missing command, missing/duplicate/unknown option, empty
  `--env-dir`, empty/unknown profile or extra pre-command argument: rc `2`;
- `run-clean` accepts no options before `--`;
- profile is exactly one of the seven installed profiles:
  `api`, `sidecar`, `db`, `backup`, `migration`, `frontend-build`,
  `deploy-control`;
- `all` and `clean` are not accepted by `run-installed`;
- command argv is passed byte-for-byte as an argv array; never concatenate or
  reconstruct a shell command;
- a bare command name is resolved only through the fixed child `PATH`;
- an absolute command path is allowed because the caller already chooses the
  executable and no privilege change occurs;
- a relative command containing `/`, `.`/`..` traversal or an empty argv[0] is
  rejected with the safe run error;
- do not execute through `sh -c`, `bash -c`, `eval`, `source`, `shell=True` or
  any command string.

Keep current centralized symbolic exit codes. If a new code is genuinely
needed, document it once in code and in the handoff. Child exit status and
signal behavior are naturally preserved by `exec`; do not wrap the child and
accidentally convert its status.

## `run-installed` filesystem and locking contract

Implement one reusable helper in `prod-env-tool.py`; do not duplicate current
generation parsing in the shell wrapper.

The helper must:

1. Open `env-dir` with the accepted C1A
   `O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC` logic and retain its fd.
2. Open `generations` by the env-dir fd, not by joining/reopening the original
   path.
3. Open `.profile.lock` by env-dir fd with `O_NOFOLLOW|O_CLOEXEC`, without
   `O_CREAT`, without truncation and with the accepted regular/nlink/owner/mode
   validation.
4. Acquire a bounded non-blocking/shared flock. Contention fails closed; it
   must not wait indefinitely and must not create or mutate any file.
5. While the shared lock is held:
   - run the accepted housekeeping validation;
   - validate `generations` owner/mode;
   - validate `current` is the canonical relative symlink owned like env-dir;
   - resolve the current generation **once**;
   - validate generation directory metadata and exact seven-file inventory;
   - open the requested profile by generation-dir fd with `O_NOFOLLOW`;
   - require regular file, nlink 1, expected uid/gid, mode `0640`, bounded size
     and read-until-EOF;
   - parse it with the one canonical EnvironmentFile deserializer.
6. Build the complete child environment in memory from that parsed profile.
7. Close profile/generation/env/lock descriptors and release the lock before
   `exec`. The immutable generation remains valid even if `current` changes
   afterward.
8. Never reopen `current/<profile>.env` by pathname after resolving the
   generation.

The returned non-secret generation identity is the exact `gen-<32hex>` basename
already proven by the current target. Never derive filenames or normal output
from profile values.

### No production-owner hardcoding in the low-level operation

Like accepted C1A, the Python operation is sandbox-testable and derives
expected uid/gid from the opened env directory. Exact `root:astro` production
identity is enforced by the production wrapper below and by the root oracle.
Do not add a production-only test bypass or environment override to Python.

## Installed profile content validation

Do not trust arbitrary EnvironmentFile bytes merely because the file is under
`current`. After canonical deserialization:

- reject a key outside the exact requested profile;
- reject missing required keys for that profile;
- reject any source-forbidden/process-control name;
- reject duplicates, unsorted keys, blank lines, malformed quoting, dangling
  or unknown escapes, no-final-LF, CR/NUL/control characters and oversized
  profile using the accepted parser;
- reject command-owned keys in a stored profile except exact generated
  `PGSSLMODE=disable` in `migration.env`;
- enforce exact production values that exist inside the requested profile
  (`APP_ENV`, `APP_DOMAIN`, `DEV_MODE`, `SESSION_COOKIE_SECURE`, provider
  selection, boolean flags, `BOT_USERNAME`, path/value constraints, and
  conditional offsite requirements where applicable);
- do not implement C2 canonical PostgreSQL URL identity yet. Retain current
  C1A non-empty/non-SQLite compatibility only and explicitly report C2 as
  remaining work.

Use centralized per-profile required sets. Minimum required installed keys:

```text
api:
  APP_ENV APP_DOMAIN DATABASE_URL TELEGRAM_BOT_TOKEN DEV_MODE
  SESSION_COOKIE_SECURE CORS_ALLOWED_ORIGINS GRACE_USER_SALT LLM_PROVIDER
  SOLARSAGE_V2_ENABLED SOLARSAGE_V2_DUAL_RUN
  SOLARSAGE_V2_FRONTEND_ENABLED SOLARSAGE_AUDIT_ARTIFACTS_ENABLED
  and exactly one provider key selected by LLM_PROVIDER

sidecar:
  SOLARSAGE_EPHEMERIS_PATH

db:
  POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB

backup:
  POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB OFFSITE_BACKUP_ENABLED
  plus the existing conditional Restic fields when enabled

migration:
  DATABASE_URL PGSSLMODE, with PGSSLMODE exactly disable

frontend-build:
  no secret key and no unknown NEXT_PUBLIC_*/VITE_* key; registered public
  keys remain optional

deploy-control:
  BOT_USERNAME SOLARSAGE_EPHEMERIS_PATH POSTGRES_USER POSTGRES_DB
```

Do not require optional sidecar version/SHA or optional frontend observability
keys merely to make tests convenient.

When validating only one installed profile, do not pretend to prove cross-file
equality that is not observable in that profile. Physical exact-generation
validation plus C1A root-owned immutable generation is the coherence boundary.

## Exact child environment

Both new operations start from an empty dict. Inherit nothing from the caller.

Fixed base:

```text
HOME=/home/astro
PATH=/home/astro/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
LANG=C.UTF-8
LC_ALL=C.UTF-8
GIT_TERMINAL_PROMPT=0
```

Then:

- `run-installed`: add only the requested profile's parsed keys;
- add command-owned marker
  `SOLARSAGE_ENV_PROFILE=<requested-profile>`;
- add command-owned marker
  `SOLARSAGE_ENV_GENERATION=gen-<32hex>`;
- `frontend-build` additionally gets command-owned exact
  `NODE_ENV=production` and `APP_ENV=production`; a stored profile/source can
  never override them;
- `migration` retains only stored generated `PGSSLMODE=disable` plus its
  migration profile;
- add `TZ=UTC` only if an executable test proves an existing timestamp contract
  requires it. Do not add it speculatively.

`run-clean` receives only the fixed base plus:

```text
SOLARSAGE_ENV_PROFILE=clean
SOLARSAGE_ENV_GENERATION=none
```

It must not open `/etc/solarsage`, any source/profile file or repository env
file.

Mandatory inherited canaries absent in both children include:

```text
BASH_ENV ENV PATH-from-parent NODE_OPTIONS LD_PRELOAD PYTHONPATH
GIT_DIR GIT_CONFIG_GLOBAL SSH_ASKPASS HTTP_PROXY HTTPS_PROXY ALL_PROXY
NO_PROXY PGHOST PGPASSWORD RESTIC_REPOSITORY RESTIC_PASSWORD_FILE
TELEGRAM_BOT_TOKEN OPENROUTER_API_KEY ANTHROPIC_API_KEY
AWS_ACCESS_KEY_ID VITE_SECRET XDG_CONFIG_HOME
```

For canaries which are legitimate keys of the selected profile, test leakage
using a different profile or `run-clean`; do not assert that API lacks its own
Telegram/provider secret.

No value, argv containing a secret, parsed dictionary, exception repr, profile
bytes or secret length may appear in tool diagnostics.

## Production wrapper `scripts/prod-env-run.sh`

Public CLI:

```text
scripts/prod-env-run.sh PROFILE -- COMMAND [ARG...]
```

Where profile is one of the seven names above or exact `clean`.

Requirements:

- `set -euo pipefail`, `umask 027`;
- CLI validated before privilege/filesystem checks;
- only users `root` and `astro` accepted; another user fails safely;
- canonical literal env dir is exactly `/etc/solarsage/env`; no env override,
  `--env-dir`, `--root`, alternate source or fallback;
- for an installed profile, prevalidate canonical env dir is a real non-symlink
  directory `root:astro 0750`; do not validate/read `source.env` and never
  mention it in the child;
- verify the tool is the exact real non-symlink regular repository file at the
  wrapper-relative `scripts/lib/prod-env-tool.py` before execution;
- `clean` must not inspect canonical env paths at all;
- use `exec /usr/bin/python3.12 -I -S ...`; do not source any helper or profile;
- preserve child argv boundaries exactly;
- no success banner before exec and no secret-bearing diagnostics.

The wrapper is preparatory in C1B1. Do not install it to `/usr/local` and do not
wire any consumer to it yet.

## Infrastructure inventory

Add `scripts/prod-env-run.sh` to:

- the canonical ordered fingerprint list in
  `scripts/prod-infra-fingerprint.sh`;
- `prod-host-prepare.sh` repository inventory;
- `prod-host-prepare.sh` Bash syntax list.

Do not make host-prepare execute it or change production host behavior in this
phase. Preserve deterministic ordering and update relevant tests only if they
assert the exact inventory/fingerprint inputs.

## Harness 1 — `test-prod-env-runtime.sh`

Self-contained, synthetic, private sandbox, no production path access. Use the
real C1A `install-set` to produce a generation; do not handcraft the canonical
green generation. Run the actual tool/wrapper copies, not mocked parser logic.

At minimum cover:

### CLI

1. missing/unknown/duplicate options;
2. missing/extra `--` and command;
3. `all`, `clean`, unknown and empty installed profile rejection;
4. `run-clean` rejects every option;
5. bare command success, absolute command success, relative slash/traversal
   rejection;
6. command-not-found returns the stable run code;
7. a child `exit 37` returns 37; HUP/INT/TERM after exec produce the natural
   child signal status and no surviving process.

### Exact environment boundary

8. for each seven profiles, child sees only fixed base + exact allowed profile
   key names + two command-owned markers;
9. frontend child sees exact command-owned `NODE_ENV=production` and
   `APP_ENV=production`, and profile data cannot override either;
10. migration sees exact `PGSSLMODE=disable`;
11. clean child sees no profile key and does not stat/open the env sandbox;
12. every inherited canary is absent in an unrelated-profile/clean child;
13. caller environment remains byte-exact after success, child failure and
    exec failure.

Do not print secret values while proving this. A child helper may compare
expected values internally and print only a fixed safe sentinel or sorted key
names. Store secret canaries only inside the private sandbox and ensure they do
not occur in captured stdout/stderr/pathnames.

### Filesystem/current/profile safety

14. current absent, malformed, absolute, traversal, external, wrong type,
    wrong owner and wrong target inventory;
15. missing/invalid lock, lock symlink/FIFO/wrong owner/mode/nlink and bounded
    contention;
16. generations/profile symlink, hardlink, FIFO, wrong owner/mode, too large,
    truncated read and extra file;
17. requested profile missing, extra key, cross-profile key, missing required
    key, duplicate, unsorted, blank interior line, malformed escape, CR/NUL,
    missing final LF;
18. API provider matrix, exact booleans/domain/bot constraints, backup disabled
    and enabled conditional fields, migration command-owned value;
19. current switches after the profile is read: the child receives one exact
    old or new generation marker and one matching non-secret public value,
    never a mixed pair;
20. concurrent install holds exclusive lock: run-installed fails bounded and
    performs no child exec; after release retry succeeds;
21. no temp file, profile mutation, lock mutation, stdout preamble or orphan
    process.

Instrument open/stat/exec behavior in a copied tool only where necessary, with
exact mutation-count assertions. Do not add production test hooks.

## Harness 2 — `test-prod-env-runtime-root.sh`

This is a real `root:astro` identity oracle under a private `/tmp` sandbox.

- It must require non-interactive `sudo -n`; absence is a hard nonzero result,
  never SKIP/green.
- Root creates env dir/source, installs the generation with the real tool and
  exact root:astro metadata.
- Execute the runtime as user `astro` via `sudo -n -u astro`.
- Prove `api`, `backup`, `migration`, `frontend-build`, and `clean` children run
  with the exact boundary/markers without printing secrets.
- Prove current symlink `root:astro`, generation/root profiles `root:astro`,
  wrapper production-owner oracle accepts root:astro and rejects root:root or
  astro:astro env-dir mutations in a sandboxed wrapper copy.
- Prove wrong current/profile ownership fails before child marker creation.
- Restore/remove every sandbox object; final stale scan zero.

The root harness must never substitute or address the real
`/etc/solarsage/env`. Sandbox the production wrapper by copying it and replacing
the canonical literal exactly once; fail if replacement count is not exactly
one.

## Harness 3 — `test-prod-env-runtime-mutations.sh`

Run canonical runtime and root baselines first. Then apply each mutation to an
isolated copied tool/wrapper and require the same canonical harness/oracle to
turn red.

At minimum exact-one mutations:

1. inherit `os.environ` instead of starting empty;
2. skip requested-profile key membership;
3. skip one required-key check;
4. reopen `current/<profile>.env` by pathname after resolving generation;
5. remove shared lock acquisition;
6. accept malformed/noncanonical current target;
7. accept profile symlink or wrong owner/mode;
8. omit/misreport `SOLARSAGE_ENV_GENERATION`;
9. omit frontend command-owned `NODE_ENV` or permit stored override;
10. let `run-clean` read an installed profile/inherit a secret;
11. allow relative `../command`;
12. weaken production wrapper `root:astro 0750` check.

For every mutation:

- selector count exactly one;
- copied Python compiles / copied Bash passes `bash -n` before execution;
- prove the mutated copy was the file actually invoked;
- nonzero must be caused by the named oracle, not syntax damage, missing fixture
  or an unrelated baseline failure;
- no `|| true`, SKIP, expected-failure masking or aggregate-only green count.

## Required regression commands

Run directly from repository root, capture real rc (never through `tail` or a
pipeline that masks status):

```bash
bash -n \
  scripts/prod-env-run.sh \
  scripts/prod-env-prepare.sh \
  scripts/lib/prod-env-loader.sh \
  scripts/tests/test-prod-env-loader.sh \
  scripts/tests/test-prod-env-profiles.sh \
  scripts/tests/test-prod-env-install-transaction.sh \
  scripts/tests/test-prod-env-profiles-mutations.sh \
  scripts/tests/test-prod-env-root-identity.sh \
  scripts/tests/test-prod-env-runtime.sh \
  scripts/tests/test-prod-env-runtime-root.sh \
  scripts/tests/test-prod-env-runtime-mutations.sh

python3.12 -I -S -c \
  'compile(open("scripts/lib/prod-env-tool.py", "rb").read(), "scripts/lib/prod-env-tool.py", "exec")'

bash scripts/tests/test-prod-env-runtime.sh
bash scripts/tests/test-prod-env-runtime.sh
sudo -n bash scripts/tests/test-prod-env-runtime-root.sh
bash scripts/tests/test-prod-env-runtime-mutations.sh

bash scripts/tests/test-prod-env-loader.sh
bash scripts/tests/test-prod-env-profiles.sh
bash scripts/tests/test-prod-env-install-transaction.sh
bash scripts/tests/test-prod-env-profiles-mutations.sh
sudo -n env TOOL_OVERRIDE=/opt/solarsage-astro/scripts/lib/prod-env-tool.py \
  bash scripts/tests/test-prod-env-root-identity.sh
bash scripts/tests/test-prod-deploy-source-loader.sh
bash scripts/tests/test-prod-host-offsite-routing.sh

bash scripts/prod-infra-fingerprint.sh
git diff --check
```

Do not run full app tests unless a file outside this exact scope is changed and
requires them. Do not call production `prod-env-run.sh` against the canonical
path during implementation; only sandbox copies are executable proof.

## Acceptance is not a case count

The handoff must include:

- exact files changed;
- exact new CLI and exit-code table;
- explanation of one-time generation resolution and fd/lock lifetime;
- exact environment key matrix for all seven profiles and clean;
- commands with true rc, stdout/stderr byte counts and unfiltered final line;
- runtime twice, root oracle and mutation results by mutation ID;
- current/generation marker evidence using only non-secret values;
- child/temp/fd/stale artifact scan;
- secret canary scan locations and result;
- fingerprint output;
- explicit remaining C1B2 work: systemd/Compose/scripts/deploy/guard/runbook
  cut-over and deprecated loader removal;
- explicit remaining C2 canonical database identity work.

Stop after the handoff. Do not begin C1B2/C2, do not commit and do not push.
