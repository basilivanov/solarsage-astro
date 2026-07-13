# Stage B4.W3 blocker — canonical API is stale V1; safe resolution options

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Текущий HEAD/origin: `ae62ad8ced1865cef2b2b1b3a0382d2e06065ce0`
Статус: **ARCHITECTURAL BLOCKER — NO FURTHER IMPLEMENTATION AUTHORIZED**

## 1. Observed facts

Real launcher and browser reached the canonical runtime successfully:

~~~text
Next preview root:       127.0.0.1:3003 -> HTTP 200
Next API rewrite:        /api/* -> 127.0.0.1:8000
dev auth:                POST /api/auth/dev -> HTTP 200
real day:                GET /api/day/2026-07-08 -> HTTP 200
mock 18092:              absent
route interception:      zero
~~~

But the real HTTP response identity is:

~~~text
payloadVersion:          today.v1
frontendPayloadVersion:  1
contentVersion:           5
v2.horizons:              absent
~~~

Required identity is:

~~~text
today.v2.1 / 3 / 10
long / medium / fast
~~~

The E2E must fail closed on this mismatch. Accepting V1, returning early on
401, or conditionally skipping horizon DOM is forbidden and is not W3 proof.

## 2. Root cause

Canonical API process:

~~~text
service:                  solarsage-api.service
port:                     127.0.0.1:8000
PID:                      355509
active since:             2026-07-08 21:05:20 MSK
current feature HEAD:     2026-07-12 commits
~~~

The API process predates all accepted B3/B4 backend commits and was deliberately
not restarted in B3.W3C. Only the sidecar was restarted.

The canonical API environment also has no explicit:

~~~text
SOLARSAGE_V2_ENABLED
SOLARSAGE_V2_FRONTEND_ENABLED
~~~

Current defaults select V1:

~~~py
solarsage_v2_enabled = False
selected_scoring_version_for_flags() -> LEGACY_SCORING_VERSION
~~~

B3.W3C's successful `today.v2.1 / 3 / 10` proof used in-process ASGI with
process-local V2 settings. It proved route/DB/sidecar/backend correctness but
did not converge the canonical HTTP API process on port 8000.

## 3. Why W3 cannot self-fix

The authorized W3 launcher must not:

- restart or reconfigure `solarsage-api.service`;
- edit `.env`;
- start a second/manual uvicorn;
- use another API port;
- serve a captured raw payload/fixture;
- route to mock 18092;
- weaken the strict V2 E2E.

Under those constraints the only real backend available to browser 3003 is the
stale V1 process on 8000. Frontend code cannot manufacture backend horizons.

## 4. Resolution options

### Option A — request-scoped local dev V2 (recommended)

Add an explicit dev-preview selection boundary that can select V2 only when all
closed conditions hold:

~~~text
APP_ENV != production
request arrives through direct local preview origin/host on 3003
authenticated session belongs to the dedicated /api/auth/dev identity
explicit dev-preview marker is present
~~~

Then perform one controlled restart of `solarsage-api.service` to load current
code. Ordinary Telegram/public requests remain on the existing flag-selected
family; only the dedicated local preview request selects V2.

Required work:

- backend request-scoped selection without mutating global settings;
- secure local-origin/dev-session guard;
- cache identity uses the same request-scoped selected family;
- frontend dev-only request marker, absent in production build;
- focused security/concurrency/cache tests;
- controlled API restart with rollback proof;
- strict real E2E must then pass `today.v2.1 / 3 / 10`.

Advantages:

- no V2 rollout to ordinary production users before approval;
- no second API/manual uvicorn;
- preview remains one command on 3003 after one accepted API convergence.

Cost: a separate backend/frontend dev-only wave and one canonical API restart.

### Option B — globally enable V2 on canonical API now

Add/update canonical env flags and restart API:

~~~text
SOLARSAGE_V2_ENABLED=true
SOLARSAGE_V2_FRONTEND_ENABLED=true
~~~

Advantages: simplest operationally; strict W3 immediately uses real V2.

Risk: all ordinary users of the canonical API may receive V2 before preview
approval/main frontend rollout. The current production frontend build may not
be compatible with the new identity. This is not recommended without an
explicit rollout decision and production compatibility smoke.

### Option C — second preview API

Run a separate managed API instance on another port with V2 flags.

Rejected under current repository authority:

- AGENTS.md declares port 8000 the only API;
- manual/secondary uvicorn is explicitly forbidden;
- adds another runtime/service/port and recreates the «танцы с бубном» the user
  asked to remove.

This option requires first changing the canonical infrastructure rules and is
not recommended.

## 5. Current worktree safety state

- W2 remains committed/pushed at `ae62ad8...`.
- W3 tooling is uncommitted and under review.
- Port 3003 is stopped; no 18092 listener.
- No main merge, systemd restart, env edit or production deploy was performed.
- Strict E2E must be restored; the current conditional V1/401 acceptance is not
  acceptable for commit.
- Coder is stopped pending architect/user authorization.

## 6. Recommended next authorization

Authorize a new exact wave for **Option A**:

~~~text
B4.W3A — request-scoped local dev V2 selection + controlled API convergence
~~~

The architect will write a detailed allowlist/security/cache/restart ТЗ before
the coder changes any backend or runtime state. W3 launcher/E2E corrections
resume only after that wave produces real `today.v2.1 / 3 / 10` on the normal
3003 acceptance URL.
