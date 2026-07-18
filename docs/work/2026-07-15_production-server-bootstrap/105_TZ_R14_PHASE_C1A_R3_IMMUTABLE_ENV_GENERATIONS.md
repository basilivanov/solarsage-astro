# R14 Phase C1A-R3 — immutable env generations with one atomic switch

## Architecture decision

Replace sequential installation of seven live files with immutable generation
directories and one atomic symlink switch. This is the canonical C1A design.

Why: seven independent renames cannot provide a single atomic visibility point.
A verified immutable generation plus one `current` symlink gives all consumers
one coherent profile set and makes rollback one atomic pointer switch.

Read:

- `99_TZ_R14_PHASE_C1A_ENV_PROFILE_ENGINE.md` for profile/secret rules;
- `103_TZ_R14_PHASE_C1A_R2_TRANSACTION_AND_HARNESS_FIX.md` for parser/test
  corrections;
- `104_REVIEW_R14_PHASE_C1A_R2_REJECTED_TRANSACTION_UNCHANGED.md` for current
  blockers.

Still no C1B/C2, production/network/SSH/DB/Docker/systemd mutation, commit or
push.

## 1. Canonical filesystem layout

```text
/etc/solarsage/env/                         root:astro 0750, real directory
  source.env                                root:astro 0640, nlink=1
  generations/                              root:astro 0750, real directory
    gen-<32-lowercase-hex>/                 root:astro 0750, immutable
      api.env                               root:astro 0640
      sidecar.env                           root:astro 0640
      db.env                                root:astro 0640
      backup.env                            root:astro 0640
      migration.env                         root:astro 0640
      frontend-build.env                    root:astro 0640
      deploy-control.env                    root:astro 0640
  current -> generations/gen-<32-hex>       root:astro symlink
  .profile.lock                             root:astro 0640, real regular
```

Generation id is random (`secrets.token_hex(16)`), never a hash of secret
values. No secret-derived data appears in filenames or normal logs.

Do not generate direct `/etc/solarsage/env/api.env` etc. C1B will update systemd,
Compose and scripts to read `current/*.env`. Until C1B, this engine remains
preparatory and no production consumer is changed.

## 2. Put the transaction in the Python engine

The repeated Bash rollback is rejected. Add exact subcommands to
`scripts/lib/prod-env-tool.py`:

```text
install-set --source PATH --env-dir PATH --domain DOMAIN
check-installed --source PATH --env-dir PATH --domain DOMAIN
```

`prod-env-prepare.sh` remains the production boundary:

- exact `--apply|--check` CLI;
- canonical literal paths only;
- root-only apply, root/astro check;
- exact production owner/mode/type checks;
- calls `install-set` or `check-installed` with canonical paths;
- contains no copy/rename/rollback loop itself.

Python lower-level operations accept explicit paths for sandbox tests. They
derive expected uid/gid from the validated env directory; the production shell
independently proves that identity is `root:astro`. This lets isolated tests run
as `astro` without lying about core file operations.

## 3. Concurrency and safe path handling

Both operations open env directory and `generations` using
`O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC`, fstat them and operate by `dir_fd` with
relative names. Do not reopen the original directory pathname for render,
verify, symlink or rename operations.

Open `.profile.lock` with `O_NOFOLLOW|O_CLOEXEC`, regular/nlink=1, and use:

- exclusive `fcntl.flock` for install;
- shared `fcntl.flock` for check.

Lock acquisition is bounded and fail-closed. Never delete the lock file during
normal operation.

Validate `current` with `lstat/readlink` by dir fd:

- it is absent (first install) or a symlink;
- target exact relative form `generations/gen-[0-9a-f]{32}`;
- no absolute path, slash suffix, `..`, extra components or external target;
- target is a real directory directly under canonical `generations`;
- all seven profiles are real regular nlink=1 with expected owner/group/mode;
- no symlink profile and no extra expected-name collision.

## 4. Install state machine

### 4.1 Prepare immutable generation

Under `generations`, create private staging directory
`.staging-<32-hex>` mode 0700.

Using one already parsed in-memory source:

1. render all seven canonical profile byte strings;
2. create each by dir fd with `O_CREAT|O_EXCL|O_NOFOLLOW`, mode 0600;
3. write all bytes, fchown to env-dir uid/gid, fchmod 0640;
4. fsync each file;
5. independently reopen/verify type, nlink, uid/gid, mode and exact content;
6. chmod staging directory 0750 and fsync it;
7. atomically rename staging to `gen-<id>` inside `generations`;
8. fsync the generations directory.

Any pre-switch failure removes only the private staging directory. It never
touches `current` or the previous generation.

### 4.2 One atomic switch

Record the previous `current` target (or explicit absent state). Create a
temporary symlink `.current-<id>` with relative target
`generations/gen-<id>`, validate its exact bytes, then `os.replace` it to
`current` using env-dir fds. Fsync env directory.

After switch, resolve and verify `current` points to the complete new immutable
generation and every profile matches expected bytes/metadata.

### 4.3 Rollback pointer only

If post-switch verification/fsync fails:

- previous target existed: create a new temp symlink to that exact validated
  target and atomically replace `current`, fsync, then verify old target;
