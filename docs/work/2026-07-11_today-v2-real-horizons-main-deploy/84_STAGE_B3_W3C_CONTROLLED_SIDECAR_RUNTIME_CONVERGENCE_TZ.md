# Stage B3.W3C — controlled sidecar runtime convergence and real proof

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted HEAD/origin: `8db2505a55a71f910bda151d39e6f8ed3036e12f`
Authority: `75`, accepted W1/W2/W3A/W3B, document `83`
Статус: **RUNTIME OPERATION — NO FILE EDIT / COMMIT / PUSH**

## 1. Outcome

Converge the already-configured canonical sidecar process with the committed
repository/runtime identity, then run the accepted W3B proof against real
routes, PostgreSQL and the restarted sidecar.

Current diagnosis is not speculative:

~~~text
loaded sidecar process start:      2026-07-10 11:02:50 MSK
current shared contract changes:   loaded after that process start
sidecar venv constants:            al-1.1 / ss-calc-1.2.0
real proof observed runtime:       al-1.0
service state:                     active
~~~

The service process is stale; repository and venv are current. Do not change
contracts, versions, thresholds, canons or proof validation.

## 2. Authorized state change

Exactly one controlled operation is authorized:

~~~bash
sudo systemctl restart solarsage-sidecar.service
~~~

This wave does not authorize:

- API restart/reload;
- frontend/nginx/database/bot restart;
- daemon-reload or systemd unit edit;
- env edit;
- manual uvicorn or second listener;
- code/document edit;
- git add/commit/push;
- B4/frontend/deploy work.

## 3. Preflight — must pass before restart

Run from repository root and record only structural/runtime facts:

~~~bash
git branch --show-current
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git status --short --branch
git diff --cached --quiet

systemctl is-active solarsage-sidecar.service
systemctl is-active solarsage-api.service
systemctl show solarsage-sidecar.service \
  -p FragmentPath -p MainPID -p ActiveEnterTimestamp -p ExecStart
systemctl show solarsage-api.service -p MainPID

curl -fsS http://127.0.0.1:18091/v1/health \
  | jq '{ok, calculation_version, version}'

apps/solarsage/venv/bin/python - <<'PY'
from solarsage_contracts.versions import (
    ACTIVATION_LAYER_VERSION,
    CALCULATION_VERSION,
)
print(ACTIVATION_LAYER_VERSION, CALCULATION_VERSION)
PY
~~~

Required:

~~~text
branch exact preview branch
HEAD = origin = 8db2505a55a71f910bda151d39e6f8ed3036e12f
tracked tree clean; untracked set is frozen unrelated paths plus this `84` architect document
index empty
sidecar active; API active
unit path exactly /etc/systemd/system/solarsage-sidecar.service
ExecStart exactly canonical venv uvicorn on 127.0.0.1:18091
health ok=true
venv constants al-1.1 / ss-calc-1.2.0
~~~

Record pre-restart sidecar PID/start timestamp and API PID. Do not print
environment contents or secrets.

If any preflight invariant fails, do not restart. Return the blocked callback.

## 4. Controlled restart

Run exactly once:

~~~bash
sudo systemctl restart solarsage-sidecar.service
~~~

Do not combine it with any other service name.

Then allow systemd up to 30 seconds to reach active state. Poll at short
intervals; no sleep longer than 30 seconds is needed inside the executor.

Require:

~~~bash
systemctl is-active --quiet solarsage-sidecar.service
curl -fsS http://127.0.0.1:18091/v1/health >/dev/null
~~~

Record post-restart sidecar PID/start timestamp and API PID.

Invariants:

- sidecar PID changed;
- sidecar start timestamp is current;
- API PID is unchanged;
- only one listener owns `127.0.0.1:18091`;
- no listener appears on 18092 or API 8001;
- sidecar and API both remain active.

Use read-only `ss`/`systemctl` checks. Do not expose process environment.

## 5. Failure handling

If the sidecar does not return active/healthy:

1. do not restart any other service;
2. run one read-only status check;
3. inspect only the last 80 sidecar journal lines for startup/config errors;
4. do not print secrets or request payloads;
5. do not change code/env/unit or attempt a manual uvicorn;
6. return the blocked callback and stop.

Do not repeatedly restart a failing service.

## 6. Official real-route proof

After the sidecar is active and healthy, remove only the old redacted proof:

~~~bash
rm -f /tmp/solarsage-v2-real-api-proof.json
~~~

Run the accepted command exactly once for the primary date:

~~~bash
make prove-today-v2-real \
  DATE=2026-07-08 \
  OUT=/tmp/solarsage-v2-real-api-proof.json
~~~

This executes:

~~~text
ASGI real FastAPI routes
-> /api/auth/dev
-> PUT /api/profile dedicated dev identity
-> /api/day/2026-07-08
-> PostgreSQL 5433
-> canonical sidecar 18091
-> real activation/scoring/horizon pipeline
~~~

Inspect only the redacted allowlist artifact. Never print/store a raw day
response, profile, cookie, activation ID or copy.

### 6.1 Pass outcome

Require exact:

~~~text
status pass
versions calculation=ss-calc-1.2.0
versions activation=al-1.1
versions scoring=ss-scoring-2.0
versions payload=today.v2.1
versions frontend=3
versions content=10
pipeline built / selectedCount=3 / deterministic
horizon IDs long,medium,fast
fixtureDependency=false
sidecarHealth=pass
~~~

If pass, `2026-07-08` is the accepted real date. Stop date work.

### 6.2 Honest unavailable outcome

If exact runtime identities are current but the pipeline is honestly
`unavailable`, invoke the same official Make command separately for ascending
dates `2026-07-01` through `2026-07-31`.

Rules:

- no inline Python or raw response probe;
- one official invocation per date;
- remove/read only the redacted artifact;
- stop at the first pass;
- do not alter profile, thresholds, canons, versions or sidecar;
- if all dates are unavailable, return the blocked-selection callback.

### 6.3 Any error outcome

If the corrected runtime still returns a closed version/health/internal error,
stop immediately. A date scan cannot fix runtime identity.

## 7. Post-proof checks

After pass or honest blocked outcome:

~~~bash
systemctl is-active --quiet solarsage-sidecar.service
systemctl is-active --quiet solarsage-api.service
git status --short --branch
git diff --cached --quiet
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
~~~

Require:

- HEAD/origin unchanged at `8db2505...`;
- tracked tree clean;
- index empty;
- no file changes from the executor runtime operation (architect document `84` remains untracked and byte-identical);
- API PID unchanged;
- services active;
- frozen unrelated paths untouched.

## 8. Success callback

~~~text
READY_STAGE_B3_W3C_REAL_PROOF_REVIEW
accepted_date: <YYYY-MM-DD>
sidecar_restart: PASS exactly one canonical service restart
sidecar_pid: <old> -> <new>
sidecar_runtime_identity: PASS al-1.1 / ss-calc-1.2.0
api_pid: UNCHANGED <pid>
proof_transport: ASGI_REAL_ROUTE
postgres: PASS canonical 5433
sidecar: PASS canonical 18091
versions: PASS calc/al/scoring/payload/frontend/content
pipeline: PASS built/selected/3 deterministic
horizons: PASS long,medium,fast
fixture_dependency: NO
redacted_artifact: /tmp/solarsage-v2-real-api-proof.json PASS
raw_payload_artifacts: ZERO
raw_activation_ids: ZERO
services: api=active unchanged; sidecar=active restarted
head_origin: 8db2505a55a71f910bda151d39e6f8ed3036e12f equal
tracked_tree: CLEAN
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback.

## 9. Blocked callbacks

Preflight/service failure:

~~~text
BLOCKED_STAGE_B3_W3C_SIDECAR_CONVERGENCE
phase: <preflight|restart|health>
closed_reason: <structural reason>
sidecar_restart_count: <0|1>
api_pid: UNCHANGED
files_changed: ZERO
commit: NOT_CREATED
push: NOT_CREATED
next_wave: NOT_STARTED
~~~

All dates honestly unavailable after current identities:

~~~text
BLOCKED_STAGE_B3_W3C_SELECTION_COVERAGE
runtime_identity: PASS current
dates_checked: 2026-07-01..2026-07-31 via official proof only
pass_dates: ZERO
closed_reasons: <redacted counts only>
thresholds_canons_profile: UNCHANGED
services: api=active unchanged; sidecar=active restarted
files_changed: ZERO
commit: NOT_CREATED
push: NOT_CREATED
next_wave: NOT_STARTED
~~~

Stop after callback.
