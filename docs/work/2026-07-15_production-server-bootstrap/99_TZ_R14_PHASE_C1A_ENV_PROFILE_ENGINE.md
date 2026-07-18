# R14 Phase C1A — production env profile engine (implementation task)

## Current state and purpose

Phase B6 is accepted in `98_REVIEW_R13_PHASE_B6_ACCEPTED_INDEPENDENT.md`.
Do not reopen or simplify its source/origin/SHA/fingerprint contracts.

The next launch blocker is the shared production environment file. Today
`scripts/lib/prod-env-loader.sh` exports every parsed key into the caller, while
API, sidecar, database, backup and build paths can all see more configuration
than they own. This phase builds the reusable profile engine and its isolated
proof. Consumer cut-over is deliberately the next phase, after architect review
of this engine.

The normative architecture is:

- `70_TZ_ENV_PROFILES_AND_SECRET_BOUNDARY.md`;
- `73_TZ_CANONICAL_DATABASE_IDENTITY.md` (read it now for interface
  compatibility, but do **not** implement Layer B or DB consumer cut-over in
  C1A).

## Hard boundaries

- No production deploy, SSH, network, GitHub API, Docker, database, systemd,
  Nginx, Certbot, backup, restore, service restart/reload, commit or push.
- Do not read or print real `.env`, `.env.production`, tokens, private keys,
  credentials or GitHub secret values.
- All executable proof uses synthetic values under a private temporary
  directory. No test may address `/etc/solarsage`, `/opt/solarsage-astro` as a
  production target, `/home/astro/.ssh`, or any live service.
- Preserve the dirty worktree. Do not edit unrelated frontend, screenshots,
  visual baselines, `.grace/`, `artifacts/design/`, `grace.db`, `skills/`, or
  old work documents.
- New/substantially changed code keeps the GRACE contracts required by
  `AGENTS.md`.
- Do not weaken existing B3-B6 harnesses or remove cases to obtain green.

## Exact scope for C1A

Create:

1. `scripts/lib/prod-env-tool.py`
2. `scripts/prod-env-prepare.sh`
3. `scripts/tests/test-prod-env-profiles.sh`

Modify only when required by this scope:

4. `scripts/lib/prod-env-loader.sh` — turn it into a thin sourceable facade for
   the new engine while keeping `prod_env_load` temporarily available for the
   not-yet-migrated callers. The compatibility function must use the same
   parser/registry and must reject unknown/process-control keys; mark it
   explicitly deprecated in the module contract. Do not maintain a second
   parser.
5. `scripts/prod-infra-fingerprint.sh` and the repository inventory in
   `scripts/prod-host-prepare.sh` — include the two new production scripts and
   the profile contract where the current fingerprint/inventory architecture
   requires it. Do not make host-prepare call `--apply` yet.
6. Existing env-loader tests only as necessary to route them through the new
   engine. Preserve their old security assertions and add, never replace,
   coverage.

Do **not** yet modify systemd unit `EnvironmentFile` paths, Docker Compose,
backup/restore/offsite consumers or the main build/restart sequence in
`prod-deploy.sh`. Those changes form C1B after this engine is accepted.

## Canonical production paths

The shell entrypoint owns these literal defaults; they must not be overridable
by environment variables:

```text
/etc/solarsage/env/source.env
/etc/solarsage/env/api.env
/etc/solarsage/env/sidecar.env
/etc/solarsage/env/db.env
/etc/solarsage/env/backup.env
/etc/solarsage/env/migration.env
/etc/solarsage/env/frontend-build.env
/etc/solarsage/env/deploy-control.env
```

Canonical metadata:

- `/etc/solarsage/env`: real directory, not symlink, `root:astro 0750`;
- `source.env`: real regular non-symlink file, `root:astro 0640`;
- generated profiles: real regular non-symlink files, `root:astro 0640`;
- no profile may be hard-linked to `source.env`, another profile or an external
  file; require link count 1 for source and generated files;