- first install: unlink `current` by dir fd, fsync, verify absent;
- never mutate the old or new generation contents during rollback;
- if rollback cannot be proven, preserve both generations and emit only safe
  paths plus symbolic recovery codes.

On success, retain the previous generation. C1A does not delete generations;
retention is a later explicit maintenance task.

## 5. Signal contract

Install Python handlers for HUP/INT/TERM that raise a private transaction signal
exception. At every state:

- before switch: clean staging, leave current unchanged;
- after switch: atomically restore previous current/absent state;
- successful recovery exits exactly 129/130/143;
- failed recovery exits a distinct recovery error and preserves artifacts.

SIGKILL/power-loss recovery: because generation creation is immutable and the
only live switch is an atomic symlink rename, `current` is either old or new.
On the next check/install, stale `.staging-*` and `.current-*` are reported, not
silently deleted. Add a separate explicit cleanup policy later; C1A fail-closes.

## 6. `check-installed`

Read-only under a shared lock:

- parse/validate source once;
- validate env/generations/current physical contracts;
- verify current generation profiles equal the source-derived expected bytes;
- reject stale staging/temp symlinks, direct legacy profile files and invalid
  current targets;
- snapshot before/after directory entries, metadata and bytes in the harness to
  prove zero mutation;
- output only current generation id, profile names/status and value-independent
  contract digest.

## 7. Finish remaining Python correctness

In the same bounded task:

- remove `traceback.print_exc()` and all raw exception output;
- allow a plain `$` value while still rejecting `${`, `$(` and backticks;
- require exact lowercase `openrouter|anthropic` (no `.lower()` acceptance);
- apply bounded size/read-until-EOF to profiles as well as source;
- make canonical deserializer reject blank interior lines, dangling escapes and
  duplicate/equal-order anomalies;
- make named-profile validate actually call `render_profile` for that profile;
- ensure render/verify path operations use validated directory fds, not the
  original pathname after opening it.

## 8. Root-independent executable harness

Rewrite the prepare section of `test-prod-env-profiles.sh` around immutable
generations.

- Sandbox env dir is owned by the current user and mode 0750.
- Python install derives current uid/gid, so do not mock chown/chmod/stat/mv.
- Sandbox shell wrapper may narrowly shim only `id` and production owner-name
  checks; assert each shim argv. Core filesystem operations remain real.
- Copy prepare + tool into exact relative layout and assert path substitutions.

Required cases:

1. first install: current absent -> valid generation/current;
2. repeat install with changed non-secret public value: current changes once,
   old generation remains immutable;
3. `check-installed` green and byte/metadata read-only;
4. invalid current targets (absolute, `..`, outside, malformed id, directory
   instead of symlink);
5. profile symlink/hardlink/mode corruption;
6. stale `.staging-*`/`.current-*` rejection;
7. failure at each pre-switch file write/chown/chmod/fsync/verify/rename: current
   remains old;
8. failure after current switch: pointer returns to old target;
9. HUP/INT/TERM before and after switch: exact rc and old pointer;
10. first-install post-switch failure: current returns absent;
11. concurrent install/check lock contention is bounded/fail-closed;
12. no secret canary in stdout/stderr/path names; zero orphan processes.

Failure injection must use exact, verified mutations of a sandbox copy of the
Python engine. Do not add production environment test hooks or path overrides to
the shell wrapper.

## 9. Real mutation harness

Replace the current direct behavior table. For each mutation, copy the tool and
the canonical harness, substitute the copy path exactly once, run the copied
harness, and require nonzero.

At minimum:

- required key;
- source O_NOFOLLOW;
- unknown/duplicate CLI;
- PGSSLMODE;
- serializer backslash escape;
- provider diagnostic leak;
- current target traversal;
- generation profile symlink acceptance;
- atomic current switch removed;
- post-switch rollback removed;
- fsync swallowed;
- signal status changed.

The mutation runner itself fails if mutation application count is not exactly
one, syntax is invalid, copied harness was not executed, or a mutated harness
returns zero.

## 10. Acceptance

Run directly with real rc capture, no `tail` masking:

```bash
bash -n scripts/lib/prod-env-loader.sh scripts/prod-env-prepare.sh \
  scripts/tests/test-prod-env-loader.sh scripts/tests/test-prod-env-profiles.sh \
  scripts/tests/test-prod-env-profiles-mutations.sh
python3.12 -I -S -c 'compile(open("scripts/lib/prod-env-tool.py", "rb").read(), "scripts/lib/prod-env-tool.py", "exec")'
bash scripts/tests/test-prod-env-loader.sh
bash scripts/tests/test-prod-env-profiles.sh
bash scripts/tests/test-prod-env-profiles.sh
bash scripts/tests/test-prod-env-profiles-mutations.sh
bash scripts/tests/test-prod-deploy-source-loader.sh
bash scripts/tests/test-prod-host-offsite-routing.sh
bash scripts/prod-infra-fingerprint.sh
git diff --check
```

Handoff includes true rc/stdout/stderr bytes, current target before/after every
failure/signal case, generation inventory, mutation IDs and stale paths. Stop
after C1A-R3; no C1B/C2/commit/push.
