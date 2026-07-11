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

const navigationState = vi.hoisted(() => ({ search: "why=1" }))

vi.mock("@/lib/log", () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }),
  usePathname: () => "/",
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(navigationState.search),
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
    navigationState.search = "why=1"
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
    expect(screen.getByTestId("activation-evidence-card").textContent).toContain(payload.headline)

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
    expect(whySection.textContent).toContain("Личная логика периода")
    expect(screen.getByTestId("why-today").textContent).not.toMatch(/Транзит|Профекция|Фирдар|орб/i)
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
    expect(screen.getByTestId("why-today").textContent).not.toMatch(/Профекция|Фирдар|орб/i)
    expect(screen.getAllByTestId("why-time-horizon").map((item) => item.getAttribute("data-horizon"))).toEqual(["long", "medium", "fast"])
    expect(screen.getAllByTestId("why-time-horizon")[0].textContent).toContain("1 год → несколько лет")
    expect(screen.getAllByTestId("why-time-horizon")[1].textContent).toContain("2–6 месяцев вокруг пика")
    expect(screen.getAllByTestId("why-time-horizon")[2].textContent).toContain("несколько часов → 2 суток")
    expect(screen.getAllByTestId("why-time-horizon")[0].textContent).toContain("Вы не просто реагируете на один сложный день")
    expect(screen.getAllByTestId("why-time-horizon")[1].textContent).toContain("Сейчас появилось окно")
    expect(screen.getAllByTestId("why-time-horizon")[2].textContent).toContain("Сегодня длинная тема особенно заметна")

    fireEvent.click(technicalToggle)
    expect(technicalToggle.getAttribute("aria-expanded")).toBe("true")
    const technical = screen.getByTestId("astrology-calculation")
    expect(screen.getAllByTestId("astrology-calculation-item")).toHaveLength(5)
    expect(technical.querySelectorAll('[data-horizon="long"] [data-testid="astrology-calculation-item"]')).toHaveLength(2)
    expect(technical.querySelectorAll('[data-horizon="medium"] [data-testid="astrology-calculation-item"]')).toHaveLength(2)
    expect(technical.querySelectorAll('[data-horizon="fast"] [data-testid="astrology-calculation-item"]')).toHaveLength(1)
    expect(technical.textContent).toContain("Луна")
    expect(technical.textContent).toContain("Плутон")
    expect(technical.textContent).toContain("Нептун")
    expect(technical.textContent).toContain("тригон")
    expect(technical.textContent).toContain("оппозиция")
    expect(technical.textContent).toContain("орб 1.05")
    expect(technical.textContent).toContain("Пик уже пройден · влияние ослабевает")
    expect(technical.textContent).toContain("Профекция")
    expect(technical.textContent).toContain("Фирдар")
    expect(technical.textContent).not.toMatch(/Moon opposition|act-|source_frame|strength/i)
  })

  it("opens both disclosures from the why and astro deeplink", () => {
    navigationState.search = "why=1&astro=1"
    const { payload } = adaptTodayPayload(dayPayloadV2, new Date("2026-07-08T12:00:00Z"))
    render(<WhyExpanded sections={[]} keyInsight="" v2={payload.v2} />)

    expect(screen.getByTestId("astrology-calculation-toggle").getAttribute("aria-expanded")).toBe("true")
    expect(screen.getAllByTestId("astrology-calculation-item")).toHaveLength(5)
  })

  it("keeps the legacy Why flow available without V2 horizons", () => {
    render(
      <WhyExpanded
        sections={[{ id: "legacy", title: "Личный контекст", iconName: "Sparkles", paragraphs: ["Существующее объяснение остаётся доступным."] }]}
        keyInsight="Ключ дня"
        open
      />,
    )

    expect(screen.getByText("Личный контекст")).toBeTruthy()
    expect(screen.getAllByText("Ключ дня")).toHaveLength(2)
    expect(screen.queryByTestId("why-time-horizon")).toBeNull()
    expect(screen.queryByTestId("astrology-calculation")).toBeNull()
  })

  it("renders standalone safe whyToday without a full V2 block", () => {
    render(
      <WhyExpanded
        sections={[]}
        keyInsight=""
        whyToday={[{
          id: "standalone-safe",
          title: "Личная тема заметнее обычного",
          body: "Полезно не торопиться с выводами и опереться на проверяемые шаги.",
          activationIds: [],
          techniques: [],
        }]}
        open
      />,
    )

    expect(screen.getByTestId("why-today-item").textContent).toContain("Личная тема заметнее обычного")
    expect(screen.queryByText("Один личный сюжет идёт в трёх скоростях.")).toBeNull()
    expect(screen.queryByTestId("astrology-calculation-toggle")).toBeNull()
  })

  it("uses the human-only fallback when V2 evidence does not pass horizon thresholds", () => {
    const { payload } = adaptTodayPayload(dayPayloadV2, new Date("2026-07-08T12:00:00Z"))
    const v2 = structuredClone(payload.v2!)
    v2.activationEvidence = [{ ...v2.activationEvidence[0], strength: 0.1, orb: 4 }]
    v2.activationSummary.topActivatedTargets[0].activationIds = ["act-moon-opp-pluto"]
    v2.whyToday = [v2.whyToday[0]]
    v2.scoreBreakdown = {}
    render(<WhyExpanded sections={[]} keyInsight="" v2={v2} open />)

    expect(screen.getByTestId("why-today-item").textContent).toContain("Сегодня длинная тема особенно заметна")
    expect(screen.queryByTestId("why-time-horizon")).toBeNull()
    expect(screen.queryByText("Один личный сюжет идёт в трёх скоростях.")).toBeNull()
    expect(screen.queryByTestId("astrology-calculation-toggle")).toBeNull()
  })

  it("returns no Why block for an empty V2 payload without safe copy or legacy sections", () => {
    const { payload } = adaptTodayPayload(dayPayloadV2, new Date("2026-07-08T12:00:00Z"))
    const v2 = structuredClone(payload.v2!)
    v2.activationSummary.topActivatedTargets = []
    v2.activationEvidence = []
    v2.whyToday = []
    v2.scoreBreakdown = {}
    const { queryByTestId } = render(<WhyExpanded sections={[]} keyInsight="" v2={v2} open />)

    expect(queryByTestId("why-expanded")).toBeNull()
  })
})
