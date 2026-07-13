# Stage 1.W3 — architect runtime acceptance evidence

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted implementation SHA: `55d98917842bd94700030356da7fa1fc50abe86e`
Runtime ТЗ:

- `113_STAGE_1_W3_CONTROLLED_CANONICAL_API_CONVERGENCE_TZ.md`
- `114_STAGE_1_W3_ARCH_ERRATA_LEGACY_UNVERSIONED_PREFLIGHT_TZ.md`

Статус: **ACCEPTED — CANONICAL API CONVERGED; W3 DOCS CHECKPOINT REQUIRED**

## 1. Решение архитектора

Stage 1.W3 принят.

Единственный canonical API process на `127.0.0.1:8000` теперь загрузил
accepted request-scoped W2 code. Глобальные V2 flags не включены.

Доказано реальным HTTP:

```text
ordinary/local control request without marker
  -> today.v1 / frontend 1 / v2 absent

same transport and same dev identity with exact marker
  -> today.v2.1 / frontend 3 / content 10
  -> built long / medium / fast horizons

subsequent control request without marker
  -> today.v1 / frontend 1 / v2 absent
```

Это подтверждает request scope, отсутствие global settings mutation и
раздельные V1/V2 cache families.

## 2. Authorized runtime mutation

До W3:

```text
API MainPID: 355509
API start: Wed 2026-07-08 21:05:20 MSK
```

Выполнена ровно одна ручная операция:

```bash
sudo systemctl restart solarsage-api.service
```

После W3:

```text
API MainPID: 3887119
API start: Mon 2026-07-13 05:12:53 MSK
API NRestarts: 0 after new invocation
API InvocationID: 56a5c781ea6a45068e80ae43f81d37e0
ActiveState/SubState: active/running
```

System journal содержит один exact lifecycle в `05:12:53 MSK`:

```text
Stopping solarsage-api.service
Deactivated successfully
Stopped solarsage-api.service
Started solarsage-api.service
```

Второго manual restart, automatic restart или manual API process нет.

## 3. Corrected pre-restart baseline

Первый run до restart правильно fail-closed остановился, потому что stale API
не сериализовал новые discriminator fields:

```text
auth = 200
control = 200
schemaVersion = today/v1
payloadVersion = absent
frontendPayloadVersion = absent
v2 = absent
restart = not performed
```

Архитектор выпустил narrow errata 114. Она разрешила только эту closed
legacy-unversioned V1 форму до restart. V2 body, V2 discriminator, partial
discriminator или другое schemaVersion оставались absolute deny.

После full repeated preflight наблюдалось:

```text
PRE_RESTART_CONTROL: PASS_LEGACY_UNVERSIONED_V1
adversarial public raw Host chain: PASS_DENIED
W2 transport module: 59 passed
```

Post-restart contract не ослаблялся и прошёл уже с explicit versions.

## 4. Coder real HTTP proof

В одном in-memory dev session coder выполнил:

```text
control -> preview -> control -> preview
```

Результат:

```text
control versions: today.v1 / 1
preview versions: today.v2.1 / 3 / 10
preview scoring: ss-scoring-2.0
preview calculation: ss-calc-1.2.0
preview activation: al-1.1
control after preview: still today.v1 / 1
```

Horizon proof:

```text
order: long, medium, fast
unique horizon ids: true
pipeline: today-horizon-pipeline-audit.v1 / built / selected / 3
long timing: background / date
medium timing: peaked / instant
fast timing: building / instant
activation counts: long=1, medium=1, fast=1
action/avoid counts: long=1/1, medium=3/1, fast=1/1
```

Для каждого горизонта доказаны:

- non-empty activation ids;
- activation ids backed by real `v2.activationEvidence`;
- non-empty likely spheres and manifestations;
- non-empty do/avoid actions;
- actions validity aligned with timing end;
- medium/fast exact peak fields;
- action and technique provenance subset of parent horizon;
- intro activation ids subset of horizon union;
- meta/audit/body version alignment.

Human copy и полный payload в evidence не выводились.

## 5. Cache separation

Для exact dev identity и `2026-07-08` найдены coherent rows обеих families:

```text
coherent V1 rows: 1
coherent V2 rows: 1
cache keys non-empty: true
cache keys distinct: true
persisted frontend versions: 1,3
persisted scoring versions align with payload meta: true
V1 row has no V2 body: true
V2 row validates current audit/horizons: true
```

