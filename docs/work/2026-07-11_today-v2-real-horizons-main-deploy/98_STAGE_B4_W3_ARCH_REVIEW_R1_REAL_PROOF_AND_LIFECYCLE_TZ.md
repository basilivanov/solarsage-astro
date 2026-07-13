# Stage B4.W3 architectural review R1 — real proof, safe restore and complete E2E

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Базовый SHA: `ae62ad8ced1865cef2b2b1b3a0382d2e06065ce0`
Предыдущее ТЗ: `97_STAGE_B4_W3_REAL_PREVIEW_NO_INTERCEPTION_E2E_TZ.md`
Статус: **REVIEW CORRECTIONS — NO COMMIT / NO PUSH**

## 1. Решение review

Не принято.

Принято как направление:

- exact package script;
- dedicated ignored dist;
- intentional tsconfig real-dist globs;
- canonical API/sidecar constants;
- separate real E2E file;
- full Vitest 97 files / 1034 tests и typecheck evidence.

Но callback не может заявлять готовность, потому что:

1. `real_e2e: NOT_RUN` — главное доказательство W3 отсутствует.
2. Managed real launcher smoke не завершён; ранний smoke падал из-за неверного
   root и после fix не показан.
3. `tracked_config_clean_while_running` заявлен только по unit source checks,
   а не по реально работающему Next.
4. `signal_cleanup_no_orphan` не доказан реальным listener/process proof.
5. Unit file содержит 11 tests вместо обязательной matrix и не тестирует
   restore/lifecycle helpers по behavior.
6. E2E не валидирует response generated schema и не выполняет значительную
   часть DOM/screenshot/network contract.
7. Launcher restore может затереть пользовательскую правку `tsconfig.json`.

Production config/runtime не менять. Исправить только ниже.

## 2. R1 allowlist

Менять можно ровно четыре implementation paths:

~~~text
scripts/preview-v2-real.mjs
__tests__/scripts/preview-v2-real.test.ts
e2e/real-v2-preview.spec.ts
e2e/README.md
~~~

Оставить без изменений уже принятые W3 config paths:

~~~text
.gitignore
package.json
tsconfig.json
~~~

Architect documents `97` и `98` не редактировать. Всё остальное запрещено.

## 3. Launcher defects and exact corrections

### 3.1 Port guard must bind, not connect

Текущий `checkPort()` использует `createConnection`, что не является требуемой
bind‑проверкой и имеет иной контракт.

Заменить на `node:net.createServer()`:

- `server.once('error', ...)` -> occupied/unavailable;
- `server.once('listening', ...)` -> close and return free;
- `server.listen({host, port, exclusive:true})`;
- server всегда закрывается;
- `3003` occupant никогда не kill‑ится.

Helper может оставаться generic для unit ephemeral port.

### 3.2 No shell interpolation for chmod

Удалить `execSync` полностью. Использовать `chmodSync` из `node:fs` и
permission bits `mode & 0o777`. Никаких shell commands/backticks внутри
launcher.

### 3.3 Restore ownership must be split by file

Текущий generic:

~~~js
const generated = cur.includes('.next-v2-real-preview')
~~~

опасен: tracked `tsconfig.json` намеренно всегда содержит эту строку, поэтому
любая пользовательская правка во время preview будет ошибочно признана
generated и затёрта на shutdown.

Закрыть два разных контракта.

#### `next-env.d.ts`

Экспортировать testable helper, принимающий snapshot/current:

~~~text
classify/restore result = unchanged | restored_generated | unsafe_user_edit
~~~

Generated shape допускается только если:

- current состоит из normal Next declaration lines;
- route import exact `.next-v2-real-preview/types/routes.d.ts`;
- отсутствуют любые дополнительные arbitrary lines;
- либо current exact snapshot.

Только exact generated shape можно заменить snapshot. Любая другая разница —
`unsafe_user_edit`, не overwrite, launcher завершает shutdown/failure non-zero.

#### `tsconfig.json`

- Snapshot до spawn.
- Единственная автоматическая проверка после readiness, до URL print.
- Если current отличается от snapshot в startup window:
  - restore exact snapshot;
  - terminate child group;
  - fail non-zero.
- После успешной startup verification generic shutdown restore **никогда** не
  переписывает `tsconfig.json`.
- Если пользователь меняет tsconfig после URL print, launcher оставляет его
  как есть.

Удалить generic `restoreAll` semantics, которые смешивают два файла.

### 3.4 Export actual behavior helpers

Для unit behavioral proof экспортировать минимум:

~~~text
buildEnv(baseEnv = process.env)
checkPort(host, port)
checkHealth(url, fetchImpl = fetch)
classifyNextEnv(...)/restoreGeneratedNextEnv(...)
verifyStartupTsconfig(...)
terminateProcessGroup(pid, signal, killImpl = process.kill)
waitForReady(...)
~~~

Названия могут отличаться, ownership должен быть таким же. Tests не должны
читать source вместо проверки behavior там, где helper доступен.

