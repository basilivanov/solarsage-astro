# Stage B4.W3 ТЗ — one-command real preview on 3003 and no-interception E2E

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Базовый SHA: `ae62ad8ced1865cef2b2b1b3a0382d2e06065ce0`
Prerequisite: accepted and pushed B4.W2
Authority: `00_MASTER_TZ.md`, `80_STAGE_B4_FRONTEND_REAL_DATA_PREVIEW_MASTER_TZ.md`, repository `AGENTS.md`
Статус: **AUTHORIZED IMPLEMENTATION WAVE — NO COMMIT / NO PUSH**

## 0. Роль и протокол

Ты кодер. Реализуй только B4.W3 по закрытой архитектуре ниже.

- Не использовать субагентов/делегирование.
- Не принимать новых продуктовых или runtime‑решений.
- Не делать commit/push/git add.
- Не переключать ветку и не трогать `main`.
- Не запускать ручной uvicorn, mock API или второй sidecar.
- Не менять systemd/nginx/env/DB/backend/frontend product behavior.
- По завершении остановить proof‑preview; постоянный review‑preview будет
  отдельно разрешён после architect acceptance.

## 1. Preflight

До изменений выполнить:

~~~bash
git branch --show-current
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git status --short --branch
git diff --cached --name-only
id
ss -ltn '( sport = :3003 or sport = :18092 or sport = :8000 or sport = :18091 )'
systemctl is-active solarsage-api.service solarsage-sidecar.service
curl --fail --silent --output /dev/null --write-out '%{http_code}\n' http://127.0.0.1:8000/api/health
curl --fail --silent --output /dev/null --write-out '%{http_code}\n' http://127.0.0.1:18091/v1/health
~~~

Ожидается:

- exact preview branch;
- local/origin exact base SHA;
- current user `astro`, не root;
- index пуст;
- tracked tree clean;
- `3003` и `18092` свободны;
- `8000` и `18091` слушают canonical systemd services и health `200`;
- только frozen unrelated untracked paths:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

Любой иной diff/listener — blocker. Ничего не убивать и не исправлять вне
allowlist.

## 2. Product/runtime outcome

После implementation одна команда от пользователя `astro`:

~~~bash
pnpm preview:v2:real
~~~

должна поднять только текущий Next dev frontend и напечатать после readiness:

~~~text
http://127.0.0.1:3003/day/2026-07-08?why=1
~~~

Этот URL должен:

1. открываться в обычном пустом браузере;
2. естественно выполнить frontend dev auth через `POST /api/auth/dev`;
3. получить session cookie через существующий Next route;
4. запросить `GET /api/day/2026-07-08` через existing same-origin rewrite;
5. попасть в canonical API `127.0.0.1:8000`;
6. получить real `today.v2.1 / frontend 3 / content 10` payload;
7. отрендерить backend-owned `long / medium / fast` horizons;
8. не использовать `fixture=...`, `page.route`, mock server `18092`, canned
   response, manual auth cookie injection или Telegram HMAC fixture.

Dev fixture URL остаётся существующим reference и не меняется. Real acceptance
URL никогда не содержит `fixture`.

## 3. Exact allowlist

Implementation allowlist:

~~~text
.gitignore
package.json
tsconfig.json
scripts/preview-v2-real.mjs
__tests__/scripts/preview-v2-real.test.ts
e2e/real-v2-preview.spec.ts
e2e/README.md
~~~

Architect-owned document, не редактировать:

~~~text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/97_STAGE_B4_W3_REAL_PREVIEW_NO_INTERCEPTION_E2E_TZ.md
~~~

Запрещены любые другие tracked paths, особенно:

~~~text
next.config.mjs
next-env.d.ts
pnpm-lock.yaml
app/**
components/**
hooks/**
lib/**
packages/contracts/**
apps/api/**
apps/solarsage/**
e2e/mock-visual/**
fixtures/assets/screenshots
systemd/nginx/env
~~~

`next-env.d.ts` может быть временно переписан самим Next во время proof, но
launcher обязан автоматически вернуть exact pre-launch bytes. Он не входит в
final diff.

## 4. Package/config changes

### 4.1 `package.json`

Добавить ровно один script, существующий mock script не менять:

~~~json
"preview:v2:real": "node scripts/preview-v2-real.mjs"
~~~

`preview:v2` остаётся test-only mock launcher. Не переименовывать и не менять
его behavior.

Lockfile не должен измениться: dependencies не добавляются.

### 4.2 `.gitignore`

Добавить отдельный comment и ровно один ignored dist:

~~~text
# Real V2 local preview Next dist
.next-v2-real-preview/
~~~

Не использовать broad `.next-*` pattern: существующие review/build каталоги
должны оставаться явно управляемыми.

### 4.3 `tsconfig.json`

Next 16 автоматически добавляет type globs для custom `distDir`. Чтобы
`pnpm preview:v2:real` не пачкал tracked config, добавить в существующий
`include` рядом с `.next-v2-preview` ровно:

~~~json
".next-v2-real-preview/types/**/*.ts",
".next-v2-real-preview/dev/types/**/*.ts"
~~~

Остальные compiler options/include/exclude/order не менять. Это intentional
tracked config; launcher всё равно snapshot‑ит `tsconfig.json` и считает любое
другое изменение от Next ошибкой.

## 5. Launcher architecture

Новый файл:

~~~text
scripts/preview-v2-real.mjs
~~~

Полный GRACE header/module contract/map обязателен. Нетривиальные exported
helpers получают function contracts. Файл import-safe: `main()` выполняется
только когда script запущен как CLI, а не при dynamic import из Vitest.

### 5.1 Закрытые constants

~~~text
ROOT              repository root, вычисленный от import.meta.url
NEXT_HOST         127.0.0.1
NEXT_PORT         3003
API_HEALTH_URL    http://127.0.0.1:8000/api/health
SIDECAR_HEALTH_URL http://127.0.0.1:18091/v1/health
API_REWRITE_BASE  http://127.0.0.1:8000
NEXT_DIST_DIR     .next-v2-real-preview
ACCEPTED_DATE     2026-07-08
ACCEPTANCE_URL    http://127.0.0.1:3003/day/2026-07-08?why=1
READINESS_URL     http://127.0.0.1:3003/
~~~

Не читать date/host/port/API base из ambient env в этой wave. Один canonical
command должен быть воспроизводимым.

### 5.2 Port preflight

До любых file snapshots/spawn:

- попытаться bind `127.0.0.1:3003` через `node:net`;
- если bind невозможен, завершиться non-zero с понятным сообщением:

~~~text
[preview:v2:real] Port 3003 is already occupied; no process was stopped.
~~~

- не убивать и не перезапускать occupant;
- не считать свободным порт только по `fetch` result;
- listener закрыть до spawn;
- порт `18092` не bind/check/start: real launcher к нему не относится.

### 5.3 Runtime health preflight

До spawn выполнить bounded GET (3–5 seconds each):

~~~text
http://127.0.0.1:8000/api/health
http://127.0.0.1:18091/v1/health
~~~

Требовать HTTP 2xx. Body не печатать. При failure:

~~~text
[preview:v2:real] Canonical API is unavailable on 127.0.0.1:8000; start/check solarsage-api.service.
[preview:v2:real] Canonical sidecar is unavailable on 127.0.0.1:18091; start/check solarsage-sidecar.service.
~~~

Launcher ничего не стартует и не вызывает sudo/systemctl restart.

### 5.4 Child environment

Создать env как copy current process env с принудительной заменой:

~~~text
NODE_ENV=development
NEXT_DIST_DIR=.next-v2-real-preview
DEV_API_REWRITE_BASE_URL=http://127.0.0.1:8000
NEXT_TELEMETRY_DISABLED=1
~~~

Критический invariant: даже если parent env содержит
`DEV_API_REWRITE_BASE_URL=http://127.0.0.1:18092` или любой другой URL, child
получает только canonical `8000`.

