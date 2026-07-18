# R14 Phase C1B2 correction — preserve CLI contract before profile bridge

Read completely before editing:

- `AGENTS.md`;
- `143_TZ_R14_PHASE_C1B2_OPERATIONAL_PROFILE_CONSUMERS.md`;
- `144_REVIEW_R14_PHASE_C1B2_REJECTED_CLI_ORDER.md`.

## Mandatory protocol and boundaries

- Work directly in the current interactive `tmux astro:0.0` pane using the
  Gemini 3 Flash AgentCLI Proxy already selected at `localhost:18317`.
- No subagents, Task, explorer, delegation or parallel agents.
- No production host/service/database/Docker/Nginx/SSH/GitHub/Restic/Telegram
  operation, no network, no systemd start/restart/reload, no commit and no push.
- Use synthetic/private `/tmp` test state only. Never read or print a real
  secret, `/etc/solarsage/env/source.env`, installed profile, token, private
  key or production URL.
- Preserve unrelated dirty-worktree changes and all existing safety logic.
- Keep GRACE markers/contracts/maps; do not create duplicate module contracts.
- This is a correction to C1B2 only. Do not start C1B3 or C2.

## Exact implementation

### Affected scripts

Modify only the ordering in:

- `scripts/prod-backup.sh`;
- `scripts/prod-offsite-check.sh`;
- `scripts/prod-offsite-maintenance.sh`.

`scripts/prod-db-restore.sh` is the reference ordering and must not be
reworked for this task.

### Required order

For each affected script, the beginning of execution must have this semantic
order:

1. `set -euo pipefail`, `umask` and existing signal setup remain as they are.
2. Parse the complete supported CLI shape using the script's existing usage
   text and exit semantics:
   - `prod-backup.sh`: no arguments or exactly `--local-only`;
   - `prod-offsite-check.sh`: exactly `--preflight` or exactly `--check`;
   - `prod-offsite-maintenance.sh`: exactly `--run`.
3. Any other shape/value prints the existing usage line to stderr and exits
   with **2**, even when `/etc/solarsage/env/current` is absent and the caller
   has an empty environment.
4. Only after the CLI is accepted, resolve/check/source
   `scripts/lib/prod-profile-context.sh` and call:

   ```bash
   prod_profile_require backup "$SCRIPT_DIR/<script>.sh" "$@"
   ```

   Preserve exact argv boundaries and the existing fail-closed symlink/missing
   helper checks.
5. After the bridge succeeds, retain the existing user/profile checks and all
   DB, Restic, filesystem, lock, signal and safety behavior exactly as before.

For `prod-offsite-maintenance.sh`, it is acceptable to keep the `main` function
and signal handlers, but the argument validation must occur before the context
bridge inside `main`. Do not call `prod_profile_require` twice.

Do not move the bridge ahead of `set -euo pipefail`/`umask`, and do not replace
the bridge with direct env-file sourcing, `eval`, `sh -c`, ambient variables or
`.env.production`.

## Regression test requirements

Extend the existing C1B2 consumer-cutover harness or add a focused test under
`scripts/tests/` (prefer the existing harness if that keeps the public test
contract in one place). It must run each direct script with:

```text
env -i PATH=/usr/bin:/bin <script> <invalid-arg>
```

Assert all of the following for every script:

- exit code is exactly `2`;
- stderr contains the script's usage line;
- no profile-wrapper error is emitted;
- no DB/Restic/service command is invoked;
- no real `/etc/solarsage/env` file is read.

Keep or add positive synthetic checks proving valid calls still enter through
the wrapper and nested maintenance/check or restore/backup calls do not spawn
an unnecessary recursive wrapper. Do not weaken existing consumer-cutover,
backup state-machine, offsite, restore, host-routing or C1A/C1B1 tests.

## Required verification and handoff

Run bounded, non-production checks:

```bash
bash -n scripts/prod-backup.sh scripts/prod-offsite-check.sh \
  scripts/prod-offsite-maintenance.sh scripts/tests/test-prod-profile-consumer-cutover.sh
bash scripts/tests/test-prod-profile-consumer-cutover.sh
bash scripts/tests/test-prod-backup-offsite.sh
bash scripts/tests/test-prod-backup-state-machine.sh
bash scripts/tests/test-prod-offsite-check.sh
bash scripts/tests/test-prod-offsite-maintenance.sh
bash scripts/tests/test-prod-db-restore-safety.sh
bash scripts/tests/test-prod-host-offsite-routing.sh
git diff --check
```

Additionally show the three direct invalid-argument probes and their exact
`rc=2` results. Do not print environment values. Hand off changed files and
outputs, then stop. No commit/push and no next phase.
