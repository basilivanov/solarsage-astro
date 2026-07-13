# Stage 1.W3 — controlled canonical API convergence and real HTTP proof

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted W2 SHA: `55d98917842bd94700030356da7fa1fc50abe86e`
Accepted W2 parent: `933e749137d00c262c8f2cedec7b945582bf40d1`
Parent plans:

- `101_TWO_STAGE_COMPLETION_MASTER_PLAN.md`
- `102_STAGE_1_SAFE_DEV_SCOPED_V2_PREVIEW_MASTER_TZ.md`

Статус: **AUTHORIZED RUNTIME WAVE — ONE API RESTART, NO PRODUCT EDITS**

## 1. Цель волны

Загрузить уже принятый и запушенный W2-код в единственный канонический API
процесс на `127.0.0.1:8000`, не меняя env и не включая V2 глобально.

После ровно одного ручного restart должны одновременно выполняться два
реальных HTTP-контракта для одного dev-пользователя и одной даты:

```text
тот же локальный transport, но БЕЗ exact preview marker
  -> today.v1
  -> frontendPayloadVersion = 1
  -> v2 = null/absent

тот же локальный transport + exact preview marker
  -> today.v2.1
  -> frontendPayloadVersion = 3
  -> contentVersion = 10
  -> horizons = [long, medium, fast]
```

Это runtime/evidence wave. Никакой реализации, исправления кода, изменения
контрактов или запуска frontend preview в этой волне нет.

## 2. Принятая база — не пересматривать

Архитектор независимо подтвердил:

```text
branch:              preview/solarsage-v2-human-first-navigator-ux
HEAD:                55d98917842bd94700030356da7fa1fc50abe86e
parent:              933e749137d00c262c8f2cedec7b945582bf40d1
subject:             feat(preview): add guarded real v2 request path
commit paths:        exact 9
local/tracking/remote equal: yes
tracked worktree:    clean
index:               empty
```

W2 accepted gates:

```text
adversarial raw Host chain: PASS_DENIED
backend exact GRACE:        4/4
backend W2 module:          59 passed
backend focused:            180 passed
full API:                   1384 passed, 4 skipped
frontend focused:           20 passed
full Vitest:                1063 passed
typecheck/contracts/prod guard: PASS
```

Не повторять full suites. В preflight повторяется только минимальный runtime
security proof, указанный ниже.

## 3. Разрешённый scope

Разрешены только:

1. read-only preflight;
2. создание временных файлов только под `/run/user/$(id -u)` или `/tmp` с
   mode `0600`, с обязательным удалением в том же shell/proof process;
3. ровно одна ручная команда:

   ```bash
   sudo systemctl restart solarsage-api.service
   ```

4. read-only post-restart HTTP, DB, journal, process and filesystem proof;
5. callback архитектору по точному формату раздела 12.

В этой волне coder не создаёт и не редактирует ни одного repository file.
Файл `113_..._TZ.md` уже создан архитектором и должен остаться byte-identical.

## 4. Абсолютные запреты

Запрещено:

- `git add`, commit, push, merge, rebase;
- редактировать product/test/config/docs files;
- редактировать `.env`, `.env.production`, systemd unit или nginx;
- `systemctl daemon-reload`;
- перезапускать/останавливать sidecar, frontend, nginx, PostgreSQL или Docker;
- выполнять второй ручной restart API, даже если первый proof не прошёл;
- запускать manual `uvicorn`, API на другом порту или второй API process;
- использовать API port `8001`;
- запускать `pnpm preview:v2:real`, Next на `3003` или mock на `18092`;
- fixture, route interception, captured payload, raw JSON fixture;
- менять `APP_ENV`, `SOLARSAGE_V2_ENABLED`,
  `SOLARSAGE_V2_FRONTEND_ENABLED` или любой другой env;
- удалять/инвалидировать существующие cache rows;
- печатать session token, Cookie/Set-Cookie value, полный Today payload,
  birth data, UUID пользователя или human copy из payload;
