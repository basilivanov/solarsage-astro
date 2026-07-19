// ############################################################################
// AI_HEADER: E2E_MOCK_VISUAL_ACCEPTANCE_DAY — same-payload UI proof (V2 gate)
// ROLE: Blocking release-acceptance UI proof: a committed V2 audit payload
//       (11_final_today_payload.json) renders correctly through the existing
//       mock-visual route harness with DOM contract assertions and one
//       evidence screenshot. Fails closed while only today/v1 exists.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-ACCEPTANCE-DAY
// purpose: Prove the SAME committed V2 payload (11_final_today_payload.json)
//   passes the contract schema and renders the key Today DOM states. The
//   gate explicitly REJECTS non-V2 payloads: while the committed artifact is
//   today/v1, this spec fails closed with an explicit blocker error — it is
//   NOT complete until an owner-approved committed today.v2.x payload exists
//   (the evidence screenshot does NOT create a visual baseline).
// owns:
//   - e2e/mock-visual/acceptance-day.spec.ts
// inputs: ACCEPTANCE_PAYLOAD_PATH env (default committed artifact path).
// outputs: Playwright assertions + evidence screenshot artifact.
// dependencies: existing route-interception harness, TodayPayloadWireSchema.
// side_effects: writes artifacts/acceptance-today.png evidence screenshot.
// emitted_logs: none.
// invariants:
//   - fails closed (hard error) when the payload file is missing, fails the
//     contract schema, or its schema version is not a V2 series.
// failure_policy: hard error naming the blocker; never expected-failure.
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-ACCEPTANCE-DAY

import { readFileSync } from "node:fs"
import { expect, test, type Page } from "@playwright/test"
import { expectNoMissingApiFixtures, installMockApiRoutes, type MockApiRouteFixtures } from "./route-interception"
import { TodayPayloadWireSchema } from "@/packages/contracts/runtime"

const payloadPath = process.env.ACCEPTANCE_PAYLOAD_PATH ?? "artifacts/audit/2026-07-08/11_final_today_payload.json"
const rawPayload = JSON.parse(readFileSync(payloadPath, "utf-8"))
const schemaVersion: string =
  rawPayload?.meta?.schemaVersion ?? rawPayload?.meta?.schema_version ?? ""

async function installTelegramFixture(page: Page) {
  // Minimal Telegram/localStorage init (mirrors existing mock-visual specs)
  // so the day page's auth-loading state cannot hang.
  await page.addInitScript(() => {
    (window as any).Telegram = {
      WebApp: {
        initData: "",
        initDataUnsafe: {},
        ready: () => {},
        expand: () => {},
        close: () => {},
        platform: "web",
        version: "9.5",
        colorScheme: "light",
        themeParams: {},
        isExpanded: true,
        viewportHeight: 812,
        viewportStableHeight: 812,
      },
    }
    localStorage.setItem("lumen:onboarded", "1")
  })
}

function buildFixtures(payload: unknown): MockApiRouteFixtures {
  const date = (payload as { date: string }).date
  return {
    [`/api/day/${date}`]: { body: payload },
    "/api/auth/dev": { status: 200, body: { status: "ok", userId: "acceptance-user" } },
    "/api/_log": { body: { ok: true } },
  }
}

test.describe("Acceptance same-payload UI proof (V2 gate)", () => {
  test("committed V2 payload renders the Today DOM contract", async ({ page }) => {
    expect(
      schemaVersion,
      `P1-3 BLOCKED: same-payload UI proof requires a committed V2 payload, ` +
      `but ${payloadPath} reports schemaVersion="${schemaVersion}". ` +
      `Wait for an owner-approved committed today.v2.x 11_final_today_payload.json ` +
      `(live audit refresh); do not substitute fixtures.`,
    ).toMatch(/^today\/v2/)

    const payload = TodayPayloadWireSchema.parse(rawPayload)
    const dayDate = payload.date

    await installTelegramFixture(page)
    const tracker = await installMockApiRoutes(page, buildFixtures(payload))
    await page.goto(`/day/${dayDate}`)

    const screen = page.getByTestId("today-screen")
    await expect(screen).toHaveAttribute("data-state", "ready", { timeout: 30_000 })
    await expect(page.getByTestId("day-summary-card")).toBeVisible()
    await expect(page.getByTestId("concrete-day-advice")).toBeVisible()

    // Evidence screenshot only — NOT a visual baseline; P1-3 stays partial
    // until an owner-approved V2 baseline exists.
    await page.screenshot({ path: "artifacts/acceptance-today.png", fullPage: true })
    await expectNoMissingApiFixtures(page, tracker)
  })
})
