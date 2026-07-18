# Report — minimal Compose path: independent-review blocker corrections

Status: the five practical blockers found by independent review are corrected in the minimal Compose path only. Source-only; no production action taken. Stopping for review.

## 1. RUNBOOK fully cleaned to canon

`docs/PRODUCTION_RUNBOOK.md` rewritten: active sections contain only the canonical path — `/etc/solarsage/app.env` (`root:astro 0640`), installed `/usr/local/libexec/solarsage/prod-orchestrator` (executed as `astro`), installed `/etc/solarsage/compose/docker-compose.app.yml`, ports 8000/3002/18091, separate DB on 5433, backup/restore via orchestrator, migrations via the one-shot `migrate` profile. All deploy/preflight/rollback/status/backup/restore commands use the installed path (`sudo -u astro -- /usr/local/libexec/solarsage/prod-orchestrator ...`), never the checkout script. The old systemd/profile-engine/`source.env`/`prod-backup`/`prod-db-restore`/systemctl start-stop path exists only in clearly non-operational Appendix A (parked). `docs/DEPLOYMENT.md` command forms aligned to the installed path. Verified: no checkout-path command references and no `systemctl start <app>` instructions remain in docs.

## 2. Cutover contradiction resolved (no state machine, no unrequested downtime)

`scripts/deploy/prod-host-prepare.sh` `--apply` no longer enables the app systemd units: `APP_UNITS` contains only the auxiliary backup timers. The `COMPOSE_OWNED_UNITS` block only **disables autostart** of `solarsage-sidecar/api/frontend.service` via plain `systemctl disable` — metadata-only, **never `--now`, never stop** — so a repeated host-prepare after cutover cannot restore autostart, and no unrequested production downtime is caused by the preparation script. The actual stop remains a separate manual one-time cutover step ordered by the owner immediately before the first Compose deploy. Module contract invariant updated accordingly ("Never start/restart/stop ... only disabled (never --now, never stopped)"). `test-prod-host-offsite-routing.sh` asserts: enable list must not contain app units; convergence must contain `systemctl disable "$unit"`; and must NOT contain `stop`/`restart`/`--now`. Runbook states the stop is ONLY the owner's explicit command. `--apply` NOT executed.

## 3. restore_cmd cleanup trap

`restore_cmd` now arms `trap 'rehearsal_cleanup || true' EXIT` plus `exit 130/143/129` on INT/TERM/HUP. The trap removes only the created unique container `solarsage-restore-rehearsal-$$`; an explicit checked cleanup runs on success; a failed `rm` surfaces as `rehearsal container cleanup failed`. Harness OC23: aborted rehearsal (injected psql failure) returns 78 and leaves no created container; the pre-existing fixed-name container is untouched.

## 4. Requested SHA protected from env substitution

`load_env_file` preserves the invocation `RELEASE_SHA` before sourcing: a conflicting `RELEASE_SHA` inside `/etc/solarsage/app.env` is a hard failure (`env file RELEASE_SHA conflicts with the requested target SHA`, no activation); a matching value is irrelevant because the requested value is restored after sourcing. Harness OC24 covers both branches (conflict → 78 without pull/up; match → deploy proceeds with the requested tag). Runbook section 2 documents that `RELEASE_SHA` must not be present in the env file.

## 5. Rehearsal image digest — DEFERRED

Not pinned. Rationale: pinning a real `postgres` digest requires a registry lookup (not authorized in this slice), a fabricated digest would be fake configuration, and adding a new required env variable expands the env contract beyond these corrections. The rehearsal container is an isolated throwaway target, not part of the release identity path (which is digest-pinned). Deferred to the restore-runbook slice.

## Verification (direct rc)

| Check | rc |
|---|---|
| `test-prod-orchestrator.sh` run 1 | 0 — 26/26 |
| `test-prod-orchestrator.sh` run 2 | 0 — 26/26, output byte-identical |
| `bash -n` orchestrator/harness/host-prepare/routing-test/wrapper | 0 |
| `test-prod-host-offsite-routing.sh` | 0 |
| `test-prod-profile-consumer-cutover.sh` | 0 |
| `test-prod-github-wrapper.sh` | 0 (56+10) |
| `test-prod-namespace-layout.sh` | 0 |
| `docker compose --env-file <temp> -f infra/production/docker-compose.app.yml config --quiet` | 0 |
| docs grep: no checkout-path orchestrator commands, no `systemctl start <app>` | 0 matches |

## Explicit non-actions

No `--apply`/install, no service change, no DB action, no image build/push, no commit/push. R14 files, stale workflow validator, old matrix and application business logic untouched.