- трогать frozen unrelated paths:

  ```text
  .grace/
  artifacts/design/
  docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
  grace.db
  skills/
  ```

Если любой обязательный preflight gate не проходит — restart запрещён, вернуть
`BLOCKED_STAGE_1_W3_PREFLIGHT`.

Если restart выполнен, но любой post-restart gate не проходит — не чинить и не
делать второй restart. Собрать безопасную диагностику и вернуть
`BLOCKED_STAGE_1_W3_POST_RESTART`.

## 5. Privacy-safe evidence contract

В callback разрешены только:

- SHA, branch, commit subject;
- HTTP status;
- payload/frontend/content/scoring/calculation/activation version labels;
- `cached` boolean;
- horizon ids, counts, timing state/precision presence;
- audit status/reason/count;
- service names, PID, start timestamps, listener counts/ports;
- cache row count, version family labels и boolean `cache_keys_distinct`;
- boolean результаты privacy scans;
- hashes файлов `.env` и unit, но не их содержимое;
- test totals.

Нельзя включать:

- opaque session token;
- raw `Cookie`/`Set-Cookie`;
- user UUID;
- точные персональные данные;
- полный JSON ответа;
- title/summary/actions/manifestation human copy;
- raw LLM prompt/output;
- raw journal dump.

Временный session token держать только в памяти process. Не передавать token в
argv дочернего process и не сохранять в repository.

## 6. Phase A — mandatory preflight before restart

### 6.1 Git identity and exact worktree state

Проверить:

```bash
git branch --show-current
git rev-parse HEAD
git rev-parse HEAD^
git show -s --format=%s HEAD
git rev-parse refs/remotes/origin/preview/solarsage-v2-human-first-navigator-ux
git ls-remote --heads origin refs/heads/preview/solarsage-v2-human-first-navigator-ux
git diff --quiet
git diff --cached --quiet
git status --short
```

Обязательный результат:

```text
branch = preview/solarsage-v2-human-first-navigator-ux
HEAD = local tracking = ls-remote = 55d98917842bd94700030356da7fa1fc50abe86e
parent = 933e749137d00c262c8f2cedec7b945582bf40d1
subject = feat(preview): add guarded real v2 request path
tracked diff = empty
index = empty
```

`git status --short` может содержать только шесть untracked entries:

```text
?? .grace/
?? artifacts/design/
?? docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
?? docs/work/2026-07-11_today-v2-real-horizons-main-deploy/113_STAGE_1_W3_CONTROLLED_CANONICAL_API_CONVERGENCE_TZ.md
?? grace.db
?? skills/
```

Любое другое изменение блокирует restart.

### 6.2 Canonical systemd identity

Снять evidence:

```bash
systemctl show solarsage-api.service \
  --property=Id,LoadState,ActiveState,SubState,FragmentPath,User,Group,WorkingDirectory,ExecStart,EnvironmentFiles,MainPID,ExecMainStartTimestamp \
  --no-pager
systemctl cat solarsage-api.service
```

Проверить exact invariants:

```text
Id = solarsage-api.service
LoadState = loaded
ActiveState = active
SubState = running
FragmentPath = /etc/systemd/system/solarsage-api.service
User = astro
Group = astro
WorkingDirectory = /opt/solarsage-astro/apps/api
EnvironmentFiles = /opt/solarsage-astro/.env (ignore_errors=no)
ExecStart executable = /opt/solarsage-astro/apps/api/.venv/bin/uvicorn
ExecStart app = app.main:app
ExecStart host = 127.0.0.1
ExecStart port = 8000
```

Не принимать symlink/override/alternate unit, manual process или port 8001.

Записать old API PID и start timestamp. Ожидаемая до-restart база на момент
выдачи ТЗ:

```text
API MainPID = 355509
API start = Wed 2026-07-08 21:05:20 MSK
```

Если фактический PID/start уже другой, restart не выполнять: сначала вернуть
`BLOCKED_STAGE_1_W3_PREFLIGHT` с причиной `API_CHANGED_BEFORE_AUTHORIZED_RESTART`.