Не передавать/создавать fixture flags, demo flags или auth tokens.

### 5.5 Spawn

Spawn без shell interpolation:

~~~text
command: pnpm
args: exec next dev --hostname 127.0.0.1 --port 3003
cwd: ROOT
stdio: inherit
detached process group on POSIX
~~~

Не использовать `nohup`, `&`, manual daemonization, `sudo`, `uvicorn`, Docker
или mock server.

На POSIX child `pnpm` и его Next descendants должны принадлежать отдельной
process group. Shutdown отправляет signal всей group через negative PID; это
нужно, чтобы не остался grandchild `next-server`.

### 5.6 Readiness

После spawn poll `READINESS_URL` с bounded timeout максимум 60 seconds:

- response status `< 500` означает server ready;
- connection errors retry с коротким interval (например 250–500 ms);
- параллельно слушать child exit;
- если child завершился до readiness — fail с его exit code;
- если timeout — terminate process group, дождаться exit, restore tracked
  generated files, exit non-zero.

Только после readiness напечатать:

~~~text
[preview:v2:real] Real API: http://127.0.0.1:8000
[preview:v2:real] http://127.0.0.1:3003/day/2026-07-08?why=1
[preview:v2:real] REAL backend preview; no fixture or mock API.
~~~

Не печатать env, cookies, user/profile data или API body.

### 5.7 Next-generated tracked-file hygiene

Проблема: Next 16 при custom dist переписывает `next-env.d.ts` на import из
active dist. Команда должна работать «без танцев с бубном» и не оставлять git
diff.

До spawn синхронно snapshot exact bytes + mode минимум:

~~~text
next-env.d.ts
tsconfig.json
~~~

После readiness:

1. `tsconfig.json` обязан совпадать с snapshot (required globs уже tracked).
   Если Next всё же изменил его:
   - restore exact snapshot;
   - terminate child group;
   - fail non-zero с sanitized config-drift message.
2. Если `next-env.d.ts` изменён Next:
   - вернуть exact snapshot bytes и mode;
   - продолжить preview;
   - не использовать git checkout/reset/show.
3. Проверить, что оба файла exact snapshot после restore.

На `SIGINT`, `SIGTERM`, child unexpected exit, readiness failure,
uncaught exception и normal process exit повторить guarded restore.

Guarded restore после readiness/shutdown не должен затирать произвольную
пользовательскую правку:

- restore `next-env.d.ts` только если current content равен snapshot либо
  является Next-generated declaration, содержащей exact
  `.next-v2-real-preview/types/routes.d.ts` import;
- если current content отличается и не является этим generated shape — не
  перезаписывать, вывести sanitized warning и завершиться non-zero;
- `tsconfig.json` после успешного startup не перезаписывать при произвольном
  later user edit; initial unexpected Next mutation обрабатывается до URL print.

Не создавать tracked backup files. Временные backup/state files не нужны;
snapshot держится в launcher memory.

### 5.8 Shutdown/no orphan

На first `SIGINT`/`SIGTERM`:

1. пометить shutdown in progress;
2. restore generated tracked file state;
3. отправить `SIGTERM` всей child process group;
4. ждать child exit ограниченно (до 5 seconds);
5. если group ещё жива — отправить `SIGKILL` всей group;
6. дождаться/проверить exit;
7. повторить guarded restore;
8. exit без orphan listener на 3003.

Repeated signals не создают двойной shutdown. Unexpected child exit
propagates non-zero code, если launcher сам не завершался.

## 6. Launcher unit/guard tests

Новый файл:

~~~text
__tests__/scripts/preview-v2-real.test.ts
~~~

Полный GRACE header/contract/map. Использовать import-safe exported helpers,
temporary directories и ephemeral ports; не запускать реальный Next в Vitest.

Минимальная matrix:

1. constants/acceptance URL exact; URL содержит `why=1`, не содержит fixture;
2. child env всегда override ambient mock URL на canonical `8000`;
3. child env sets exact development/dist/telemetry values;
4. free ephemeral port accepted;
5. occupied ephemeral port rejected with clear message and occupant untouched;
6. health helper calls exact API/sidecar URLs and accepts 2xx only;
7. non-2xx/network failure maps to sanitized API/sidecar errors, body не входит;
8. generated `next-env.d.ts` shape restores exact snapshot;
9. arbitrary non-generated next-env edit is not overwritten;
10. unchanged `tsconfig.json` passes; unexpected startup drift restores snapshot
    and returns failure;
11. process-group termination helper uses negative PID on POSIX and has safe
    non-POSIX fallback;
12. launcher source contains no `18092`, mock fixture import, `nohup`, uvicorn
    or `page.route`;
13. `package.json` maps `preview:v2:real` to exact script;
14. `.gitignore` contains exact real dist;
15. `tsconfig.json` contains both exact real dist type globs once.

Tests не должны kill real processes or bind 3003/8000/18091/18092.

## 7. No-interception real E2E

Новый файл:

~~~text
e2e/real-v2-preview.spec.ts
~~~

Полный GRACE header/contract/map. Import `test/expect` directly from
`@playwright/test`, не из `e2e/fixtures.ts`: browser context должен быть empty,
без seeded Telegram cookie/initData.

### 7.1 Абсолютные запреты в spec

В source не должно быть вызовов/механизмов:

~~~text
page.route
context.route
routeFromHAR
browserContext.addCookies
storageState
setupTelegramAuth
applyAuthCookies
generate-telegram-test-initdata
window.Telegram injection
mock-visual imports
fixture query
~~~

Можно использовать только passive `page.on('request'|'response')` и
`waitForResponse`.

### 7.2 Test setup

Один semantic test должен выполняться в обоих Playwright projects:

~~~text
chromium (desktop)
mobile (iPhone 13 / 390px)
~~~

Timeout 120 seconds. До navigation:

- `context.cookies()` exact empty;
- подписаться на request events и собирать только URLs/statuses in memory;
- подписаться/wait на `POST /api/auth/dev` response;
- подписаться/wait на exact `GET /api/day/2026-07-08` response.

Navigation exact:

~~~text
/day/2026-07-08?why=1
~~~

Не посещать home first и не выполнять auth вручную. Normal Grace layout и
`useTelegramAuth` должны сами пройти dev auth.

### 7.3 Network assertions

Доказать:

- `/api/auth/dev` observed, method POST, status 200;
- exact day request observed, status 200;
- acceptance URL query не содержит `fixture`;
- ни один request path не начинается `/api/dev-fixtures/`;
- ни один request URL не имеет port `18092`;
- нет request к mock fixture JSON/files;
- day response JSON parses через generated `TodayPayloadWireSchema` (или exact
  generated runtime schema barrel), не ad-hoc cast;
- exact identity:

~~~text
meta.payloadVersion = today.v2.1
meta.frontendPayloadVersion = 3
meta.contentVersion = 10
~~~

- `v2.horizons` non-null;
- `schemaVersion = today-horizons.v1`;
- item horizon order exact `long, medium, fast`;
- all three item IDs non-empty and unique;
- each item has non-empty activation IDs/actions do/actions avoid;
- do not print/attach raw payload or IDs.

Создать только redacted test attachment/proof:

~~~json
{
  "source": "real-api",
  "fixture": false,
  "versions": {"payload":"today.v2.1","frontend":3,"content":10},
  "horizons": ["long","medium","fast"],
  "authPath": "/api/auth/dev",
  "dayPath": "/api/day/2026-07-08"
}
~~~

Никаких copy/profile/cookie/raw IDs в proof.

### 7.4 DOM assertions

После ready:

~~~text
today-screen data-state=ready
why-expanded visible and expanded
why-horizons data-state=ready data-source=backend-horizons
three why-horizon roots exact long/medium/fast order
no why-horizons-unavailable
no dev-timing-fixture-shell
~~~

Для каждого из трёх horizon cards:

