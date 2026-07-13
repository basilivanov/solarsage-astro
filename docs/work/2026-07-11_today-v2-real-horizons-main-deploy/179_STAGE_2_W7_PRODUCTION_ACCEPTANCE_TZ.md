# Stage 2.W7 — production acceptance and final completion proof

Дата: `2026-07-13`

Prerequisite:
successful callback from `178_STAGE_2_W6B_ATOMIC_PRODUCTION_DEPLOY_TZ.md`.

Статус: **AUTHORIZED ONLY AFTER ARCHITECT ACCEPTS W6B DEPLOY CALLBACK**

Работай лично в `tmux astro:0.0`, без subagents/delegation/background coding.

## 1. Goal

Prove the deployed final main SHA, wheel, env and frontend build deliver the
user-approved human-first Today V2 through the public production host with
real Telegram HMAC and no fixture, preview, interception or dev-auth dependency.

Completion requires simultaneously:

- local/origin/remote main equals deployed API git SHA;
- canonical systemd/PID/listener/health topology is correct;
- exact retained wheel is non-editable in API and sidecar;
- V2 flags are true in canonical `.env` and `.env.production` unchanged;
- public real payload is `today.v2.1 / 3 / 10` with exact long/medium/fast,
  timing, actions, spheres and valid provenance;
- natural browser Telegram HMAC succeeds in desktop and mobile without cookie
  seeding, `/api/auth/dev`, `page.route`, HAR, fixture or mock;
- all 12 navigator spheres and public semantic/test contracts render;
- logs, console, privacy and security audits pass;
- full canonical tests/guards pass from deployed main;
- old dist, env backup and exact wheel remain rollback-ready.

Only architect marks the overall goal complete after independent review.

## 2. Absolute restrictions

- no product/source/test/tracked config/docs edit;
- no git add/commit/push/switch/merge/rebase/pull/stash;
- no env, venv, build, service, nginx, DB or Docker mutation;
- no restart/reload/stop unless executing the W6B rollback procedure after a
  proven release regression;
- no manual uvicorn/Next server;
- no 3003/3010/8001/18092;
- no route interception/HAR/mock/fixture/dev auth;
- no raw initData, token, cookie, UUID, Telegram ID, birth/profile data or full
  personal payload in output/artifacts;
- no deletion of W6B release/rollback assets.

Allowed temporary repo path is exactly one production Playwright spec named in
section 6, created/deleted with `apply_patch`. It must be absent at callback.

Persistent acceptance artifacts live only in W6B `$EVIDENCE_DIR` outside Git.

## 3. Entry and deployed-runtime identity

Use exact values from W6B callback:

```text
DEPLOY_SHA
STAMP
RELEASE_ROOT
WHEEL
WHEEL_SHA256
ENV_BACKUP
ROLLBACK_DIST
old/new BUILD_ID SHA
new sidecar/API/frontend PIDs and start timestamps
```

Do not infer paths from a glob when callback gives an exact path.

Run:

```bash
git fetch origin --prune
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git ls-remote --heads origin refs/heads/main
git diff --quiet
git diff --cached --quiet
git status --short --branch

systemctl show \
  solarsage-sidecar.service \
  solarsage-api.service \
  solarsage-frontend.service \
  nginx.service \
  --property=Id,ActiveState,SubState,MainPID,ExecMainStartTimestamp --no-pager

ss -ltnp 'sport = :3002 or sport = :3003 or sport = :3010 or sport = :5433 or sport = :8000 or sport = :8001 or sport = :18091 or sport = :18092'

curl -fsS --max-time 10 http://127.0.0.1:8000/api/health
curl -fsS --max-time 10 http://127.0.0.1:18091/v1/health
curl -fsS --max-time 10 -o /dev/null -w 'frontend=%{http_code}\n' http://127.0.0.1:3002/
curl -fsS --max-time 15 -o /dev/null -w 'public_root=%{http_code}\n' https://dev.astro.vasiliy-ivanov.ru/
curl -fsS --max-time 15 https://dev.astro.vasiliy-ivanov.ru/api/health
```

Require local/origin/remote `main = DEPLOY_SHA`; API local/public health
`git_sha` equals first seven characters of DEPLOY_SHA; exact W6B new PIDs/start;
sidecar/API/frontend/nginx active; one listener per canonical port; DB 5433;
temporary ports absent.