### 6.3 Environment and immutable file hashes

Проверить только безопасные значения; secrets не печатать:

```bash
for key in APP_ENV SOLARSAGE_V2_ENABLED SOLARSAGE_V2_FRONTEND_ENABLED; do
  value=$(sed -n "s/^${key}=//p" .env | tail -n 1)
  if [ -n "$value" ]; then
    printf '%s=%s\n' "$key" "$value"
  else
    printf '%s=<UNSET>\n' "$key"
  fi
done
sha256sum .env /etc/systemd/system/solarsage-api.service
stat -c '%n %s %Y %a %U:%G' .env /etc/systemd/system/solarsage-api.service
```

Обязательная база:

```text
APP_ENV=development
SOLARSAGE_V2_ENABLED=<UNSET>
SOLARSAGE_V2_FRONTEND_ENABLED=<UNSET>
```

Сохранить в отчёте before SHA-256, size, mtime, mode, owner. После restart они
должны совпасть буквально.

### 6.4 Service and port baseline

```bash
systemctl show \
  solarsage-api.service \
  solarsage-sidecar.service \
  solarsage-frontend.service \
  nginx.service \
  --property=Id,ActiveState,SubState,MainPID,ExecMainStartTimestamp \
  --no-pager

ss -ltnp 'sport = :3002 or sport = :3003 or sport = :8000 or sport = :8001 or sport = :18091 or sport = :18092'
```

Записать exact PID/start для всех четырёх services. До restart:

- API, sidecar, frontend, nginx active/running;
- ровно один listener `127.0.0.1:8000`, владелец old API PID;
- ровно один listener `127.0.0.1:18091`, canonical sidecar;
- production frontend listener `3002` существует;
- `3003`, `8001`, `18092` отсутствуют.

Sidecar/frontend/nginx PID и start timestamp — immutable witnesses для всей W3.

### 6.5 Health baseline

```bash
curl -fsS --max-time 5 -o /dev/null -w 'api_health=%{http_code}\n' \
  http://127.0.0.1:8000/api/health
curl -fsS --max-time 5 -o /dev/null -w 'sidecar_health=%{http_code}\n' \
  http://127.0.0.1:18091/v1/health
```

Оба exact `200`.

### 6.6 Minimal accepted-code security proof

Не запускать full suites. Выполнить только:

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python - <<'PY'
from app.services.today_preview_guard import (
    TODAY_PREVIEW_HEADER_VALUE,
    TODAY_PREVIEW_TG_USER_ID,
    TODAY_PREVIEW_TG_USERNAME,
    TodayPreviewGuardInput,
    TodayPreviewGuardReason,
    authorize_today_preview,
)

case = TodayPreviewGuardInput(
    app_env="development",
    marker_value=TODAY_PREVIEW_HEADER_VALUE,
    client_host="127.0.0.1",
    host="public.example:8000",
    origin=None,
    forwarded=None,
    x_forwarded_for="127.0.0.1",
    x_forwarded_host="127.0.0.1:3003",
    x_forwarded_port="3003",
    x_real_ip=None,
    tg_user_id=TODAY_PREVIEW_TG_USER_ID,
    tg_username=TODAY_PREVIEW_TG_USERNAME,
)
decision = authorize_today_preview(case)
assert decision.authorized is False
assert decision.reason is TodayPreviewGuardReason.HOST_DENIED
print("ADVERSARIAL_HOST_CHAIN: PASS_DENIED")
PY

PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_preview_transport.py -q
```

Обязательный результат:

```text
ADVERSARIAL_HOST_CHAIN: PASS_DENIED
59 passed
```

### 6.7 Pre-restart real HTTP control must still be V1

Сделать реальный HTTP login через `POST http://127.0.0.1:8000/api/auth/dev`,
удержать opaque cookie только в памяти, затем реальный
`GET /api/day/2026-07-08` без preview marker.

Транспорт day request:

```text
Host: 127.0.0.1:8000
Origin: http://127.0.0.1:3003
X-Forwarded-For: 127.0.0.1
X-Real-IP: 127.0.0.1
X-Forwarded-Host: 127.0.0.1:3003
X-Forwarded-Port: 3003
Cookie: held only in process memory
X-SolarSage-Preview-Mode: ABSENT
```

Не печатать response body. Парсить JSON в памяти и вывести только safe summary.

Обязательный pre-restart результат:

```text
auth_status = 200
control_status = 200
control.payloadVersion = today.v1
control.frontendPayloadVersion = 1
control.v2_present = false
```

Если stale API неожиданно возвращает V2 или request не 200 — restart не
выполнять.

## 7. Phase B — the only authorized mutation

Сразу перед операцией записать UTC epoch и monotonic narrative timestamp для
journal window. Затем выполнить ровно один раз:

```bash
sudo systemctl restart solarsage-api.service
```

Не выполнять `daemon-reload`. Не объединять restart с другими services. Не
использовать `restart || restart` или retry loop.

После команды ждать readiness polling, а не делать второй restart:

```bash
for attempt in $(seq 1 30); do
  if curl -fsS --max-time 2 -o /dev/null http://127.0.0.1:8000/api/health; then
    printf 'api_ready_after_attempt=%s\n' "$attempt"
    break
  fi
  sleep 1
done
```

После loop отдельный exact health check обязан вернуть 200. Если нет — W3
blocked, второй restart запрещён.

## 8. Phase C — post-restart process convergence

### 8.1 API process identity

Повторить service/port evidence из 6.2 и 6.4.

Обязательно:

- API active/running;
- API MainPID non-zero и отличается от `355509`;
- API start timestamp строго новый;
- единственный listener 8000 принадлежит новому canonical API process;
- sidecar/frontend/nginx exact PID и start timestamp не изменились;
- listeners 3003/8001/18092 отсутствуют;
- listener 18091 unchanged;
- production frontend 3002 unchanged.

### 8.2 File/env immutability

Повторить раздел 6.3 и буквально сравнить:

```text
.env SHA/size/mtime/mode/owner: unchanged
systemd unit SHA/size/mtime/mode/owner: unchanged
APP_ENV: development
global V2 flags: unset
```

### 8.3 Health after restart

Exact 200:

```text
GET 127.0.0.1:8000/api/health
GET 127.0.0.1:18091/v1/health
```

Health `git_sha` сам по себе не доказывает загруженный code и не заменяет
следующий real HTTP contract proof.

## 9. Phase D — real HTTP control and preview proof

Создать новую dev session после restart. Cookie держать только в памяти.

Для одного session и даты `2026-07-08` выполнить последовательно:

1. control request с local transport headers, но без marker;
2. preview request с теми же headers плюс exact marker;
3. control request повторно;
4. preview request повторно.

Exact marker:

```text
X-SolarSage-Preview-Mode: today-v2-real
```

### 9.1 Control invariants — оба вызова

```text
HTTP = 200
meta.payloadVersion = today.v1
meta.frontendPayloadVersion = 1
v2 = null/absent
```

Наличие V2 marker в соседнем request не должно менять global settings или
последующий control response.

### 9.2 Preview invariants — оба вызова

```text
HTTP = 200
meta.payloadVersion = today.v2.1
meta.frontendPayloadVersion = 3
meta.contentVersion = 10
v2 != null
v2.audit.available = true
v2.audit.payloadVersion = meta.payloadVersion
v2.audit.scoringVersion = meta.scoringVersion
v2.audit.calculationVersion = meta.calculationVersion
v2.audit.horizonPipeline.schemaVersion = today-horizon-pipeline-audit.v1
v2.audit.horizonPipeline.status = built
v2.audit.horizonPipeline.reason = selected
v2.audit.horizonPipeline.selectedCount = 3
v2.horizons.schemaVersion = today-horizons.v1
v2.horizons.items[].horizon = [long, medium, fast] exact order
three unique non-empty horizon ids
```