- same-directory temporary files, `0600`, atomic rename, directory fsync after
  commit;
- failure before commit leaves every existing output byte- and metadata-exact;
- failure during a multi-profile apply rolls back the complete profile set;
  never expose a mixed generation.

`prod-env-prepare.sh` must not offer a production `--root`, `--source-file`,
`--output-dir` or environment-variable path override. The harness may create a
sandbox copy and replace each canonical literal path with an exact-count
assertion before execution. The Python library accepts explicit paths because
it is a lower-level tool; the production shell wrapper supplies only canonical
paths.

## Exact CLI of `scripts/prod-env-prepare.sh`

Only:

```text
scripts/prod-env-prepare.sh --apply
scripts/prod-env-prepare.sh --check
```

- no/unknown/extra/repeated args: rc `2`, before privilege or filesystem checks;
- `--apply`: root only; validates source, renders all eight profiles into a
  private transaction directory, validates rendered files independently, then
  atomically commits the entire generation with rollback on any failure;
- `--check`: read-only, allowed for root or `astro`; validates source and exact
  content/owner/group/mode/type/link-count of every generated profile; no temp
  files and no metadata changes;
- stable safe diagnostics contain only symbolic error code, profile name and
  canonical path. Never include a value, full assignment, URL, password, token,
  value length, Python repr or exception text;
- success prints one concise line per profile and a final generation digest.
  Digest is over canonical **key names, profile mapping and generated bytes**;
  do not claim it is safe to publish if it hashes secrets without a keyed
  construction. In normal output print only a contract/version digest that does
  not depend on secret values. A value-dependent digest may exist only in the
  root-readable state file and must never be logged.

## `prod-env-tool.py` public operations

Implement one parser and one registry. The shell facade may call these exact
subcommands:

```text
/usr/bin/python3.12 -I -S scripts/lib/prod-env-tool.py validate --source PATH --profile all --domain astro.vasiliy-ivanov.ru
/usr/bin/python3.12 -I -S scripts/lib/prod-env-tool.py render-set --source PATH --output-dir PATH --domain astro.vasiliy-ivanov.ru
/usr/bin/python3.12 -I -S scripts/lib/prod-env-tool.py verify-set --source PATH --output-dir PATH --domain astro.vasiliy-ivanov.ru
/usr/bin/python3.12 -I -S scripts/lib/prod-env-tool.py emit-nul --source PATH --profile PROFILE --domain astro.vasiliy-ivanov.ru
/usr/bin/python3.12 -I -S scripts/lib/prod-env-tool.py run --source PATH --profile PROFILE --domain astro.vasiliy-ivanov.ru -- COMMAND [ARG...]
```

Requirements:

- stdlib only; no repository imports and no dependency on caller `PYTHONPATH`;
- validate operation is read-only;
- `render-set` writes only inside the already-created private transaction
  directory supplied by the root shell wrapper; it never installs canonical
  paths itself;
- `verify-set` parses every emitted EnvironmentFile independently and compares
  exact key/value bytes to the expected profile; it must detect missing, extra,
  duplicate, reordered-as-duplicate, truncated and malformed output;
- `emit-nul` writes `KEY=VALUE\0` records only to stdout and errors only to
  stderr. It exists solely for the deprecated shell compatibility facade; the
  caller must never log/capture it in an audit file;
- `run` builds a fresh environment and calls `os.execvpe`; no shell, `eval`,
  command-string reconstruction or inherited arbitrary environment;
- `run` requires a non-empty command after `--`; reject NUL/empty argv and
  command names containing `/` unless the path is one of the explicitly
  caller-owned absolute binaries documented in code;
- symbolic exit codes and messages are centralized. Unexpected exceptions map
  to one safe generic code without exception content.

## Source parser contract

- UTF-8 without BOM; final LF required; CR, NUL and all ASCII controls except
  the line LF are rejected;
