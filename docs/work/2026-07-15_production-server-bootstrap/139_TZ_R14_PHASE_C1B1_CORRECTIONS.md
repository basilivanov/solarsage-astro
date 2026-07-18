# R14 Phase C1B1 — corrective task after independent rejection

Read first:

- `138_REVIEW_R14_PHASE_C1B1_REJECTED_INDEPENDENT.md`;
- the original `137_TZ_R14_PHASE_C1B1_INSTALLED_PROFILE_RUNTIME.md`;
- `AGENTS.md` and accepted C1A review `136_REVIEW_R14_PHASE_C1A_R7K_ACCEPTED_INDEPENDENT.md`.

## Hard boundaries

- Work directly in the current interactive coder session.
- No subagents, Task, explorer, delegation or parallel agents.
- No commit/push, production apply, service/systemd/Docker/database/network/
  SSH/GitHub/Restic/Telegram activity.
- Synthetic `/tmp` sandboxes only; never read real source/profile/token files.
- Do not start C1B2 or C2.
- Preserve all unrelated dirty-worktree changes.

This is a narrow correction. Do not redesign the accepted runtime or weaken
existing C1A tests to obtain green.

## Fix 1 — nonblocking lock open

In the installed-profile read path, make the `create=False` lock open
nonblocking (`O_NONBLOCK` in addition to the existing safe flags). Then:

1. `fstat` and reject FIFO/socket/device/symlink/non-regular/nlink/owner/mode;
2. acquire the existing bounded `LOCK_SH|LOCK_NB`;
3. preserve stable `EXIT_VERIFY`/`EXIT_IO` semantics;
4. do not create, truncate, unlink or replace `.profile.lock`;
5. do not change C1A install lock behavior except where the shared helper must
   remain compatible.

Add to ordinary runtime harness:

- replace the lock with a FIFO;
- run with an external timeout of at most 2 seconds;
- assert the command itself returns the stable validation code quickly, not
  timeout `124`;
- prove no child marker/process/temp mutation.

Do not use a background FIFO writer to make a bad implementation green.

## Fix 2 — strict installed-file byte validation

Update the single canonical `deserialize_envfile()` path used by installed
profiles (and existing verify operations) to reject before returning data:

- NUL, CR, DEL and every ASCII control byte other than the final record LF;
- invalid UTF-8, mapped to `EXIT_VERIFY` with a safe symbolic message;
- interior blank lines, malformed quote/escape and missing final LF as before.

Do not print byte values, reprs, line contents or secret values. Add synthetic
tests that mutate only an optional value (`CORS_ALLOWED_ORIGINS` or another
optional registered value) with U+0001, DEL, CR, NUL and invalid UTF-8. Each
must return `14`, must not execute `/usr/bin/true`, and must leave no temp or
secret-bearing output. Keep exact production-value checks as a separate oracle.

## Fix 3 — real root mutation execution from `astro`

Refactor `test-prod-env-runtime-mutations.sh` so root coverage is never
conditional on the caller's uid:

1. At startup require `sudo -n true`; missing capability is a hard failure.
2. Run root baseline with `sudo -n bash test-prod-env-runtime-root.sh`.
3. For root wrapper mutation, invoke the copied root harness with `sudo -n`.
4. If a tool-root mutation is added, pass its exact copied tool path through a
   real, asserted harness override; do not rely on an ignored variable.
5. Delete the branch that assigns a fake nonzero “caught” result when not root.
6. Print a per-mutation line proving the root oracle actually ran; no SKIP.

Run the mutation harness as the normal `astro` user in acceptance evidence. It
must execute MUT12, not merely report it.

## Fix 4 — deterministic `strace` dependency handling

Choose one and implement it completely:

### Preferred

Replace the MUT04/MUT07 `strace` dependency with a deterministic test oracle
that proves fd-relative/open-no-follow behavior without modifying production
code or relying on a race. The mutation must still be applied exactly once and
the copied canonical harness must turn nonzero for the named reason.

### Acceptable fallback

Keep `strace`, but at the very start of the mutation harness:

- require `command -v strace` and a bounded version probe;
- if absent/failing, exit nonzero with a safe dependency error before any
  mutation is reported;
- assert every strace command returns zero and the log is nonempty before
  interpreting it;
- never treat missing/empty log/strace failure as caught.

Do not add `strace` to production runtime dependencies or host apply actions.

## Fix 5 — exact root-wrapper sandbox substitution

In `test-prod-env-runtime-root.sh`:

- remove the empty/no-op replacement-count branch;
- assert the exact assignment line
  `ENV_DIR="/etc/solarsage/env"` occurs once;
- replace exactly once and assert the canonical assignment is absent from the
  executable sandbox copy (comments may be retained only if they cannot be
  interpreted as a path override);
- assert wrapper/tool copy metadata and executable mode before `sudo -n -u astro`.

## Fix 6 — trusted wrapper PATH

In `scripts/prod-env-run.sh`, after CLI parsing but before `id`, `dirname`,
`stat` or other helper commands, set/export a fixed trusted wrapper PATH such as
`/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`, or invoke every
preflight helper by absolute path. Do not include a caller-writable directory.
The child environment contract in Python remains unchanged and still includes
the documented `/home/astro/.local/bin` for application commands.

Add a wrapper test that runs with a deliberately hostile PATH containing a fake
`stat`/`id`; the wrapper must reject/execute using trusted utilities and the
fake helper must never run. Keep the test synthetic and do not install anything.

## Fix 7 — GRACE maps

Add `START_MODULE_MAP`/`END_MODULE_MAP` with public entrypoints, semantic blocks
and owned tests to:

- `scripts/prod-env-run.sh`;
- each new `scripts/tests/test-prod-env-runtime*.sh` file;
- the changed Python module map, listing `cmd_run_installed`, `cmd_run_clean`,
  `load_installed_profile` and `validate_installed_profile_data` as appropriate.

Do not rewrite old unrelated modules.

## Acceptance commands for the coder

Run directly, with true rc and no output masking:

```bash
bash -n scripts/prod-env-run.sh scripts/tests/test-prod-env-runtime*.sh
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

The mutation harness must be green when run as `astro` because it genuinely
uses `sudo -n`; a missing sudo capability is red. Report explicit evidence for
the four new blocker probes and final stale-process/temp/secret scans.

Stop after this correction and handoff. No commit, push, production action,
C1B2 or C2.
