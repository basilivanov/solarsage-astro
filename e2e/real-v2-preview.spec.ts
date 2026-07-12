// ############################################################################
// AI_HEADER: MODULE_E2E_REAL_V2_PREVIEW — strict no-interception real V2 proof.
// ROLE: Requires dev auth, canonical API identity, backend horizons, technical
//   disclosures, and sphere navigation in untouched desktop/mobile projects.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-REAL-V2-PREVIEW
// purpose: Fail closed unless a clean browser reaches the exact acceptance URL
//   and renders backend-owned today.v2.1 horizons from the real API.
// owns:
//   - e2e/real-v2-preview.spec.ts
// inputs:
//   - E2E_BASE_URL (expected http://127.0.0.1:3003)
//   - natural frontend /api/auth/dev and /api/day/2026-07-08 requests
// outputs:
//   - strict Playwright assertions
//   - project-specific full-day and Why PNG attachments
//   - redacted network-proof JSON attachment
// dependencies:
//   - @playwright/test
//   - packages/contracts/runtime
// side_effects:
//   - writes Playwright screenshots and proof attachments under ignored test-results
// emitted_logs:
//   - none
// invariants:
//   - browser context begins without cookies
//   - project viewports are not overridden
//   - route interception, HAR, cookie seeding, fixture, and mock APIs are absent
//   - V1, 401, locked, unavailable, malformed, and missing horizons always fail
//   - dynamic response copy and raw activation IDs are absent from proof artifacts
// failure_policy:
//   - any transport, schema, identity, horizon, DOM, accessibility, focus, or
//     viewport mismatch fails the project without skip or compatibility fallback
// END_MODULE_CONTRACT: M-E2E-REAL-V2-PREVIEW

// START_MODULE_MAP: M-E2E-REAL-V2-PREVIEW
// public_entrypoints:
//   - strict real-preview Playwright test
// semantic_blocks:
//   - CLOSED_ENUMS: static horizon and sphere selector contracts
//   - NETWORK_AND_SCHEMA: passive transport capture and generated schema proof
//   - IDENTITY_AND_HORIZONS: exact versions and backend horizon invariants
//   - DOM_AND_TECHNICAL: ready UI and all accessible technical disclosures
//   - SPHERE_NAVIGATION: selected/expanded/focus/status/viewport repeat proof
//   - ATTACHMENTS: project-specific PNGs and redacted structural network JSON
// owned_tests:
//   - self
// END_MODULE_MAP: M-E2E-REAL-V2-PREVIEW

import { expect, test } from "@playwright/test"
import { TodayPayloadWireSchema } from "../packages/contracts/runtime"

// START_BLOCK: CLOSED_ENUMS
const DATE = "2026-07-08"
const DAY_PATHNAME = `/day/${DATE}`
const DAY_PATH = `${DAY_PATHNAME}?why=1`
const HORIZONS = ["long", "medium", "fast"] as const
const SPHERE_KEYS = [
  "work",
  "money",
  "documents",
  "relationships",
  "sport",
  "communication",
  "health",
  "decisions",
  "travel",
  "creativity",
  "study",
  "shopping",
] as const

type SphereKey = (typeof SPHERE_KEYS)[number]

const SPHERE_ROW_SELECTOR: Record<SphereKey, string> = {
  work: '[data-testid="concrete-day-advice-row"][data-sphere-key="work"]',
  money: '[data-testid="concrete-day-advice-row"][data-sphere-key="money"]',
  documents: '[data-testid="concrete-day-advice-row"][data-sphere-key="documents"]',
  relationships: '[data-testid="concrete-day-advice-row"][data-sphere-key="relationships"]',
  sport: '[data-testid="concrete-day-advice-row"][data-sphere-key="sport"]',
  communication: '[data-testid="concrete-day-advice-row"][data-sphere-key="communication"]',
  health: '[data-testid="concrete-day-advice-row"][data-sphere-key="health"]',
  decisions: '[data-testid="concrete-day-advice-row"][data-sphere-key="decisions"]',
  travel: '[data-testid="concrete-day-advice-row"][data-sphere-key="travel"]',
  creativity: '[data-testid="concrete-day-advice-row"][data-sphere-key="creativity"]',
  study: '[data-testid="concrete-day-advice-row"][data-sphere-key="study"]',
  shopping: '[data-testid="concrete-day-advice-row"][data-sphere-key="shopping"]',
}