- blank lines and full-line comments beginning with `#` after optional spaces
  are allowed;
- assignment grammar is one physical line `KEY=VALUE`;
- key must be exact ASCII `[A-Z][A-Z0-9_]*`; no `export`, whitespace around the
  key, lowercase aliases or Unicode lookalikes;
- duplicate key is fatal;
- value is the exact text after first `=` with no trimming or expansion;
- leading/trailing whitespace in a value is rejected;
- shell substitutions, backticks, heredoc syntax and multiline values are
  rejected; values are data and never executed;
- empty values are allowed only for explicitly optional keys; all required keys
  are non-empty;
- diagnostics identify line number and symbolic code but not source line/value;
- validate the complete source and all cross-field rules before rendering any
  output.

Use the exact registry/profile membership from
`70_TZ_ENV_PROFILES_AND_SECRET_BOUNDARY.md`. Unknown keys are errors. Do not add
keys merely because they appear in an old `.env.example`; report any genuine
missing application key in the handoff for architect decision.

## Process-control denylist

Implement the exact hard-deny names/prefixes in section "Hard denylist" of
`70_TZ_ENV_PROFILES_AND_SECRET_BOUNDARY.md` before profile membership logic.
Matching for dangerous families (`LD_`, `PYTHON`, `GIT_`, `PG`, proxy names,
etc.) must be fail-closed and covered by one case per family plus the named
canaries below. An explicitly registered legitimate key wins only where the
architecture document names that exact exception; do not add wildcard
exceptions.

Mandatory canaries:

```text
BASH_ENV PATH NODE_OPTIONS LD_PRELOAD PYTHONPATH GIT_DIR
GIT_CONFIG_GLOBAL SSH_ASKPASS HTTP_PROXY HTTPS_PROXY PGHOST PGPASSWORD
VITE_SECRET AWS_ACCESS_KEY_ID
```

Each must fail before output creation and must not appear in stdout/stderr/temp
artifacts.

## Exact profiles and isolation

Use the profile lists in `70_TZ...` verbatim. Additionally prove:

- API has no `POSTGRES_*`, bot username, offsite/restic or sidecar-only keys;
- sidecar has no Telegram, DB, LLM, GitHub or backup keys;
- DB has exactly `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`;
- migration has exactly `DATABASE_URL` plus generated
  `PGSSLMODE=disable`; source `PGSSLMODE` is forbidden;
- backup has only DB and approved offsite keys;
- frontend build contains only approved `NEXT_PUBLIC_*`; any unknown
  `NEXT_PUBLIC_*`, `VITE_*`, token, DB, LLM, salt or offsite key is rejected;
- deploy-control contains only `BOT_USERNAME`,
  `SOLARSAGE_EPHEMERIS_PATH`, `POSTGRES_USER`, `POSTGRES_DB`;
- command-owned values cannot be overridden by source input.

The active LLM provider rule is exact:

- `openrouter`: `OPENROUTER_API_KEY` required and non-empty;
  `ANTHROPIC_API_KEY` absent;
- `anthropic`: `ANTHROPIC_API_KEY` required and non-empty;
  `OPENROUTER_API_KEY` absent;
- any other provider or both provider keys: fail.

## Fixed child environment for `run`

Start from an empty mapping. Include only:

```text
HOME=/home/astro
PATH=/home/astro/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
LANG=C.UTF-8
LC_ALL=C.UTF-8
GIT_TERMINAL_PROMPT=0
```

Add `TZ=UTC` only for profiles/commands whose timestamp contract requires it.
Then add that profile's exact keys. Inherited canaries from the parent must be
absent. The tool must not promise memory zeroization; it guarantees no
file/argv/stdout/stderr leakage.

## EnvironmentFile serialization

Implement one reversible serializer for systemd `EnvironmentFile` syntax.
Values may contain spaces, quotes, backslashes, `#`, `%`, `=`, non-ASCII UTF-8
and URL punctuation, but never NUL/CR/LF. Do not use shell escaping as an
unverified substitute.