### 3.5 Lifecycle must await termination

Текущий signal handler запускает interval, но не владеет complete awaited
shutdown result и не фиксирует final exit semantics.

Сделать idempotent `shutdown(reason, desiredExitCode)` returning one shared
Promise:

1. guarded next-env restore;
2. `SIGTERM` entire POSIX group;
3. await child `exit` или timeout <=5s;
4. при timeout `SIGKILL` entire group;
5. await final exit bounded;
6. guarded next-env restore again;
7. remove listeners/timers;
8. set `process.exitCode`, не делать преждевременный `process.exit()` до cleanup.

Handle:

~~~text
SIGINT
SIGTERM
readiness timeout/failure
unexpected child exit
main rejection
uncaughtException
unhandledRejection
normal exit synchronous final next-env guard
~~~

Repeated signals reuse same shutdown Promise. Child unexpected exit after
readiness propagates non-zero (null signal code maps 1), except explicit normal
user shutdown.

`detached`/negative PID используется только POSIX. Non-POSIX fallback calls
positive PID. Tests use injected kill function; real processes не трогают.

### 3.6 GRACE exactness

Launcher:

- canonical multi-line `owns`, `inputs`, `outputs`, `dependencies`,
  `side_effects`, `emitted_logs`, `invariants`, `failure_policy`;
- module map uses `public_entrypoints` and `semantic_blocks`;
- every exported non-trivial helper and `main/shutdown` has function contract;
- emitted logs list exact console lifecycle labels or state `none` consistently,
  not `none` while contract claims console output without names;
- no second informal header before GRACE header.

Unit/E2E files also use canonical maps/lists, not single-line pseudo fields.

## 4. Unit matrix must prove behavior

`__tests__/scripts/preview-v2-real.test.ts` minimum 15 real tests:

1. exact acceptance URL;
2. `buildEnv({DEV_API_REWRITE_BASE_URL:'http://127.0.0.1:18092'})` -> exact 8000;
3. exact NODE_ENV/dist/telemetry values;
4. bind guard free ephemeral port;
5. bind guard occupied ephemeral port and occupant remains alive;
6. health accepts 2xx with injected/local fetch;
7. health rejects non-2xx without exposing body;
8. health rejects network error bounded;
9. exact generated next-env is restored byte-for-byte/mode-safe;
10. arbitrary next-env user edit is classified unsafe and not overwritten;
11. startup tsconfig exact passes untouched;
12. startup tsconfig drift restores exact snapshot and reports failure;
13. process group helper sends negative PID on POSIX through injected kill;
14. package/gitignore/tsconfig exact configuration once each;
15. launcher source guard: no functional `18092`, mock import, uvicorn, nohup,
    shell exec/interpolation or route interception.

Можно иметь больше 15. Удалить неиспользуемые imports/temp-dir scaffolding.
Все ephemeral HTTP servers закрывать через `try/finally`, чтобы failing
assertion не оставлял open handles/timeouts.

Не использовать `any`, unsafe casts, suppression или real fixed ports.

## 5. E2E corrections

### 5.1 Preserve project viewports

Удалить:

~~~ts
test.use({ viewport: { width: 390, height: 844 } })
~~~

`chromium` должен остаться desktop device из config, `mobile` — iPhone 13.
Иначе обе screenshots являются mobile и callback ложен.

### 5.2 Generated response validation

Import:

~~~ts
import { TodayPayloadWireSchema } from '../packages/contracts/runtime'
~~~

Day JSON сначала проходит `TodayPayloadWireSchema.parse`. Только typed result
используется дальше.

Удалить:

~~~text
(i: any)
as string
~~~

Добавить explicit narrowing helper для nullable attributes. Assert:

- item IDs all non-empty and unique;
- horizon order exact;
- activation/do/avoid non-empty;
- `guidanceMode=deterministic`;
- response request method exact GET;
- acceptance pathname/query exact and no fixture param.

### 5.3 Passive network proof

Use `page.on('request')` для URLs/methods и `waitForResponse` для statuses.
Никаких interception calls даже в helper.

Proof attachment:

- write project-specific filename;
- `testInfo.attach` JSON;
- no raw payload/IDs/copy/cookies.

### 5.4 DOM completeness

Добавить:

- `why-expanded-toggle aria-expanded=true`;
- no `dev-timing-fixture-shell`;
- each technical region visible;
- each region `aria-labelledby` exact toggle id;
- exact `data-horizon` toggle and region;
- safe aria-controls narrowing.

Sphere:

- `toBeFocused()` после first click;
- row rect intersects viewport;
- status/details/focus/selected/expanded сохраняются после second click;
- no unsafe selector interpolation: key is generated closed sphere enum from
  parsed payload/DOM and use a locator filter or escaped/evaluated public
  attributes safely.

### 5.5 Screenshots and attachments

Для каждого actual project:

~~~text
real-v2-preview-<project>-day.png
real-v2-preview-<project>-why.png
real-v2-preview-<project>-network-proof.json
~~~

- day screenshot;
- exact Why locator screenshot after all technical regions opened;
- attach both PNGs and JSON through `testInfo.attach`;
- no baseline update;
- output remains ignored.

### 5.6 Navigation wait

Не полагаться на `page.goto(... waitUntil:'networkidle')`: Next dev HMR и
external Telegram SDK can make it flaky. Use `domcontentloaded`, awaited auth/day
responses and stable public DOM readiness.

## 6. README correction

Новый top section оставить. Ниже удалить/заменить manual runtime instructions:

~~~text
cd apps/api ... uvicorn ...
~~~

Canonical instruction:

~~~bash
systemctl is-active solarsage-api.service solarsage-sidecar.service
pnpm preview:v2:real
~~~

Не оставлять contradictory ручной uvicorn совет в том же README.

## 7. Actual managed proof is mandatory

`real_e2e: NOT_RUN` больше недопустим. Интерактивный coder может использовать
managed shell/background session; отсутствие отдельного terminal не blocker.

### 7.1 Launcher smoke

Запустить exact command, дождаться printed acceptance URL. Пока running:

~~~bash
curl --fail --silent --output /dev/null --write-out '%{http_code}\n' http://127.0.0.1:3003/
curl --fail --silent --output /dev/null --write-out '%{http_code}\n' http://127.0.0.1:3003/api/health
git status --short -- next-env.d.ts tsconfig.json
ss -ltnp '( sport = :3003 or sport = :18092 )'
~~~

Require 200/200, config status empty relative to intended W3 diff, 3003 live,
18092 absent.

### 7.2 Real E2E

~~~bash
E2E_BASE_URL=http://127.0.0.1:3003 \
pnpm exec playwright test e2e/real-v2-preview.spec.ts \
  --project=chromium --project=mobile
~~~

Exact 2 project tests PASS. Return actual attachment paths.

### 7.3 Termination proof

Send SIGTERM to launcher parent, wait for exit, then require:

~~~text
no 3003 listener
no pnpm/next descendants from launcher process group
next-env.d.ts clean
tsconfig contains only intentional W3 diff
18092 absent
~~~

Не оставлять preview running in correction wave.

## 8. Remaining gates

После actual E2E:

~~~bash
npx vitest run __tests__/scripts/preview-v2-real.test.ts
pnpm typecheck
npx vitest run
pnpm guardrails:prod
pnpm guardrails:frontend
NEXT_DIST_DIR=.next-b4-w3-candidate pnpm build
bash scripts/grace/check-markers.sh
git diff --check
~~~

Candidate build cleanup exact как в `97`; no checkout/reset. Не заявлять gate,
если он не запускался. Full Vitest count fresh.

`guardrails:frontend` может выявить baseline; callback обязан вернуть exact
result, не заменять его общим `PASS`.

## 9. Final state

- exact 7 implementation paths + docs `97`,`98`;
- index empty;
- no 3003/18092 listener;
- next-env/lockfile/next config/generated contracts clean;
- isolated candidate removed;
- no commit/push;
- frozen paths untouched.

## 10. Callback

~~~text
READY_FOR_ARCH_REVIEW_STAGE_B4_W3_R1
changed_paths: EXACT_7_IMPLEMENTATION
changed_now: EXACT_4_R1_ALLOWLIST
port_guard: BIND_BASED_PASS
shell_interpolation: ZERO
next_env_restore_behavior: PASS
arbitrary_next_env_edit_preserved: PASS
tsconfig_user_edit_shutdown_preserved: PASS
shutdown_awaited_no_orphan: PASS
launcher_grace: COMPLETE
unit_matrix: <exact count PASS>
actual_launcher_root: /opt/solarsage-astro
actual_http_root: 200
actual_http_api_health: 200
tracked_config_clean_while_running: REAL_PASS
mock_18092: ABSENT
empty_browser_context: PASS
natural_dev_auth: PASS_200
real_day_response: PASS_GET_200
generated_schema_parse: PASS
versions: today.v2.1_FRONTEND_3_CONTENT_10
horizon_order: long_medium_fast
route_interception: ZERO
desktop_project: PASS_<viewport>
mobile_project: PASS_<viewport>
technical_disclosures_all_3: PASS
sphere_exact_target_repeat_focus_status: PASS
desktop_attachments: <3 exact paths>
mobile_attachments: <3 exact paths>
signal_cleanup_no_listener_or_descendants: REAL_PASS
launcher_unit: <exact>
real_e2e: 2_PROJECT_TESTS_PASS
full_vitest: <fresh exact>
typecheck: PASS
prod_guard: <exact>
frontend_guard: <exact>
isolated_build: PASS
isolated_dist_removed: YES
grace_gate: <exact>
git_diff_check: PASS
generated_diff: EMPTY
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
services_env_main: UNCHANGED
next_wave: NOT_STARTED
~~~

После callback остановиться.