Require current `.next-prod/BUILD_ID` hash equals W6B new build hash and
rollback dist BUILD_ID hash equals W6B old hash.

## 4. Dependency/env/rollback proof

Require exact retained wheel path exists and its SHA/size match W6B callback.

For both venvs require:

- solarsage-contracts version 0.1.0;
- no editable location;
- imported module path under owning `site-packages`;
- `pip check` PASS;
- installed public version/activation identities equal.

Safe env parser may print only occurrences/states. Require canonical `.env`:

```text
SOLARSAGE_V2_ENABLED             exactly one / TRUE
SOLARSAGE_V2_FRONTEND_ENABLED    exactly one / TRUE
SOLARSAGE_V2_DUAL_RUN            zero / default
```

Require `.env` differs from root backup by exactly the two added true lines and
`.env.production` hash equals W6B start hash.

Require ENV_BACKUP root:root 600, ROLLBACK_DIST present/readable, release root
and wheel retained. Do not print env backup.

Public dev-auth denial:

```bash
status=$(curl -sS --max-time 15 -o /dev/null -w '%{http_code}' \
  -X POST https://dev.astro.vasiliy-ivanov.ru/api/auth/dev)
test "$status" = 403
```

This proves public production cannot use local dev auth even though the local
diagnostic boundary remains available only on trusted loopback conditions.

## 5. Direct public Telegram HMAC payload proof

Use API-venv Python and import the existing generator in memory. Never invoke
its CLI or print raw initData. Use synthetic established identity
`999999999 / dev_user`, preserving the existing onboarded test profile.

The script must:

1. `POST https://dev.astro.vasiliy-ivanov.ru/api/auth/telegram` and require 200;
2. keep the returned session cookie memory-only;
3. `GET /api/profile` require 200 without reading it into evidence;
4. `GET /api/day/2026-07-08` require 200;
5. validate body with `app.schemas.today.TodayPayload.model_validate`;
6. require exact wire meta `today.v2.1`, frontend `3`, content `10`;
7. require access `full` with no commercial metadata leakage;
8. require exact horizon order long/medium/fast, unique IDs, nonempty activation
   IDs, actions and likely spheres;
9. require every horizon timing activeFrom/activeUntil/state/stateLabel;
10. require medium/fast exactAt and peakLabel non-null;
11. rely on Pydantic cross-reference validators and additionally record
    `provenance_integrity=true`;
12. recursively assert no fixture/dev-fixture marker/source field;
13. write only structural redacted evidence to:

```text
$EVIDENCE_DIR/production-payload-proof.redacted.json
```

Allowed evidence keys:

```text
source
fixtureDependency
versions
accessState
horizonOrder
horizons[]: horizon,id,activationCount,actionDoCount,actionAvoidCount,
            likelySpheres,timing{activeFrom,activeUntil,exactAtPresent,
            precision,state,peakLabelPresent,timezone}
provenanceIntegrity
```

No human copy/action text/profile/IDs except synthetic horizon IDs and closed
sphere keys. File owner astro:astro mode 640.

Then `POST /api/auth/logout` require 204 and reused cookie `GET /api/profile`
require 401. Print only safe status/version/count booleans.

## 6. Natural production browser HMAC spec

Create exactly this temporary file with `apply_patch`:

```text
e2e/.stage2-w7-production-v2.spec.ts
```

It is operational proof, never committed. Required complete content:

```ts
// ############################################################################
// AI_HEADER: TEMP_STAGE2_W7_PRODUCTION_V2_E2E — natural Telegram HMAC production proof.
// ROLE: Temporary release acceptance test; deleted after execution.
// GRACE_ANCHORS: [PRODUCTION_NETWORK, PRODUCTION_DOM, PRODUCTION_EVIDENCE]
// ############################################################################

// START_MODULE_CONTRACT: M-TEMP-STAGE2-W7-PRODUCTION-E2E
// purpose: Prove public production naturally authenticates with Telegram HMAC
//   and renders backend-owned Today V2 in desktop/mobile without interception.
// owns:
//   - e2e/.stage2-w7-production-v2.spec.ts
// inputs: E2E_BASE_URL, RELEASE_EVIDENCE_DIR, real bot token through generator.
// outputs: strict assertions, redacted JSON evidence, synthetic screenshots.
// dependencies: @playwright/test, generated TodayPayloadWireSchema, Python generator.
// side_effects: creates/revokes synthetic sessions and writes external evidence.
// emitted_logs: none.
// invariants: no cookie seeding, auth/dev, route interception, fixture, mock or raw secret output.
// failure_policy: any auth/network/schema/DOM/console/privacy mismatch fails closed.
// END_MODULE_CONTRACT: M-TEMP-STAGE2-W7-PRODUCTION-E2E

// START_MODULE_MAP: M-TEMP-STAGE2-W7-PRODUCTION-E2E
// public_entrypoints:
//   - production V2 Playwright test
// semantic_blocks:
//   - PRODUCTION_NETWORK
//   - PRODUCTION_DOM
//   - PRODUCTION_EVIDENCE
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEMP-STAGE2-W7-PRODUCTION-E2E

import { execFileSync } from "node:child_process"
import { mkdirSync, writeFileSync } from "node:fs"
import { join } from "node:path"
import { expect, test } from "@playwright/test"
import { TodayPayloadWireSchema } from "../packages/contracts/runtime"

const BASE_URL = process.env.E2E_BASE_URL ?? ""
const EVIDENCE_DIR = process.env.RELEASE_EVIDENCE_DIR ?? ""
const DATE = "2026-07-08"
const DAY_PATH = `/day/${DATE}?why=1`
const HORIZONS = ["long", "medium", "fast"] as const
const STATUSES = new Set(["good", "caution", "avoid", "neutral"])

function generateInitData(): string {
  const stdout = execFileSync(
    "python3",
    [
      "scripts/generate-telegram-test-initdata.py",
      "--user-id=999999999",
      "--username=dev_user",
      "--first-name=Dev",
    ],
    { cwd: process.cwd(), encoding: "utf8", timeout: 10_000 },
  )
  const value = stdout
    .split("\n")
    .map((line) => line.trim())
    .find((line) => line.length > 0 && !line.startsWith("#") && line.includes("="))
  if (!value) throw new Error("HMAC generator returned no parseable initData")
  return value
}

function telegramRuntime(initData: string) {
  ;(window as any).Telegram = {
    WebApp: {
      initData,
      initDataUnsafe: {},
      ready: () => {},
      expand: () => {},
      close: () => {},
      platform: "web",
      version: "9.5",
      colorScheme: "light",
      themeParams: {},
      isExpanded: true,
      viewportHeight: window.innerHeight,
      viewportStableHeight: window.innerHeight,
      headerColor: "#ffffff",
      backgroundColor: "#ffffff",
      MainButton: {
        text: "", isVisible: false, isActive: true, isProgressVisible: false,
        setText: () => {}, onClick: () => {}, offClick: () => {}, show: () => {},
        hide: () => {}, enable: () => {}, disable: () => {}, showProgress: () => {},
        hideProgress: () => {},
      },
      BackButton: {
        isVisible: false, onClick: () => {}, offClick: () => {}, show: () => {}, hide: () => {},
      },
      HapticFeedback: {
        impactOccurred: () => {}, notificationOccurred: () => {}, selectionChanged: () => {},
      },
      onEvent: () => {}, offEvent: () => {}, sendData: () => {},
      switchInlineQuery: () => {}, openLink: () => {}, openTelegramLink: () => {},
      openInvoice: () => {}, showPopup: () => {}, showAlert: () => {},
      showConfirm: () => {},
    },
  }
}

test.use({ browserName: "chromium" })

test("public production naturally authenticates and renders exact V2", async ({ context, page }, testInfo) => {
  test.setTimeout(240_000)
  expect(BASE_URL).toBe("https://dev.astro.vasiliy-ivanov.ru")
  expect(EVIDENCE_DIR.length).toBeGreaterThan(0)
  expect(await context.cookies()).toEqual([])
  mkdirSync(EVIDENCE_DIR, { recursive: true })

  const initData = generateInitData()
  await page.addInitScript(telegramRuntime, initData)
  await page.addInitScript(() => localStorage.setItem("lumen:onboarded", "1"))

  const consoleErrors: string[] = []
  const pageErrors: string[] = []
  const apiFailures: string[] = []
  const requests: Array<{ method: string; path: string; status?: number }> = []

  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push("console-error")
  })
  page.on("pageerror", () => pageErrors.push("page-error"))
  page.on("requestfailed", (request) => {
    const url = new URL(request.url())
    if (url.pathname.startsWith("/api/")) apiFailures.push(url.pathname)
  })
  page.on("request", (request) => {
    const url = new URL(request.url())
    if (url.origin === BASE_URL && url.pathname.startsWith("/api/")) {
      requests.push({ method: request.method(), path: url.pathname })
    }
  })
  page.on("response", (response) => {
    const url = new URL(response.url())
    if (url.origin === BASE_URL && url.pathname.startsWith("/api/")) {
      const row = [...requests].reverse().find(
        (item) => item.path === url.pathname && item.status === undefined,
      )
      if (row) row.status = response.status()
    }
  })

  const authPromise = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/auth/telegram"
      && response.request().method() === "POST",
    { timeout: 120_000 },
  )
  const dayPromise = page.waitForResponse(
    (response) => new URL(response.url()).pathname === `/api/day/${DATE}`
      && response.request().method() === "GET"
      && response.status() === 200,
    { timeout: 180_000 },
  )

  await page.goto(DAY_PATH, { waitUntil: "domcontentloaded", timeout: 60_000 })
  const [authResponse, dayResponse] = await Promise.all([authPromise, dayPromise])
  expect(authResponse.status()).toBe(200)
  expect(dayResponse.status()).toBe(200)

  const payload = TodayPayloadWireSchema.parse(await dayResponse.json())
  const horizons = payload.v2?.horizons
  expect(payload.meta.payloadVersion).toBe("today.v2.1")
  expect(payload.meta.frontendPayloadVersion).toBe(3)
  expect(payload.meta.contentVersion).toBe(10)
  expect(payload.access.state).toBe("full")
  if (!horizons) throw new Error("Production backend horizons are required")
  expect(horizons.items.map((item) => item.horizon)).toEqual(HORIZONS)
  for (const item of horizons.items) {
    expect(item.activationIds.length).toBeGreaterThan(0)
    expect(item.actions.do.length).toBeGreaterThan(0)
    expect(item.actions.avoid.length).toBeGreaterThan(0)
    expect(item.timing.activeFrom.length).toBeGreaterThan(0)
    expect(item.timing.activeUntil.length).toBeGreaterThan(0)
    if (item.horizon !== "long") expect(item.timing.exactAt).toBeTruthy()
  }

  await expect(page.getByTestId("today-screen")).toHaveAttribute("data-state", "ready")
  await expect(page.getByTestId("error-boundary")).toHaveCount(0)
  await expect(page.getByTestId("why-horizons"))
    .toHaveAttribute("data-source", "backend-horizons")
  await expect(page.getByTestId("why-horizon")).toHaveCount(3)
  await expect(page.getByTestId("why-horizons-unavailable")).toHaveCount(0)
  await expect(page.getByTestId("dev-timing-fixture-shell")).toHaveCount(0)
  await expect(page.locator('script[src*="/_vercel/insights/"]')).toHaveCount(0)

  const cards = page.getByTestId("why-horizon")
  for (let index = 0; index < HORIZONS.length; index += 1) {
    const card = cards.nth(index)
    await expect(card).toHaveAttribute("data-horizon", HORIZONS[index])
    const toggle = card.getByTestId("why-horizon-technical-toggle")
    await toggle.click()
    await expect(toggle).toHaveAttribute("aria-expanded", "true")
    await expect(card.getByTestId("why-horizon-technical-content")).toBeVisible()
  }

  const sphereRows = page.getByTestId("concrete-day-advice-row")
  await expect(sphereRows).toHaveCount(12)
  for (let index = 0; index < 12; index += 1) {
    const status = await sphereRows.nth(index).getAttribute("data-status")
    expect(status && STATUSES.has(status)).toBe(true)
  }

  const firstSphere = page.getByTestId("why-horizon-sphere").first()
  await expect(firstSphere).toBeVisible()
  await firstSphere.click()
  const selectedKey = await firstSphere.getAttribute("data-sphere-key")
  expect(selectedKey).toBeTruthy()
  const selectedRow = page.locator(
    `[data-testid="concrete-day-advice-row"][data-sphere-key="${selectedKey}"]`,
  )
  await expect(selectedRow).toHaveAttribute("data-selected", "true")
  await expect(selectedRow).toHaveAttribute("aria-expanded", "true")
  await expect(selectedRow).toBeFocused()
  await expect(selectedRow).toBeInViewport({ ratio: 0.5 })

  const currentUrl = new URL(page.url())
  expect(currentUrl.pathname).toBe(`/day/${DATE}`)
  expect(currentUrl.searchParams.get("why")).toBe("1")
  expect(currentUrl.searchParams.has("fixture")).toBe(false)
  expect(requests.some((row) => row.path === "/api/auth/dev")).toBe(false)
  expect(requests.some((row) => row.path.includes("dev-fixtures"))).toBe(false)
  expect(requests.some((row) => row.path.includes("fixture"))).toBe(false)
  expect(apiFailures).toEqual([])
  expect(consoleErrors).toEqual([])
  expect(pageErrors).toEqual([])

  const project = testInfo.project.name
  const safeRequests = requests.map(({ method, path, status }) => ({ method, path, status }))
  const proof = {
    project,
    source: "public-production",
    naturalTelegramAuth: true,
    cookieSeeded: false,
    authDev: false,
    fixture: false,
    interception: false,
    versions: {
      payload: payload.meta.payloadVersion,
      frontend: payload.meta.frontendPayloadVersion,
      content: payload.meta.contentVersion,
    },
    horizons: horizons.items.map((item) => item.horizon),
    sphereRows: 12,
    consoleErrors: 0,
    pageErrors: 0,
    apiFailures: 0,
    requests: safeRequests,
  }
  const networkPath = join(EVIDENCE_DIR, `production-${project}-network.redacted.json`)
  writeFileSync(networkPath, `${JSON.stringify(proof, null, 2)}\n`, { mode: 0o640 })
  await testInfo.attach(`production-${project}-network.redacted.json`, {
    body: JSON.stringify(proof, null, 2),
    contentType: "application/json",
  })

  await page.screenshot({
    path: join(EVIDENCE_DIR, `production-${project}-day.png`),
    fullPage: true,
  })
  await page.getByTestId("why-expanded").screenshot({
    path: join(EVIDENCE_DIR, `production-${project}-why.png`),
  })

  const logoutStatus = await page.evaluate(async () => {
    const response = await fetch("/api/auth/logout", { method: "POST" })
    return response.status
  })
  expect(logoutStatus).toBe(204)
})
```