- exact direct technical toggle by card;
- initial `aria-expanded=false`;
- click native button;
- `aria-expanded=true`;
- `aria-controls` resolves one role=region;
- region `data-horizon` exact;
- technical content visible.

### 7.5 Sphere navigation assertion

Выбрать первый реально существующий `why-horizon-sphere`:

1. прочитать его closed `data-sphere-key`;
2. найти exact `concrete-day-advice-row` с тем же key;
3. сохранить initial `data-status`;
4. click chip;
5. доказать row:
   - `data-selected=true`;
   - `aria-expanded=true`;
   - exact same `data-status`;
   - focused (`toBeFocused`);
6. details exists with same `data-sphere-key` and same status;
7. row bounding rect после smooth scroll пересекает viewport;
8. click same chip again and доказать, что row остаётся selected/expanded/focused,
   details остаётся exact key, verdict не меняется.

### 7.6 Screenshots

Для каждого project сохранить и attach через `testInfo.outputPath`:

~~~text
real-v2-preview-<project>-day.png
real-v2-preview-<project>-why.png
real-v2-preview-<project>-network-proof.json
~~~

Screenshots/test-results остаются в ignored `test-results/`, не копируются в
repo и не коммитятся. Day screenshot — current viewport/full page as technically
stable; Why screenshot — exact `why-expanded` locator after three technical
regions opened. Не обновлять visual regression baselines.

## 8. `e2e/README.md`

Добавить отдельный верхний раздел `Real Today V2 preview (3003)` с exact:

~~~bash
systemctl is-active solarsage-api.service solarsage-sidecar.service
pnpm preview:v2:real
~~~

URL:

~~~text
http://127.0.0.1:3003/day/2026-07-08?why=1
~~~

E2E command из второго terminal:

~~~bash
E2E_BASE_URL=http://127.0.0.1:3003 \
pnpm exec playwright test e2e/real-v2-preview.spec.ts \
  --project=chromium --project=mobile
~~~

Явно написать:

- real launcher не стартует backend/sidecar;
- mock `pnpm preview:v2` остаётся отдельным test-only reference;
- real spec не использует route interception;
- stop real launcher через Ctrl+C;
- command автоматически убирает Next-generated tracked config drift.

Удалить/исправить в README только противоречащую canonical правилам инструкцию
про ручной uvicorn. Остальные исторические sections не переписывать целиком.

## 9. Required implementation gates

### 9.1 Static/unit

~~~bash
npx vitest run __tests__/scripts/preview-v2-real.test.ts
pnpm typecheck
git diff --check
~~~

### 9.2 Managed launcher smoke

Запустить `pnpm preview:v2:real` как managed foreground process, не daemon.
Из второго managed shell после readiness:

~~~bash
curl --fail --silent --output /dev/null --write-out '%{http_code}\n' \
  http://127.0.0.1:3003/
curl --fail --silent --output /dev/null --write-out '%{http_code}\n' \
  http://127.0.0.1:3003/api/health
git status --short -- next-env.d.ts tsconfig.json
ss -ltnp '( sport = :3003 or sport = :18092 )'
~~~

Ожидания:

- both HTTP 200;
- tracked config status empty while launcher remains running;
- 3003 слушает Next child tree;
- 18092 не слушает.

### 9.3 Real E2E

Пока managed launcher running:

~~~bash
E2E_BASE_URL=http://127.0.0.1:3003 \
pnpm exec playwright test e2e/real-v2-preview.spec.ts \
  --project=chromium --project=mobile
~~~

Вернуть exact pass count/projects и exact attachment paths. Не использовать
`--update-snapshots`.

### 9.4 Signal/no-orphan proof

После E2E отправить launcher `SIGTERM` (отдельно Ctrl+C не обязателен в
automation), дождаться его exit, затем:

~~~bash
ss -ltnp '( sport = :3003 )'
git status --short -- next-env.d.ts tsconfig.json
test ! -e .next-b4-w3-candidate
~~~

