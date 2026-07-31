// ############################################################################
// AI_HEADER: MODULE_E2E_ACCEPTANCE_COHORT_SPEC — P8-C seeder self-check.
// ROLE: Exercise the real auth/profile/referral/day APIs and verify the
//       cleanup ledger without browser route interception.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-ACCEPTANCE-COHORT-SPEC
// purpose: Verify the P8-C acceptance cohort helper against a live runtime.
// owns:
//   - e2e/acceptance-cohort.spec.ts
// inputs: E2E_BASE_URL, optional E2E_API_BASE_URL and E2E_CREATED_USERS_FILE,
//   live Telegram HMAC/API runtime.
// outputs: Playwright assertions for three profile modes, three access states,
//   and three cleanup-ledger entries.
// dependencies: @playwright/test, e2e/acceptance-cohort.ts, public API routes.
// side_effects: creates three real E2E users and one public referral claim;
//   cleanup is delegated to the existing JSONL ledger workflow.
// emitted_logs: none.
// invariants:
//   - skipped when E2E_BASE_URL is absent;
//   - runs once under the chromium project because this is API-only and has no
//     viewport/browser contract;
//   - never uses page.route, fixtures, test-only routes, or SQL.
// failure_policy: any non-2xx response, malformed envelope, mode mismatch,
//   access mismatch, or missing ledger entry fails the test.
// END_MODULE_CONTRACT: M-E2E-ACCEPTANCE-COHORT-SPEC

// START_MODULE_MAP: M-E2E-ACCEPTANCE-COHORT-SPEC
// public_entrypoints:
//   - Playwright test runner
// semantic_blocks:
//   - PROFILE_PROOF: authenticated GET /api/profile for each mode
//   - ACCESS_PROOF: exact user full/preview/locked day matrix
//   - CLEANUP_LEDGER_PROOF: JSONL tail contains all created Telegram IDs
// owned_tests:
//   - self
// END_MODULE_MAP: M-E2E-ACCEPTANCE-COHORT-SPEC

import { readFileSync } from "node:fs"

import { expect, request, test, type APIRequestContext } from "@playwright/test"

import {
  accessDatesFor,
  seedAcceptanceCohort,
  type AcceptanceCohort,
  type CohortUser,
} from "./acceptance-cohort"

const CREATED_USERS_FILE =
  process.env.E2E_CREATED_USERS_FILE || "/tmp/solarsage-e2e-created-users.jsonl"
const SESSION_COOKIE_NAME = "grace_session_v2"

type JsonObject = Record<string, unknown>

function apiBaseURL(baseURL: string): string {
  return (process.env.E2E_API_BASE_URL || baseURL).replace(/\/+$/, "")
}

function endpointURL(baseURL: string, path: string): string {
  return `${baseURL}${path.startsWith("/") ? path : `/${path}`}`
}