Before running, static-scan this temporary file and require zero matches for:

```text
page.route
context.route
routeFromHAR
addCookies
storageState
/api/auth/dev request construction
fixture=
18092
```

The string assertion for `/api/auth/dev` is allowed; no request construction.
Classify the scan structurally, not with a naive zero-string check for that one
assertion.

Run exactly:

```bash
E2E_BASE_URL=https://dev.astro.vasiliy-ivanov.ru \
RELEASE_EVIDENCE_DIR="$EVIDENCE_DIR" \
E2E_WORKERS=1 \
pnpm exec playwright test e2e/.stage2-w7-production-v2.spec.ts \
  --project=chromium \
  --project=mobile
```

Require exact `2 PASS`, no retries, six external image artifacts (day/why for
two projects = four PNGs) plus two network JSONs, all mode 640. Combined with
payload proof: seven safe artifacts total.

Delete the temporary spec with `apply_patch` immediately after result, whether
pass or fail. Prove it absent and tracked/index clean.

## 7. Full deployed-main canonical gate matrix

Run from exact deployed main:

```bash
pnpm contracts:generate
git diff --exit-code -- \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts
pnpm contracts:check
pnpm contracts:compat
pnpm contracts:fixture:check
PYTHONPATH=packages/py-contracts \
  apps/api/.venv/bin/python -m pytest packages/py-contracts/tests/ -q

npx vitest run
pnpm typecheck
pnpm guardrails:prod
pnpm guardrails:contracts
pnpm guardrails:frontend
pnpm guardrails:secrets

PYTHONPATH=apps/api \
  apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
PYTHONPATH=apps/solarsage \
  apps/solarsage/venv/bin/python -m pytest apps/solarsage/tests/ -q
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_preview_transport.py \
  apps/api/tests/test_today_preview_access.py \
  apps/api/tests/test_today_selection_context.py \
  apps/api/tests/test_today_cache_v2_key.py \
  -q
apps/api/.venv/bin/python -m pip check
apps/solarsage/venv/bin/python -m pip check
```