Ожидания: no listener, no tracked config diff.

### 9.5 Full frontend gates

~~~bash
npx vitest run
pnpm typecheck
pnpm guardrails:prod
pnpm guardrails:frontend
NEXT_DIST_DIR=.next-b4-w3-candidate pnpm build
bash scripts/grace/check-markers.sh
git diff --check
~~~

Isolated build cleanup:

- pre-build `next-env.d.ts`/`tsconfig.json` должны быть clean;
- после build удалить только `.next-b4-w3-candidate`;
- exact patch вернуть только Next-generated candidate additions/import;
- не использовать checkout/reset;
- финально оба tracked config files clean except intentional W3 `tsconfig`
  diff relative HEAD;
- `.next-prod`, `.next`, `.next-v2-preview` не трогать.

Accepted GRACE unrelated baseline may remain only:

~~~text
scripts/grace_front_lint.py:588
SyntaxError: from __future__ imports must occur at the beginning of the file
~~~

Не исправлять вне allowlist.

## 10. Final proof before callback

~~~bash
git diff --name-only
git diff --cached --name-only
git status --short --branch
git diff --check
git diff -- package.json .gitignore tsconfig.json
git diff -- next-env.d.ts pnpm-lock.yaml next.config.mjs
git diff -- packages/contracts/_generated.ts packages/contracts/_generated.zod.ts packages/contracts/openapi.json
ss -ltnp '( sport = :3003 or sport = :18092 )'
~~~

Ожидания:

- implementation diff exact 7 allowlisted paths;
- plus architect-owned untracked document `97`;
- index empty;
- `next-env.d.ts`, lockfile, next config, generated contracts clean;
- 3003/18092 free after proof;
- frozen unrelated paths untouched;
- no commit/push;
- main/services/env unchanged.

## 11. Запрещено

- ручной uvicorn/API `8001`/mock API `18092`;
- route interception/HAR/cookie seeding/Telegram injection in real spec;
- fixture query or fixture endpoint in acceptance flow;
- edits to frontend/backend contracts or product components;
- killing an occupied 3003 process;
- broad git add/checkout/reset/clean;
- `nohup`, background orphan, persistent systemd unit for preview;
- screenshots/binaries in repo;
- secrets/raw cookies/profile/payload/copy in logs or proof;
- subagents;
- commit/push/B4 follow-up/main/deploy.

## 12. Callback

~~~text
READY_FOR_ARCH_REVIEW_STAGE_B4_W3
branch: preview/solarsage-v2-human-first-navigator-ux
base_sha: ae62ad8ced1865cef2b2b1b3a0382d2e06065ce0
changed_paths: EXACT_7_IMPLEMENTATION
real_command: pnpm preview:v2:real
acceptance_url: http://127.0.0.1:3003/day/2026-07-08?why=1
launcher_user: astro
launcher_api_target: 127.0.0.1:8000
launcher_sidecar_target: 127.0.0.1:18091
mock_18092: NOT_STARTED_NOT_REQUESTED
dedicated_dist: .next-v2-real-preview
port_guard: PASS_NO_KILL
health_preflight: PASS
tracked_config_clean_while_running: PASS
signal_cleanup_no_orphan: PASS
natural_dev_auth: PASS
empty_browser_context: PASS
route_interception: ZERO
real_day_response: PASS_200
versions: today.v2.1_FRONTEND_3_CONTENT_10
horizon_order: long_medium_fast
backend_dom_source: PASS
technical_disclosures_all_3: PASS
sphere_exact_target_repeat: PASS
mobile_screenshot: <ignored test-results path>
desktop_screenshot: <ignored test-results path>
redacted_network_proofs: <paths>
launcher_unit: <exact summary>
real_e2e: <exact summary>
full_vitest: <exact fresh summary>
typecheck: PASS
prod_guard: PASS
frontend_guard: PASS
isolated_build: PASS
isolated_dist_removed: YES
grace_gate: UNRELATED_BASELINE_ERROR_UNCHANGED
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