Required proof:

1. independent parse of emitted files by the project's verifier;
2. a disposable `systemd-analyze verify` fixture unit referencing a synthetic
   emitted profile when `systemd-analyze` is available; this is static parsing
   only, never install/start/reload a unit;
3. byte-exact round-trip cases covering spaces, single/double quotes,
   backslash, `#`, `%`, `=`, Unicode and URL punctuation;
4. malformed/truncated serialized assignments are rejected;
5. no value is printed during proof.

If systemd syntax cannot represent an allowed source value byte-exactly, fail
with a stable code. Do not silently change it.

## Deprecated compatibility facade

`prod_env_load SOURCE DOMAIN` remains temporarily because C1A does not switch
all consumers. It must:

- delegate validation and NUL emission to `prod-env-tool.py` profile `all`;
- never execute source text;
- reject all unknown/dangerous keys through the same registry;
- collect all assignments before exporting any; a producer failure leaves
  caller environment unchanged;
- preserve signal cleanup and exact nonzero status;
- be marked deprecated and scheduled for deletion in C1B;
- retain existing owner/mode/type checks expected by current callers/harnesses.

Do not add a second Python snippet inside the shell facade.

## Required isolated harness

`scripts/tests/test-prod-env-profiles.sh` must be self-contained and must leave
no temp paths/processes. At minimum cover:

1. exact CLI and privilege ordering;
2. source/output type, symlink, hardlink, owner, group and mode rejection;
3. parser grammar, duplicate, unknown and missing keys;
4. every mandatory denylist canary;
5. exact membership/no cross-profile leakage for all eight profiles;
6. provider selection matrix;
7. frontend public-only boundary;
8. fixed child environment and inherited canary removal on success and child
   failure;
9. caller environment unchanged for deprecated loader failure;
10. atomic all-profile commit, injected render/write/fsync/rename failure and
    complete rollback with no mixed generation;
11. `--check` is byte/metadata read-only (snapshot before/after);
12. signal HUP/INT/TERM during transaction: exact 129/130/143, no partial
    profiles, no surviving holder/child/temp directory;
13. secret canary absent from stdout, stderr, filenames, audit manifests and
    leftover files;
14. serializer round-trip/static systemd parsing;
15. mutation proof: weakening unknown-key rejection, one dangerous prefix,
    profile isolation, env clearing, atomic rollback or secret-output guard must
    make the copied harness red.

Tests may mock `id`, `stat`, `install`, `mv`, `fsync` helper behavior and
`systemd-analyze`, but must verify mock argv and mutation counts. They may not
mock the parser/registry under test.

## Regression and acceptance commands

Run from repository root, without filters:

```bash
bash -n scripts/lib/prod-env-loader.sh \
  scripts/prod-env-prepare.sh \
  scripts/tests/test-prod-env-loader.sh \
  scripts/tests/test-prod-env-profiles.sh

python3.12 -m py_compile scripts/lib/prod-env-tool.py

scripts/tests/test-prod-env-loader.sh
scripts/tests/test-prod-env-profiles.sh
scripts/tests/test-prod-deploy-source-loader.sh
scripts/tests/test-prod-host-offsite-routing.sh

scripts/prod-infra-fingerprint.sh
git diff --check
```

Run the new harness twice from fresh shells. A green case count alone is not
acceptance: show exact command, exit code, stdout/stderr byte counts, stale temp
count and at least six independently applied adversarial mutations.

## Required handoff

Stop after C1A and report:

- exact files changed;
- public CLI/functions and exit-code table;
- profile/key matrix;
- atomicity and signal behavior;
- every command with exact rc and unfiltered final line;
- temp/process leak check;
- adversarial mutation results;
- any source key that could not be placed without an architect decision;
- remaining C1B work (consumer cut-over) and C2 work (canonical DB identity).

Do not start C1B, production rehearsal, commit or push.