Require exact accepted counts: contracts 110, compat 16/0, pycontracts 44,
Vitest 97/1067, API 1406/4, sidecar 201, preview security 163, all guards/pip
green. Contract generation leaves zero tracked diff.

## 8. Logs, privacy and security audit

Collect sidecar/API/frontend journal text only into root/private `/tmp` files
from W6B service start timestamps through completion. Do not paste raw logs.

Automated safe counts must require:

```text
traceback/critical/startup failure/unhandled exception   0
HTTP 5xx                                                  0
repeated restart loop                                     0
raw tgWebAppData/query_id/hash/initData                    0
raw Cookie/Set-Cookie/session value                        0
bot token/database URL/API key                             0
birth date/time/city/lat/lon                               0
synthetic Telegram numeric ID in logs                      0
```

Expected logout/revoked 401 is allowed exactly by acceptance flow; public
`/api/auth/dev` 403 is expected. Record counts, not lines.

Inspect browser results: console/page/API failures zero, no auth/dev, fixture,
mock or 18092 request. Ensure evidence JSON contains only allowlisted structural
keys and screenshots are synthetic-user evidence stored outside Git.

## 9. Final runtime/ref/build/rollback audit

Repeat:

- local/origin/remote main equality to DEPLOY_SHA;
- API local/public git SHA equality;
- exact service PIDs/start from W6B and active states;
- one listener each 18091/8000/3002, DB 5433;
- 3003/3010/8001/18092 absent;
- flags true/true and `.env.production` unchanged;
- same non-editable retained wheel in both venvs;
- current `.next-prod` new BUILD_ID;
- rollback dist old BUILD_ID;
- ENV_BACKUP root600 and wheel retained;
- release evidence seven exact files with safe permissions;
- tracked worktree/index clean; only frozen five untracked;
- no temporary production spec/process/window.

