// ############################################################################
// AI_HEADER: MODULE_E2E_ACCEPTANCE_COHORT — real-API P8-C acceptance seeder.
// ROLE: Create exact/bucket/unknown Telegram users, grant a public referral
//       trial between two cohort members, and expose deterministic dates for
//       acceptance checks without test-only routes or database writes.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-ACCEPTANCE-COHORT
// purpose: Seed a small real-API acceptance cohort for Today convergence.
// owns:
//   - e2e/acceptance-cohort.ts
// inputs: frontend baseURL, TELEGRAM_BOT_TOKEN-backed initData generator,
//   E2E_RUN_SALT/GITHUB_RUN_ID, optional E2E_API_BASE_URL.
// outputs: AcceptanceCohort with three users and fixed hero/quiet dates.
// dependencies: @playwright/test APIRequestContext, the existing Telegram
//   initData generator, /api/auth/telegram, /api/profile, and public referral
//   endpoints.
// side_effects: creates users and profiles through public HTTP APIs, creates
//   one public referral claim, appends three JSONL cleanup-ledger records.
// emitted_logs: none.
// invariants:
//   - no route interception, test-only route, or direct SQL write;
//   - every seed uses fresh run-salted Telegram IDs;
//   - exact/bucket/unknown profile modes are validated by the API response;
//   - the full-access grant uses only two of the three created users.
// failure_policy: throws with endpoint/status context on any failed API
//   request or malformed response; never includes initData in an error.
// END_MODULE_CONTRACT: M-E2E-ACCEPTANCE-COHORT

// START_MODULE_MAP: M-E2E-ACCEPTANCE-COHORT
// public_entrypoints:
//   - seedAcceptanceCohort
//   - accessDatesFor
// semantic_blocks:
//   - TELEGRAM_ID_AND_INITDATA: run-salted user identity and HMAC generation
//   - PROFILE_SEED: authenticated profile creation for three birth-time modes
//   - PUBLIC_TRIAL_GRANT: referral claim using the existing public API
//   - ACCESS_DATES: deterministic full/preview/locked date matrix
// owned_tests:
//   - e2e/acceptance-cohort.spec.ts
// END_MODULE_MAP: M-E2E-ACCEPTANCE-COHORT

import { execFileSync } from "node:child_process"
import { appendFileSync } from "node:fs"
import { createHash, randomUUID } from "node:crypto"

import { request, type APIRequestContext, type APIResponse } from "@playwright/test"

const SCRIPT_PATH = "scripts/generate-telegram-test-initdata.py"
const SESSION_COOKIE_NAME = "grace_session_v2"
const CREATED_USERS_FILE =
  process.env.E2E_CREATED_USERS_FILE || "/tmp/solarsage-e2e-created-users.jsonl"
const HERO_DATE = "2026-07-08"
const QUIET_DATE = "2026-07-12"
const COHORT_LABELS = ["exact", "bucket", "unknown"] as const

type CohortLabel = (typeof COHORT_LABELS)[number]
type JsonObject = Record<string, unknown>

export interface CohortUser {
  label: CohortLabel
  telegramUserId: number
  userId: string
  initDataRaw: string
}

export interface AcceptanceCohort {
  baseURL: string
  users: CohortUser[]
  heroDate: string
  quietDate: string
}

// START_BLOCK: TELEGRAM_ID_AND_INITDATA
function normalizeBaseURL(baseURL: string): string {
  const configured = baseURL.trim()
  if (!configured) throw new Error("Acceptance cohort requires a non-empty baseURL")

  const parsed = new URL(configured)
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("Acceptance cohort baseURL must use http or https")
  }
  return configured.replace(/\/+$/, "")
}

function apiBaseURL(baseURL: string): string {
  return normalizeBaseURL(process.env.E2E_API_BASE_URL || baseURL)
}

function generateInitData(userId: number, label: CohortLabel): string {
  const stdout = execFileSync(
    "python3",
    [
      SCRIPT_PATH,
      `--user-id=${userId}`,
      `--username=p8c_${label}_${userId}`,
      `--first-name=P8C-${label}`,
    ],
    {
      encoding: "utf-8",
      cwd: process.cwd(),
      timeout: 5000,
    },
  )

  for (const line of stdout.split("\n")) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith("#")) continue
    if (trimmed.includes("tgWebAppData")) continue
    if (trimmed.includes("=")) return trimmed
  }

  throw new Error(`Failed to parse Telegram initData for cohort label ${label}`)
}