Ни user UUID, ни profile hash, ни payload JSON, ни полный cache hash не
выводились.

## 6. Journal privacy and runtime health

Coder proof:

```text
session token absent: true
raw cookie value absent: true
preview header/value absent: true
dev identity absent: true
birth data absent: true
traceback/critical runtime failure absent: true
runtime 5xx absent: true
sidecar failure/timeout absent: true
split-brain failure absent: true
```

API and sidecar health returned exact 200.

## 7. Independent architect review

Архитектор не полагался только на coder callback и независимо повторил real
HTTP/cache/journal proof после завершения coder process.

Independent result:

```text
ARCH_INDEPENDENT_RUNTIME_REVIEW: PASS
control sequence: today.v1/1 -> today.v2.1/3/10 -> today.v1/1
horizons: long,medium,fast
horizon pipeline: built/selected/3
timing: long=background/date,medium=peaked/instant,fast=building/instant
cache families: v1,v2
cache keys distinct: true
journal privacy and runtime errors: PASS
```

Independent verifier used one asyncio event loop for HTTP, DB and engine
cleanup and exited cleanly with code 0.

## 8. Local verifier cleanup warning — reviewed, not hidden

Coder's first post-restart verifier produced a local SQLAlchemy/asyncpg cleanup
traceback after all assertions because it called the same async engine from
different short-lived event loops during disposal.

Important facts:

- it was emitted by the one-off shell verifier, not by canonical API/sidecar;
- product requests, cache assertions and privacy assertions had passed;
- verifier process exited 0 after safe results;
- service journal had no traceback/runtime failure;
- architect repeated the same substantive proof with one event loop;
- the independent verifier exited cleanly without cleanup warning.

Therefore this is classified as an evidence-script lifecycle warning, not a
product/runtime defect. No repository script was created or changed, and no
second restart was performed.

## 9. Service and infrastructure invariants

Unchanged witnesses:

```text
sidecar MainPID: 3582982
sidecar start: Sun 2026-07-12 22:02:52 MSK
frontend MainPID: 916433
frontend start: Thu 2026-07-09 11:30:03 MSK
frontend listener child: 916457 on 3002
nginx MainPID: 1048
nginx start: Wed 2026-07-01 15:36:15 MSK
```

All remain active/running with `NRestarts=0` in their current invocations.
Their journals contain no lifecycle restart during W3.

Listeners after W3:

```text
127.0.0.1:8000 -> canonical API PID 3887119
127.0.0.1:18091 -> canonical sidecar PID 3582982
*:3002 -> production frontend child PID 916457
3003 -> absent
8001 -> absent
18092 -> absent
```

No manual uvicorn, second API, mock or preview frontend exists.

## 10. Env/unit immutability

Before/after hashes and metadata matched:

```text
.env SHA-256:
4c640f968d7a1163d79b397241496ccdc5d485ddc9895c12da486b8225bd94a7

solarsage-api.service SHA-256:
88306782b4276dcbb436d93a8fd0b6b6bf3591973207e517244d86abaa65de8a
```

Final metadata:

```text
.env: size=2219 mtime=1780922870 mode=664 owner=astro:astro
unit: size=502 mtime=1780260735 mode=644 owner=root:root
```

Safe flag truth:

```text
APP_ENV=development
SOLARSAGE_V2_ENABLED=<UNSET>
SOLARSAGE_V2_FRONTEND_ENABLED=<UNSET>
```

No env edit, unit edit, daemon-reload or nginx change occurred.

## 11. Repository state

At acceptance:

```text
branch: preview/solarsage-v2-human-first-navigator-ux
HEAD: 55d98917842bd94700030356da7fa1fc50abe86e
origin: 55d98917842bd94700030356da7fa1fc50abe86e
tracked worktree: clean
index: empty
```

Untracked scope consists only of five frozen unrelated paths plus architect
documents 113, 114 and this 115 evidence document.

## 12. Acceptance decision and next boundary

Stage 1.W3 runtime is accepted.

Before S1.W4 starts, documents 113–116 must be committed and pushed as one
docs-only checkpoint. That checkpoint must not restart services or start 3003.

After the docs checkpoint is independently verified, S1.W4 may:

- start only `pnpm preview:v2:real` on 3003;
- run strict no-interception desktop/mobile E2E;
- collect screenshots and redacted network evidence;
- leave the accepted review URL running for the user.

Main merge, production deploy and global V2 rollout remain forbidden until
explicit user visual approval.