Do not delete rollback assets after success. Cleanup is a later explicit ops
decision after an observation window.

## 10. Rollback trigger

If direct payload or either browser project proves a release regression (5xx,
invalid V2, render failure, auth failure caused by release, privacy leak), stop
remaining acceptance and execute the exact automatic rollback section 13 from
W6B. Return blocked with rollback health proof. A test-harness-only defect that
does not contradict direct runtime evidence must still stop for architect
classification; do not edit product or weaken assertions.

## 11. Final callback and stop

```text
READY_STAGE_2_W7_PRODUCTION_ACCEPTANCE_REVIEW
deploy_sha: <40-char main SHA>
merge_sha: 57230b7b8eedb772a936726f6abf97427bc37f6a
main_local_origin_remote: EQUAL
api_git_sha_local_public: MATCH_DEPLOY_SHA
wheel_path: <absolute>
wheel_sha256: <sha256>
wheel_installs: API_SIDECAR_NONEDITABLE_SAME
flags: ENABLED_TRUE_FRONTEND_TRUE_DUAL_DEFAULT
services: SIDECAR_API_FRONTEND_NGINX_ACTIVE
ports: 18091_8000_3002_5433_PRESENT_3003_3010_8001_18092_ABSENT
health: LOCAL_PUBLIC_ALL_PASS
public_dev_auth: 403_DENIED
direct_hmac: AUTH_200_PROFILE_200_DAY_200_LOGOUT_204_REVOKED_401
payload_versions: TODAY_V2_1_FRONTEND_3_CONTENT_10
horizons: LONG_MEDIUM_FAST
timing: ALL_RANGES_MEDIUM_FAST_PEAKS_PASS
actions_spheres: PASS
provenance_integrity: PASS
fixture_dependency: FALSE
browser_e2e: 2_PASS_CHROMIUM_MOBILE_NATURAL_HMAC
browser_cookie_seed: ZERO
browser_auth_dev: ZERO
browser_interception_fixture_mock: ZERO
navigator: 12_SPHERES_STATUS_FOCUS_PASS
console_page_api_errors: ZERO
evidence_artifacts: 7_SAFE_EXTERNAL
contracts: GENERATE_0_CHECK_110_COMPAT_16_0_FIXTURE_PYCONTRACTS_44
frontend_tests: VITEST_97_1067_TYPECHECK_GUARDS_PASS
backend_tests: API_1406_4_SIDECAR_201_SECURITY_163_PIP_PASS
journal_runtime_5xx_startup_errors: ZERO
privacy_audit: PASS
tracked_worktree: CLEAN
index: EMPTY
frozen_untracked: PRESERVED
rollback_env: RETAINED_ROOT600
rollback_dist: RETAINED_OLD_BUILD
rollback_wheel: RETAINED
goal_completion: AWAITING_ARCHITECT_INDEPENDENT_REVIEW
```

Then stop. Architect performs final independent audit and alone marks the goal
complete.