function newTelegramUserId(seedNonce: string, label: CohortLabel): number {
  const runSalt = process.env.E2E_RUN_SALT || process.env.GITHUB_RUN_ID || "local"
  const digest = createHash("sha256")
    .update(`${runSalt}\0p8c-acceptance-cohort\0${seedNonce}\0${label}`)
    .digest()
  const telegramUserId = 1_000_000_000 + (digest.readUInt32BE(0) % 1_000_000_000)

  // Keep the same JSONL shape consumed by scripts/acceptance/cleanup_e2e_users.py
  // and used by e2e/fixtures.ts. The nonce is only part of the test label, not
  // a user attribute or a secret.
  appendFileSync(
    CREATED_USERS_FILE,
    JSON.stringify({
      tg_user_id: telegramUserId,
      test_id: `p8c-acceptance-cohort:${seedNonce}:${label}`,
      run_salt: runSalt,
    }) + "\n",
  )

  return telegramUserId
}

function endpointURL(baseURL: string, path: string): string {
  return `${baseURL}${path.startsWith("/") ? path : `/${path}`}`
}

async function responseJSON(response: APIResponse, operation: string): Promise<unknown> {
  if (!response.ok()) {
    throw new Error(`${operation} failed with HTTP ${response.status()}`)
  }
  return response.json()
}

