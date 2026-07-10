// ############################################################################
// AI_HEADER: MODULE_TODAYSCREEN_V2_DOWNSTREAM_TEST
// ROLE: W11 frontend tests rendering real TodayScreen from committed fixture
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-TODAYSCREEN-V2-DOWNSTREAM
// purpose: Prove TodayScreen renders V2 evidence from committed frontend fixture.
// owns:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// inputs: artifacts/audit/2026-07-08/downstream/11_frontend_fixture.json
// outputs: vitest assertions
// dependencies: TodayScreen, WhyExpanded, DevAuditDrawer, validateAdaptedTodayPayload
// side_effects: none
// emitted_logs: none
// invariants: whyToday/score contribution ids subset of activationEvidence ids
// failure_policy: test fail
// END_MODULE_CONTRACT: M-TEST-TODAYSCREEN-V2-DOWNSTREAM

// START_MODULE_MAP: M-TEST-TODAYSCREEN-V2-DOWNSTREAM
// public_entrypoints: describe/it blocks
// END_MODULE_MAP: M-TEST-TODAYSCREEN-V2-DOWNSTREAM

import { describe, it, expect, vi, beforeEach } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import React from "react"
import fs from "node:fs"
import path from "node:path"
import type { AccessInfo } from "@/lib/contracts/access"
import { validateAdaptedTodayPayload } from "@/lib/contracts/today"
import { TodayScreen } from "@/components/today/today-screen"
import { WhyExpanded } from "@/components/today/why-expanded"
import { DevAuditDrawer } from "@/components/today/dev-audit-drawer"
import { dayPayloadV2 } from "@/e2e/mock-visual/fixtures/day-v2-2026-07-08"
import { adaptTodayPayload } from "@/lib/adapters/today-payload"

vi.mock("@/lib/log", () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }),
  usePathname: () => "/",
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams("why=1"),
}))

vi.mock("@/components/today/date-header", () => ({
  DateHeader: () => <div data-testid="date-header" />,
}))
vi.mock("@/components/today/today-notes", () => ({
  TodayNotes: () => <div data-testid="today-notes" />,
}))
vi.mock("@/components/today/day-reading", () => ({
  DayReading: () => <div data-testid="day-reading" />,
}))
vi.mock("@/components/today/week-strip", () => ({
  WeekStrip: () => <div data-testid="week-strip" />,
}))
vi.mock("@/components/paywall", () => ({
  Paywall: () => <div data-testid="paywall" />,
}))
vi.mock("@/components/trial-banner", () => ({
  TrialBanner: () => <div data-testid="trial-banner" />,
}))
vi.mock("@/components/checkin/yesterday-echo", () => ({
  YesterdayEchoLoader: () => <div data-testid="yesterday-echo" />,
}))
vi.mock("@/lib/today", () => ({
  addDays: (d: Date, n: number) => new Date(d.getTime() + n * 86400000),
  sameDay: () => true,
  TODAY: new Date("2026-07-08T12:00:00Z"),
}))
vi.mock("@/lib/access", () => ({
  isDayAccessible: () => true,
}))

const fixturePath = path.join(
  process.cwd(),
  "artifacts/audit/2026-07-08/downstream/11_frontend_fixture.json",
)

function loadFixture() {
  const raw = JSON.parse(fs.readFileSync(fixturePath, "utf8"))
  const payload = validateAdaptedTodayPayload(raw.payload)
  return { raw, payload }
}

const access: AccessInfo = {
  state: "subscription",
  hasAccess: true,
  accessStart: null,
  accessEnd: null,
  daysLeft: 0,
}

describe("TodayScreen V2 downstream fixture", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders TodayScreen with activation evidence from committed fixture", () => {
    const { raw, payload } = loadFixture()
    expect(raw.assertions.has_v2).toBe(Boolean(payload.v2))
    render(
      <TodayScreen
        payload={payload}
        access={access}
        selectedDate={new Date("2026-07-08T12:00:00Z")}
        onDateChange={() => {}}
      />,
    )
    // Stable screen root contract
    expect(screen.getByTestId("today-screen")).toBeTruthy()
    expect(screen.getByTestId("activation-evidence-card")).toBeTruthy()
    expect(screen.getByTestId("activation-evidence-card").textContent).toContain(
      payload.v2!.activationSummary.headline,
    )

    // Every activation contribution id in scoreBreakdown must exist in activationEvidence
    const evidenceIds = new Set((payload.v2?.activationEvidence || []).map((e) => e.id))
    const scoreBreakdown = payload.v2?.scoreBreakdown || {}
    for (const ss of Object.values(scoreBreakdown)) {
      for (const c of ss.contributions || []) {
        if (c.source === "activation") {
          expect(evidenceIds.has(c.sourceId)).toBe(true)
        }
      }
    }
  })

  it("renders human-safe WhyExpanded content and keeps activation id integrity", () => {
    const { payload } = loadFixture()
    const why = payload.v2?.whyToday || []
    expect(why.length).toBeGreaterThan(0)
    render(
      <WhyExpanded
        sections={payload.why}
        keyInsight={payload.keyInsight}
        v2={payload.v2}
        open
      />,
    )
    const whySection = screen.getByTestId("why-expanded")
    expect(whySection.textContent).toContain("Личная логика дня")
    expect(whySection.textContent).not.toMatch(/Транзит|Профекция|Фирдар|орб/i)
    expect(screen.getByTestId("astrology-calculation-toggle").getAttribute("aria-expanded")).toBe("false")
    const evidenceIds = new Set((payload.v2?.activationEvidence || []).map((e) => e.id))
    for (const item of why) {
      for (const id of item.activationIds || []) {
        expect(evidenceIds.has(id)).toBe(true)
      }
    }
  })

  it("renders DevAuditDrawer versions from fixture audit", () => {
    const { payload } = loadFixture()
    render(<DevAuditDrawer audit={payload.v2?.audit} forceShow={true} />)
    expect(screen.getByTestId("dev-audit-drawer")).toBeTruthy()
    expect(screen.getByText(String(payload.v2?.audit?.scoringVersion))).toBeTruthy()
    expect(screen.getByText(String(payload.v2?.audit?.calculationVersion))).toBeTruthy()
  })

  it("keeps technical evidence nested until the astrology disclosure is opened", () => {
    const { payload } = adaptTodayPayload(dayPayloadV2, new Date("2026-07-08T12:00:00Z"))
    render(
      <WhyExpanded
        sections={[]}
        keyInsight=""
        v2={payload.v2}
        open
      />,
    )
    const section = screen.getByTestId("why-expanded")
    const technicalToggle = screen.getByTestId("astrology-calculation-toggle")
    expect(technicalToggle.getAttribute("aria-expanded")).toBe("false")
    expect(section.textContent).not.toMatch(/Профекция|Фирдар|орб/i)

    fireEvent.click(technicalToggle)
    expect(technicalToggle.getAttribute("aria-expanded")).toBe("true")
    const technical = screen.getByTestId("astrology-calculation")
    expect(screen.getAllByTestId("astrology-calculation-item")).toHaveLength(3)
    expect(technical.textContent).toContain("Луна")
    expect(technical.textContent).toContain("Профекция")
    expect(technical.textContent).toContain("Фирдар")
    expect(technical.textContent).not.toMatch(/Moon opposition|act-|source_frame|strength/i)
  })
})