function requiredAttribute(element: { getAttribute(name: string): Promise<string | null> }, name: string): Promise<string> {
  return element.getAttribute(name).then((value) => {
    if (!value) throw new Error(`Missing required ${name}`)
    return value
  })
}

function narrowSphereKey(value: string): SphereKey {
  for (const key of SPHERE_KEYS) {
    if (value === key) return key
  }
  throw new Error(`Unexpected sphere key: ${value}`)
}
// END_BLOCK: CLOSED_ENUMS

// Keep each configured project's device/viewport untouched while using Chromium
// for loopback HTTP. WebKit rejects the backend's production-safe Secure cookie
// on http://127.0.0.1 even after the natural auth 200 response.
test.use({ browserName: "chromium" })

test.describe("Real V2 preview — strict no interception", () => {
  test("requires exact V2 identity, horizons, disclosures, and sphere navigation", async ({ context, page }, testInfo) => {
    test.setTimeout(120_000)
    expect(await context.cookies()).toEqual([])

    // START_BLOCK: NETWORK_AND_SCHEMA
    const requests: { method: string; url: string }[] = []
    page.on("request", (request) => requests.push({ method: request.method(), url: request.url() }))

    const authResponsePromise = page.waitForResponse((response) => {
      const url = new URL(response.url())
      return url.pathname === "/api/auth/dev" && response.request().method() === "POST"
    }, { timeout: 90_000 })
    const dayResponsePromise = page.waitForResponse((response) => {
      const url = new URL(response.url())
      return url.pathname === `/api/day/${DATE}` && response.request().method() === "GET"
    }, { timeout: 90_000 })

    await page.goto(DAY_PATH, { waitUntil: "load", timeout: 60_000 })
    const [authResponse, dayResponse] = await Promise.all([authResponsePromise, dayResponsePromise])
    expect(authResponse.status(), "auth transport must be exact 200").toBe(200)
    expect(dayResponse.status(), "day transport must be exact 200").toBe(200)
    expect(authResponse.request().method()).toBe("POST")
    expect(dayResponse.request().method()).toBe("GET")

    const payload = TodayPayloadWireSchema.parse(await dayResponse.json())
    const horizons = payload.v2?.horizons
    const currentUrl = new URL(page.url())
    expect(currentUrl.pathname).toBe(DAY_PATHNAME)
    expect([...currentUrl.searchParams.entries()]).toEqual([["why", "1"]])
    const allUrls = requests.map((request) => request.url)
    expect(allUrls.some((url) => url.includes("/api/dev-fixtures/"))).toBe(false)
    expect(allUrls.some((url) => url.includes(":18092"))).toBe(false)
    expect(allUrls.some((url) => /\/mock(?:\/|\?|$)/i.test(url))).toBe(false)
    expect(allUrls.some((url) => /\.json(?:\?|$)/i.test(url))).toBe(false)
    expect(currentUrl.searchParams.has("fixture")).toBe(false)

    const proof = {
      source: "real-api",
      fixture: false,
      interception: false,
      transport: { auth: authResponse.status(), day: dayResponse.status() },
      versions: {
        payload: payload.meta.payloadVersion,
        frontend: payload.meta.frontendPayloadVersion,
        content: payload.meta.contentVersion,
      },
      horizons: horizons?.items.map((item) => item.horizon) ?? [],
      authPath: "/api/auth/dev",
      dayPath: `/api/day/${DATE}`,
    }
    await testInfo.attach(`real-v2-preview-${testInfo.project.name}-network-proof.json`, {
      body: JSON.stringify(proof, null, 2),
      contentType: "application/json",
    })
    // END_BLOCK: NETWORK_AND_SCHEMA

    // START_BLOCK: IDENTITY_AND_HORIZONS
    expect(payload.meta.payloadVersion).toBe("today.v2.1")
    expect(payload.meta.frontendPayloadVersion).toBe(3)
    expect(payload.meta.contentVersion).toBe(10)
    if (!horizons) throw new Error("Backend horizons are required")
    expect(horizons.items.map((item) => item.horizon)).toEqual(HORIZONS)
    expect(new Set(horizons.items.map((item) => item.id)).size).toBe(3)
    for (const item of horizons.items) {
      expect(item.id.length).toBeGreaterThan(0)
      expect(item.activationIds.length).toBeGreaterThan(0)
      expect(item.actions.do.length).toBeGreaterThan(0)
      expect(item.actions.avoid.length).toBeGreaterThan(0)
    }

    // END_BLOCK: IDENTITY_AND_HORIZONS

    // START_BLOCK: DOM_AND_TECHNICAL
    const todayScreen = page.getByTestId("today-screen")
    await expect(todayScreen).toHaveAttribute("data-state", "ready")
    const whySection = page.getByTestId("why-expanded")
    const whyToggle = page.locator("#why-expanded-toggle")
    await expect(whySection).toBeVisible()
    await expect(whyToggle).toHaveAttribute("aria-expanded", "true")
    const horizonsBlock = page.getByTestId("why-horizons")
    await expect(horizonsBlock).toHaveAttribute("data-state", "ready")
    await expect(horizonsBlock).toHaveAttribute("data-source", "backend-horizons")
    await expect(page.getByTestId("why-horizons-unavailable")).toHaveCount(0)
    await expect(page.getByTestId("dev-timing-fixture-shell")).toHaveCount(0)
    await expect(page.getByTestId("dev-timing-fixture")).toHaveCount(0)

    const cards = page.getByTestId("why-horizon")
    await expect(cards).toHaveCount(3)
    for (let index = 0; index < HORIZONS.length; index += 1) {
      const horizon = HORIZONS[index]
      const card = cards.nth(index)
      await expect(card).toHaveAttribute("data-horizon", horizon)
      const toggle = card.getByTestId("why-horizon-technical-toggle")
      await expect(toggle).toHaveAttribute("data-horizon", horizon)
      await expect(toggle).toHaveAttribute("aria-expanded", "false")
      const toggleId = await requiredAttribute(toggle, "id")
      const regionId = await requiredAttribute(toggle, "aria-controls")
      await toggle.click()
      await expect(toggle).toHaveAttribute("aria-expanded", "true")
      const region = card.getByTestId("why-horizon-technical-content")
      await expect(region).toBeVisible()
      await expect(region).toHaveAttribute("id", regionId)
      await expect(region).toHaveAttribute("role", "region")
      await expect(region).toHaveAttribute("aria-labelledby", toggleId)
      await expect(region).toHaveAttribute("data-horizon", horizon)
    }
    // END_BLOCK: DOM_AND_TECHNICAL

    // START_BLOCK: SPHERE_NAVIGATION
    const sphereChips = page.getByTestId("why-horizon-sphere")
    await expect(sphereChips.first()).toBeVisible()
    const sphereKey = narrowSphereKey(await requiredAttribute(sphereChips.first(), "data-sphere-key"))
    const targetRow = page.locator(SPHERE_ROW_SELECTOR[sphereKey])
    const initialStatus = await requiredAttribute(targetRow, "data-status")

    await sphereChips.first().click()
    await expect(targetRow).toHaveAttribute("data-selected", "true")
    await expect(targetRow).toHaveAttribute("aria-expanded", "true")
    await expect(targetRow).toHaveAttribute("data-status", initialStatus)
    await expect(targetRow).toBeFocused()
    const details = page.getByTestId("concrete-day-advice-details")
    await expect(details).toBeVisible()
    await expect(details).toHaveAttribute("data-sphere-key", sphereKey)
    await expect(details).toHaveAttribute("data-status", initialStatus)
    const viewport = page.viewportSize()
    if (!viewport) throw new Error("Project viewport is required")
    const rowBox = await targetRow.boundingBox()
    if (!rowBox) throw new Error("Selected sphere row has no viewport box")
    expect(rowBox.y + rowBox.height).toBeGreaterThan(0)
    expect(rowBox.y).toBeLessThan(viewport.height)

    await sphereChips.first().click()
    await expect(targetRow).toHaveAttribute("data-selected", "true")
    await expect(targetRow).toHaveAttribute("aria-expanded", "true")
    await expect(targetRow).toHaveAttribute("data-status", initialStatus)
    await expect(targetRow).toBeFocused()
    await expect(details).toHaveAttribute("data-sphere-key", sphereKey)
    await expect(details).toHaveAttribute("data-status", initialStatus)
    // END_BLOCK: SPHERE_NAVIGATION

    // START_BLOCK: ATTACHMENTS
    const dayPng = await page.screenshot({ fullPage: true })
    await testInfo.attach(`real-v2-preview-${testInfo.project.name}-day.png`, {
      body: dayPng,
      contentType: "image/png",
    })
    const whyPng = await whySection.screenshot()
    await testInfo.attach(`real-v2-preview-${testInfo.project.name}-why.png`, {
      body: whyPng,
      contentType: "image/png",
    })
    // END_BLOCK: ATTACHMENTS
  })
})