function asObject(value: unknown, operation: string): JsonObject {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${operation} returned a non-object JSON response`)
  }
  return value as JsonObject
}

async function withAuthenticatedContext<T>(
  baseURL: string,
  initDataRaw: string,
  operation: (context: APIRequestContext, userId: string) => Promise<T>,
): Promise<T> {
  const authContext = await request.newContext()
  let authenticatedContext: APIRequestContext | undefined
  try {
    const authResponse = await authContext.post(endpointURL(baseURL, "/api/auth/telegram"), {
      data: { initData: initDataRaw },
      headers: { "Content-Type": "application/json" },
    })
    const authPayload = asObject(
      await responseJSON(authResponse, "POST /api/auth/telegram"),
      "POST /api/auth/telegram",
    )
    if (typeof authPayload.userId !== "string" || !authPayload.userId) {
      throw new Error("POST /api/auth/telegram returned no userId")
    }

    // The API keeps SESSION_COOKIE_SECURE=true even for local HTTP. Carry the
    // opaque cookie explicitly so APIRequestContext does not discard it on a
    // loopback HTTP request; initData itself is never forwarded after auth.
    const setCookie = authResponse.headers()["set-cookie"] || ""
    const cookieValue = setCookie.match(new RegExp(`${SESSION_COOKIE_NAME}=([^;]+)`))?.[1]
    if (!cookieValue) {
      throw new Error(`POST /api/auth/telegram did not return ${SESSION_COOKIE_NAME}`)
    }
    authenticatedContext = await request.newContext({
      extraHTTPHeaders: { Cookie: `${SESSION_COOKIE_NAME}=${cookieValue}` },
    })
    return await operation(authenticatedContext, authPayload.userId)
  } finally {
    await authenticatedContext?.dispose()
    await authContext.dispose()
  }
}
// END_BLOCK: TELEGRAM_ID_AND_INITDATA

// START_BLOCK: PROFILE_SEED
function profilePayload(label: CohortLabel): JsonObject {
  const birth: JsonObject = {
    birthday: "1990-01-15",
    birthTimeMode: label,
    birthCity: "Moscow",
    birthLat: 55.7558,
    birthLon: 37.6173,
    birthTz: "Europe/Moscow",
  }

  if (label === "exact") birth.birthTime = "14:30"
  if (label === "bucket") birth.birthTimeBucket = "morning"

  return {
    firstName: `P8-C ${label}`,
    gender: "female",
    birth,
  }
}

async function seedProfile(
  baseURL: string,
  initDataRaw: string,
  label: CohortLabel,
): Promise<string> {
  return withAuthenticatedContext(baseURL, initDataRaw, async (context, userId) => {
    const response = await context.put(endpointURL(baseURL, "/api/profile"), {
      data: profilePayload(label),
      headers: { "Content-Type": "application/json" },
    })
    const payload = asObject(
      await responseJSON(response, "PUT /api/profile"),
      "PUT /api/profile",
    )
    const birth = asObject(payload.birth, "PUT /api/profile.birth")
    if (payload.userId !== userId || birth.birthTimeMode !== label) {
      throw new Error(`PUT /api/profile returned an unexpected ${label} profile mode`)
    }
    return userId
  })
}
// END_BLOCK: PROFILE_SEED

// START_BLOCK: PUBLIC_TRIAL_GRANT
async function grantPublicReferralAccess(
  baseURL: string,
  referrer: CohortUser,
  invitee: CohortUser,
): Promise<void> {
  const inviteCode = await withAuthenticatedContext(
    baseURL,
    referrer.initDataRaw,
    async (context) => {
      const response = await context.get(endpointURL(baseURL, "/api/referral"))
      const payload = asObject(
        await responseJSON(response, "GET /api/referral"),
        "GET /api/referral",
      )
      if (typeof payload.inviteCode !== "string" || !/^\d+$/.test(payload.inviteCode)) {
        throw new Error("GET /api/referral returned an invalid inviteCode")
      }
      return payload.inviteCode
    },
  )

  // Telegram auth itself is deliberately side-effect limited and does not
  // create a trial entry. This is the existing public product flow for the
  // 14-day entry; using the already-created bucket user keeps the cohort at
  // three users and avoids direct SQL or a test-only grant endpoint.
  await withAuthenticatedContext(baseURL, invitee.initDataRaw, async (context) => {
    const response = await context.post(endpointURL(baseURL, "/api/referral/claim"), {
      data: { referrer_code: inviteCode },
      headers: { "Content-Type": "application/json" },
    })
    const payload = asObject(
      await responseJSON(response, "POST /api/referral/claim"),
      "POST /api/referral/claim",
    )
    if (payload.success !== true || payload.days_granted !== 14) {
      throw new Error("POST /api/referral/claim did not grant the expected trial")
    }
  })
}
// END_BLOCK: PUBLIC_TRIAL_GRANT

// START_BLOCK: COHORT_BUILDER
export async function seedAcceptanceCohort(baseURL: string): Promise<AcceptanceCohort> {
  // START_FUNCTION_CONTRACT: F-M-E2E-ACCEPTANCE-COHORT.seedAcceptanceCohort
  // purpose: Create three fresh, onboarded birth-time-mode users and make the
  //   exact user full-access through the existing public referral flow.
  // inputs: baseURL — frontend origin; E2E_API_BASE_URL may override API calls.
  // returns: AcceptanceCohort — users, normalized baseURL, and fixed reference dates.
  // side_effects: Telegram auth/profile HTTP writes, referral HTTP write, JSONL
  //   cleanup-ledger appends.
  // emitted_logs: none.
  // error_behavior: throws on invalid baseURL, generator failure, or any
  //   non-2xx/malformed public API response.
  // END_FUNCTION_CONTRACT: F-M-E2E-ACCEPTANCE-COHORT.seedAcceptanceCohort
  const normalizedBaseURL = normalizeBaseURL(baseURL)
  const requestBaseURL = apiBaseURL(normalizedBaseURL)
  const seedNonce = `${Date.now()}-${process.pid}-${randomUUID()}`
  const users: CohortUser[] = []

  for (const label of COHORT_LABELS) {
    const telegramUserId = newTelegramUserId(seedNonce, label)
    const initDataRaw = generateInitData(telegramUserId, label)

    // Auth creates the session and lazy profile row; seedProfile performs the
    // profile write in that same isolated cookie jar.
    const userId = await seedProfile(requestBaseURL, initDataRaw, label)
    users.push({ label, telegramUserId, userId, initDataRaw })
  }

  await grantPublicReferralAccess(requestBaseURL, users[0], users[1])

  return {
    baseURL: normalizedBaseURL,
    users,
    // 2026-07-08 is the frozen hero reference used by the Today evidence;
    // 2026-07-12 is the documented quiet-day reference. The live API creates
    // any missing snapshot on first request; this helper only fixes identity.
    heroDate: HERO_DATE,
    quietDate: QUIET_DATE,
  }
}
// END_BLOCK: COHORT_BUILDER

// START_BLOCK: ACCESS_DATES
function parseISODate(value: string): Date {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) throw new Error(`Expected YYYY-MM-DD date, received ${value}`)

  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const date = new Date(Date.UTC(year, month - 1, day))
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    throw new Error(`Invalid calendar date: ${value}`)
  }
  return date
}

function shiftISODate(value: string, days: number): string {
  const date = parseISODate(value)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export function accessDatesFor(
  user: CohortUser,
  today: string,
): { fullDate: string; previewDate: string; lockedDate: string } {
  // START_FUNCTION_CONTRACT: F-M-E2E-ACCEPTANCE-COHORT.accessDatesFor
  // purpose: Derive the deterministic access-state matrix for one cohort user.
  // inputs: user — validated cohort member; today — YYYY-MM-DD current UTC date.
  // returns: fullDate=today, previewDate=yesterday, lockedDate=today+400 days.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: throws on an unknown label or malformed calendar date.
  // END_FUNCTION_CONTRACT: F-M-E2E-ACCEPTANCE-COHORT.accessDatesFor
  if (!COHORT_LABELS.includes(user.label)) {
    throw new Error(`Unsupported acceptance cohort label: ${user.label}`)
  }
  parseISODate(today)
  return {
    fullDate: today,
    previewDate: shiftISODate(today, -1),
    lockedDate: shiftISODate(today, 400),
  }
}
// END_BLOCK: ACCESS_DATES