function asObject(value: unknown, operation: string): JsonObject {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${operation} returned a non-object JSON response`)
  }
  return value as JsonObject
}

async function authenticatedJSON(
  baseURL: string,
  user: CohortUser,
  path: string,
): Promise<JsonObject> {
  const authContext: APIRequestContext = await request.newContext()
  let context: APIRequestContext | undefined
  try {
    const authResponse = await authContext.post(endpointURL(baseURL, "/api/auth/telegram"), {
      data: { initData: user.initDataRaw },
      headers: { "Content-Type": "application/json" },
    })
    if (!authResponse.ok()) {
      throw new Error(`POST /api/auth/telegram failed with HTTP ${authResponse.status()}`)
    }

    const setCookie = authResponse.headers()["set-cookie"] || ""
    const cookieValue = setCookie.match(new RegExp(`${SESSION_COOKIE_NAME}=([^;]+)`))?.[1]
    if (!cookieValue) {
      throw new Error(`POST /api/auth/telegram did not return ${SESSION_COOKIE_NAME}`)
    }
    context = await request.newContext({
      extraHTTPHeaders: { Cookie: `${SESSION_COOKIE_NAME}=${cookieValue}` },
    })

    const response = await context.get(endpointURL(baseURL, path), {
      headers: { Accept: "application/json" },
    })
    if (!response.ok()) {
      throw new Error(`GET ${path} failed with HTTP ${response.status()}`)
    }
    return asObject(await response.json(), `GET ${path}`)
  } finally {
    await context?.dispose()
    await authContext.dispose()
  }
}

function accessState(payload: JsonObject, date: string): string {
  const access = asObject(payload.access, `GET /api/day/${date}.access`)
  if (typeof access.state !== "string") {
    throw new Error(`GET /api/day/${date} returned no access.state`)
  }
  return access.state
}

function readLedgerTail(cohort: AcceptanceCohort): JsonObject[] {
  const content = readFileSync(CREATED_USERS_FILE, "utf-8")
  const records = content
    .split("\n")
    .filter((line) => line.trim().length > 0)
    .map((line) => asObject(JSON.parse(line), "E2E cleanup ledger"))
  return records.slice(-cohort.users.length)
}

test.describe("P8-C acceptance cohort — real API self-check", () => {
  test("seeds three modes and proves full/preview/locked access", async ({ baseURL }, testInfo) => {
    test.setTimeout(240_000)
    test.skip(!process.env.E2E_BASE_URL, "E2E_BASE_URL is required for the live cohort self-check")
    test.skip(testInfo.project.name !== "chromium", "API-only self-check runs once")

    const targetBaseURL = baseURL || process.env.E2E_BASE_URL
    if (!targetBaseURL) throw new Error("Playwright did not provide E2E_BASE_URL")

    const cohort = await seedAcceptanceCohort(targetBaseURL)
    expect(cohort.users).toHaveLength(3)
    expect(cohort.users.map((user) => user.label)).toEqual(["exact", "bucket", "unknown"])
    expect(cohort.heroDate).toBe("2026-07-08")
    expect(cohort.quietDate).toBe("2026-07-12")

    // START_BLOCK: PROFILE_PROOF
    for (const user of cohort.users) {
      const profile = await authenticatedJSON(apiBaseURL(cohort.baseURL), user, "/api/profile")
      expect(profile.userId).toBe(user.userId)
      const birth = asObject(profile.birth, `GET /api/profile (${user.label})`)
      expect(birth.birthTimeMode).toBe(user.label)

      if (user.label === "exact") expect(birth.birthTime).toBe("14:30:00")
      if (user.label === "bucket") expect(birth.birthTimeBucket).toBe("morning")
      if (user.label === "unknown") {
        expect(birth.birthTime).toBeNull()
        expect(birth.birthTimeBucket).toBeNull()
      }
    }
    // END_BLOCK: PROFILE_PROOF

    // START_BLOCK: ACCESS_PROOF
    const exactUser = cohort.users[0]
    if (!exactUser) throw new Error("Acceptance cohort did not contain exact user")
    const today = new Date().toISOString().slice(0, 10)
    const dates = accessDatesFor(exactUser, today)
    const apiURL = apiBaseURL(cohort.baseURL)

    const fullPayload = await authenticatedJSON(apiURL, exactUser, `/api/day/${dates.fullDate}`)
    const previewPayload = await authenticatedJSON(apiURL, exactUser, `/api/day/${dates.previewDate}`)
    const lockedPayload = await authenticatedJSON(apiURL, exactUser, `/api/day/${dates.lockedDate}`)

    expect(accessState(fullPayload, dates.fullDate)).toBe("full")
    expect(accessState(previewPayload, dates.previewDate)).toBe("preview")
    expect(accessState(lockedPayload, dates.lockedDate)).toBe("locked")
    // END_BLOCK: ACCESS_PROOF

    // START_BLOCK: CLEANUP_LEDGER_PROOF
    const ledgerTail = readLedgerTail(cohort)
    const ledgerIds = ledgerTail.map((record) => record.tg_user_id)
    expect(ledgerIds).toEqual(
      expect.arrayContaining(cohort.users.map((user) => user.telegramUserId)),
    )
    // END_BLOCK: CLEANUP_LEDGER_PROOF
  })
})
