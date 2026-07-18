# TZ — minimal host runtime convergence

Independent review found real blockers in the minimal Compose path. This slice fixes exactly A–F below. No R14, no matrix, no new frameworks/suites, no state machines. Update existing focused tests only (orchestrator, wrapper, host routing/profile/unit tests). No apply/install/service/DB/registry/login/push/commit.

## A. Docker authority boundary

`prod-os-bootstrap` forbids `astro` in the docker group, while the orchestrator calls Docker. Do NOT weaken to docker-group membership.

- The forced GitHub wrapper invokes the installed root-owned orchestrator via `sudo -n -H`:
  `/usr/bin/sudo -n -H /usr/local/libexec/solarsage/prod-orchestrator deploy <sha> --manual-confirm`.
- Sudoers (sudo 1.9.15 regex) allows ONLY the exact deploy argv: full 40-lowercase-hex SHA plus `--manual-confirm`. Remove the old active aliases for systemd app-unit restarts and the parked release-authority.
- Orchestrator shebang/exec must be deterministic (`#!/bin/bash`).
- Direct owner commands in the runbook go through root sudo (`sudo /usr/local/libexec/solarsage/prod-orchestrator ...`); the GitHub wrapper exposes only `deploy`.

## B. Fresh/reboot maintenance lock

`/run/solarsage-maintenance.lock` does not exist on a fresh/rebooted host.

- Add a standard systemd-tmpfiles config creating it `root:astro 0660`.
- host-prepare installs it byte-exact (root:root `0644`) into `/etc/tmpfiles.d/`, verifies bytes/metadata and the lock file metadata in `--check`, and runs `systemd-tmpfiles --create` on `--apply`.
- No custom state machine.

## C. Host verify contradiction + canonical daily backup

`verify_host_state` must not require the app units enabled while apply is disable-only.

- App units (api/sidecar/frontend) are installed but required DISABLED; host-prepare never starts/stops/restarts them.
- Daily backup stays canonical and automated: `solarsage-backup.service` ExecStart becomes the installed orchestrator `backup --manual-confirm` (no mutable checkout, no profile engine); the daily timer stays enabled/active.
- Old backup-maintenance timer/service and old backup scripts are parked: host-prepare does not enable/start them and requires them disabled. Do not delete backup data.

## D. Executable migration command

The documented direct compose migration was not executable (missing digest env and RELEASE_SHA).

- Add `prod-orchestrator migrate <sha> --manual-confirm`: exact SHA, maintenance lock, env/DB/restic/compose preflight, resolve+verify target digests, pre-migration backup, run ONLY the one-shot `migrate` profile with pinned digest env. No app up, no release record mutation.
- Deploy remains separate and manual; migrations are never automatic.

## E. Private registry auth

- Runbook gains a one-time standard root Docker login for private GHCR using a read-only packages credential; no token in Git or logs.
- The root orchestrator uses root's Docker config; preflight/pull fail closed on auth errors.

## F. Restore cleanup correctness

- `created=0` is set only after a successful `docker rm`; an EXIT cleanup failure emits one generic warning without secrets.

## Verification

Direct rc only (no pipelines as oracles): bash -n, compose config with temp env, `visudo -cf` for the sudoers template, focused orchestrator harness twice (byte-identical), github-wrapper suite, host routing test, profile/unit tests, namespace layout. Write `180_REPORT_MINIMAL_HOST_RUNTIME_CONVERGENCE.md` and stop for review.