Для каждого horizon:

```text
activationIds non-empty and unique
likelySpheres non-empty
manifestations non-empty
actions.do non-empty
actions.avoid non-empty
actions.validUntil == timing.activeUntil
timing.activeFrom non-empty
timing.activeUntil non-empty
timing.precision in {date, instant}
timing.state in closed enum
timing.rangeLabel/stateLabel/timezone non-empty
techniqueExplanations non-empty
```

Для `medium` и `fast` дополнительно:

```text
timing.exactAt non-empty
timing.peakLabel non-empty
```

Provenance proof без human text:

- horizon `activationIds` — subset реальных `v2.activationEvidence[].id`;
- intro `activationIds` — subset union трёх horizons;
- каждое action/avoid provenance activation id входит в parent horizon;
- каждое technique explanation activation id входит в parent horizon;
- audit/body/meta versions согласованы.

Вывести только compact safe summary, например:

```text
REAL_HTTP_CONTROL_PREVIEW: PASS
control_versions: today.v1 / 1
preview_versions: today.v2.1 / 3 / 10
preview_scoring: <version label>
preview_calculation: <version label>
preview_activation: <version label>
horizon_order: long,medium,fast
horizon_ids_unique: true
horizon_timing: long=<state>/<precision>,medium=<state>/<precision>,fast=<state>/<precision>
horizon_activation_counts: long=<n>,medium=<n>,fast=<n>
horizon_action_counts: long=<do>/<avoid>,medium=<do>/<avoid>,fast=<do>/<avoid>
control_after_preview_still_v1: true
```

Не выводить titles, summaries, actions или другие human copy.

## 10. Phase E — cache separation and privacy-safe journal proof

### 10.1 DB cache separation

Использовать repository venv/settings и SQLAlchemy. Найти пользователя только
по exact `tg_user_id=999999999`, `tg_username=dev_user`, затем rows
`today_payloads_cache` для `2026-07-08`.

Нельзя печатать user UUID, profile hash, payload JSON или полный cache hash.

Из rows в памяти разобрать `payload_json.meta` и подтвердить наличие как минимум
одной coherent row каждой семьи:

```text
V1 row:
  payloadVersion = today.v1
  frontendPayloadVersion = 1
  persisted frontend_payload_version = 1
  persisted scoring_version = meta.scoringVersion

V2 row:
  payloadVersion = today.v2.1
  frontendPayloadVersion = 3
  contentVersion = 10
  v2 present
  persisted frontend_payload_version = 3
  persisted scoring_version = meta.scoringVersion
```

Выбрать latest coherent V1 и V2 row и assert:

```text
cache_key_hash both non-empty
cache_key_hash V1 != cache_key_hash V2
V1 payload_json has no V2 body
V2 payload_json has exact current V2 body/audit/horizons
```

Safe output:

```text
CACHE_SEPARATION: PASS
coherent_v1_rows: <count>
coherent_v2_rows: <count>
cache_keys_non_empty: true
cache_keys_distinct: true
persisted_frontend_versions: 1,3
```

### 10.2 Journal privacy and runtime failures

Читать только journal window начиная непосредственно перед authorized restart.
Не печатать raw journal.

Проверить:

- exact opaque session token текущего proof не встречается;
- `Cookie:`/`Set-Cookie:` raw values не встречаются;
- `grace_session_v2=<value>` не встречается;
- `X-SolarSage-Preview-Mode` и `today-v2-real` не логируются как raw request
  header/value;
- `999999999` и `dev_user` не встречаются;
- birth date/city/coordinates из dev profile не встречаются;
- нет traceback, uncaught exception, `CRITICAL`, bind error, address-in-use;
- нет sidecar request failure/timeout;
- нет split-brain assertion failure;
- нет 5xx для proof calls.

Проверка exact session token должна делаться в том же process, где token ещё
находится в памяти, или через stdin/anonymous pipe. Token запрещено помещать в
argv, env, temp file или callback.

Safe output:

```text
JOURNAL_PRIVACY: PASS
session_token_absent: true
raw_cookie_absent: true
preview_header_absent: true
dev_identity_absent: true
birth_data_absent: true
traceback_critical_absent: true
runtime_5xx_absent: true
```

Строка вида `[Auth] Cookie 'grace_session_v2': present` содержит только
стабильное имя cookie и boolean presence; это не raw cookie data. Она допустима,
если никакого `=<opaque value>` или token нет.

## 11. Final invariants before callback

Повторить:

```bash
git branch --show-current
git rev-parse HEAD
git rev-parse refs/remotes/origin/preview/solarsage-v2-human-first-navigator-ux
git diff --quiet
git diff --cached --quiet
git status --short
ss -ltnp 'sport = :3002 or sport = :3003 or sport = :8000 or sport = :8001 or sport = :18091 or sport = :18092'
systemctl show solarsage-api.service solarsage-sidecar.service solarsage-frontend.service nginx.service \
  --property=Id,ActiveState,SubState,MainPID,ExecMainStartTimestamp --no-pager
```

Final state:

- HEAD/local/origin unchanged `55d9891...`;
- tracked worktree clean, index empty;
- exact same six allowed untracked paths;
- API new PID and active/running;
- sidecar/frontend/nginx unchanged;
- env/unit unchanged;
- one canonical listener 8000;
- 18091/3002 unchanged;
- 3003/8001/18092 absent;
- no manual child process;
- no commit/push;
- S1.W4 not started.

## 12. Exact callback

Success callback:

```text
READY_STAGE_1_W3_RUNTIME_ARCH_REVIEW
branch: preview/solarsage-v2-human-first-navigator-ux
head: 55d98917842bd94700030356da7fa1fc50abe86e
origin: 55d98917842bd94700030356da7fa1fc50abe86e
preflight_security: PASS_ADVERSARIAL_DENY_AND_59
pre_restart_control: PASS_TODAY_V1_FRONTEND_1
manual_api_restarts: EXACTLY_1
api_old_pid: 355509
api_new_pid: <pid>
api_new_start: <timestamp>
api_health: 200
sidecar_health: 200
sidecar_pid_start_unchanged: PASS
frontend_pid_start_unchanged: PASS
nginx_pid_start_unchanged: PASS
env_hash_metadata_unchanged: PASS
unit_hash_metadata_unchanged: PASS
global_v2_flags: UNSET_UNCHANGED
control_real_http: PASS_TODAY_V1_FRONTEND_1
preview_real_http: PASS_TODAY_V2_1_FRONTEND_3_CONTENT_10
control_after_preview: PASS_STILL_V1
horizon_order: long,medium,fast
horizon_pipeline: BUILT_SELECTED_3
timing_contract: PASS
actions_contract: PASS
provenance_contract: PASS
cache_separation: PASS_DISTINCT_V1_V2_KEYS
journal_privacy: PASS
runtime_errors_5xx: ABSENT
tracked_worktree: CLEAN
index: EMPTY
untracked_scope: EXACT_6_ALLOWED
listeners_3003_8001_18092: ABSENT
manual_or_second_api: ABSENT
commit_push: NOT_PERFORMED
stage_1_w4: NOT_STARTED
```

Preflight failure callback:

```text
BLOCKED_STAGE_1_W3_PREFLIGHT
failed_gate: <exact section/gate>
safe_observed: <no secrets/personal data>
api_restart_performed: NO
```

Post-restart failure callback:

```text
BLOCKED_STAGE_1_W3_POST_RESTART
failed_gate: <exact section/gate>
safe_observed: <no secrets/personal data>
manual_api_restarts: EXACTLY_1
second_restart: NOT_PERFORMED
sidecar_frontend_nginx: UNTOUCHED
```

После callback остановиться. Не запускать 3003, не начинать S1.W4, не создавать
evidence doc и не выполнять commit/push. Evidence doc и acceptance checkpoint
будут отдельным решением архитектора после независимого review.
