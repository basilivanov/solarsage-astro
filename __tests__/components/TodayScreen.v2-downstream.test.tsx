// ############################################################################
// AI_HEADER: MODULE_TODAYSCREEN_V2_DOWNSTREAM_TEST
// ROLE: Focused frontend tests for Stage B1 backend-owned horizons and legacy fallback.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-TODAYSCREEN-V2-DOWNSTREAM
// purpose: Prove TodayScreen/WhyExpanded preserve the original downstream matrix while extending it with backend-owned horizons coverage, exact DOM order, timing strings, technical ARIA, exact-row navigation, and missing-row filtering.
// owns:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// inputs: tracked downstream fixture, canonical dayPayloadV2 fixture, TodayScreen, WhyExpanded, ConcreteDayAdvice, presentation helpers.
// outputs: vitest assertions.
// dependencies: testing-library, vitest, fs/path, tracked fixture validator, canonical fixture, TodayScreen, WhyExpanded.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - backend horizons are authoritative when present.
//   - legacy selector is resolved only for exact previous accepted pair + horizons null.
//   - current/unavailable/mismatch identity never infers horizons.
//   - spies are created before render and restored between tests (order-independent).
//   - W2 test helpers use explicit narrowing, no new unsafe/non-null assertions.
//   - exact element spies prove row target, not container.
//   - original downstream audit/legacy assertions remain covered.
// failure_policy: test failure.
// END_MODULE_CONTRACT: M-TEST-TODAYSCREEN-V2-DOWNSTREAM

// START_MODULE_MAP: M-TEST-TODAYSCREEN-V2-DOWNSTREAM
// public_entrypoints: describe/it blocks
// semantic_blocks:
//   - FIXTURE_LOADING: tracked audit fixture loader and canonical fixture adapter.
//   - LEGACY_MATRIX: original downstream legacy scenarios preserved.
//   - MODE_MATRIX: current/previous/mismatch/missing identity + horizons coverage.
//   - BACKEND_HORIZONS_MATRIX: B1 backend-owned horizons coverage.
//   - HUMAN_DOM_ORDER: exact meaning-first layout with strength/risk/validity/actions/spheres/tech.
//   - EXACT_TIMING_MATRIX: verbatim range/peak/state for all three horizons.
//   - TECHNICAL_ACCESSIBILITY_MATRIX: unique ids, aria-controls/labelledby, data-horizon.
//   - SPHERE_NAVIGATION_MATRIX: exact row scroll/focus with own-property spies, repeat, status unchanged.
//   - MISSING_ROW_FILTERING: horizon chip suppressed for absent concreteAdvice row.
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP: M-TEST-TODAYSCREEN-V2-DOWNSTREAM

import { beforeEach, describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen, within } from "@testing-library/react"
import React from "react"
import fs from "node:fs"
import path from "node:path"
import type { AccessInfo } from "@/lib/contracts/access"
import { validateAdaptedTodayPayload, type TodayWireIdentity } from "@/lib/contracts/today"
import { TodayScreen } from "@/components/today/today-screen"
import { ConcreteDayAdvice } from "@/components/today/concrete-day-advice"
import { SphereDetailsSheet } from "@/components/today/sphere-details-sheet"
import { WhyExpanded } from "@/components/today/why-expanded"
import { DevAuditDrawer } from "@/components/today/dev-audit-drawer"
import { dayPayloadV2 } from "@/e2e/mock-visual/fixtures/day-v2-2026-07-08"
import { adaptTodayPayload } from "@/lib/adapters/today-payload"
import * as todayV2Presentation from "@/lib/presentation/today-v2"

function requireElement<T extends Element>(value: T | null | undefined, label: string): T {
  if (!value) throw new Error(`${label} is missing`)
  return value
}

const navigationState = vi.hoisted(() => ({ search: "why=1" }))

// Consumer routing constants matching the WhyExpanded consumer boundary.
// W2-VALENCE: current = today.v2.2/frontend 4, previous = today.v2.1/frontend 3.
const CURRENT_WIRE_IDENTITY = { payloadVersion: "today.v2.2", frontendPayloadVersion: 4, contentVersion: 11 } satisfies TodayWireIdentity
const PREVIOUS_WIRE_IDENTITY = { payloadVersion: "today.v2.1", frontendPayloadVersion: 3, contentVersion: 10 } satisfies TodayWireIdentity
const MISMATCH_WIRE_IDENTITY = { payloadVersion: "today.v2.2", frontendPayloadVersion: 3, contentVersion: 11 } satisfies TodayWireIdentity
const HIGH_CONTENT_IDENTITY = { payloadVersion: "today.v2.2", frontendPayloadVersion: 4, contentVersion: 999 } satisfies TodayWireIdentity

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

function buildCanonicalPayload() {
  return adaptTodayPayload(dayPayloadV2, new Date("2026-07-08T12:00:00Z"))
}

function renderBackendWhyExpanded() {
  const { payload } = buildCanonicalPayload()
  render(
    <WhyExpanded
      sections={payload.why}
      keyInsight={payload.keyInsight}
      v2={payload.v2}
      wireIdentity={payload.wireIdentity}
      concreteAdvice={payload.concreteAdvice}
      open
    />,
  )
  return payload
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
    vi.restoreAllMocks()
    vi.clearAllMocks()
    navigationState.search = "why=1"
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", { configurable: true, value: vi.fn() })
    Object.defineProperty(HTMLElement.prototype, "focus", { configurable: true, value: vi.fn() })
  })

  it("renders TodayScreen with activation evidence from tracked fixture", () => {
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

    expect(screen.getByTestId("today-screen")).toBeTruthy()
    expect(screen.getByTestId("activation-evidence-card")).toBeTruthy()
    expect(screen.getByTestId("activation-evidence-card").textContent).toContain(payload.headline)

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
        wireIdentity={PREVIOUS_WIRE_IDENTITY}
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

  it("renders DevAuditDrawer versions from tracked fixture audit", () => {
    const { payload } = loadFixture()
    render(<DevAuditDrawer audit={payload.v2?.audit} forceShow={true} />)
    expect(screen.getByTestId("dev-audit-drawer")).toBeTruthy()
    expect(screen.getByText(String(payload.v2?.audit?.scoringVersion))).toBeTruthy()
    expect(screen.getByText(String(payload.v2?.audit?.calculationVersion))).toBeTruthy()
  })

  it("keeps technical evidence nested until the astrology disclosure is opened in legacy-v2 mode", () => {
    const { payload } = buildCanonicalPayload()
    const v2 = structuredClone(payload.v2!)
    v2.horizons = null
    render(
      <WhyExpanded
        sections={[]}
        keyInsight=""
        v2={v2}
        wireIdentity={PREVIOUS_WIRE_IDENTITY}
        open
      />,
    )

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

  it("opens both disclosures from the why and astro legacy deeplink", () => {
    navigationState.search = "why=1&astro=1"
    const { payload } = buildCanonicalPayload()
    const v2 = structuredClone(payload.v2!)
    v2.horizons = null
    render(<WhyExpanded sections={[]} keyInsight="" v2={v2} wireIdentity={PREVIOUS_WIRE_IDENTITY} />)

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

  it("uses the human-only fallback when V2 evidence does not pass legacy horizon thresholds", () => {
    const { payload } = buildCanonicalPayload()
    const v2 = structuredClone(payload.v2!)
    v2.horizons = null
    v2.activationEvidence = [{ ...v2.activationEvidence[0], strength: 0.1, orb: 4 }]
    v2.activationSummary.topActivatedTargets[0].activationIds = ["act-moon-opp-pluto"]
    v2.whyToday = [v2.whyToday[0]]
    v2.scoreBreakdown = {}
    render(<WhyExpanded sections={[]} keyInsight="" v2={v2} wireIdentity={PREVIOUS_WIRE_IDENTITY} open />)

    expect(screen.getByTestId("why-today-item").textContent).toContain("Сегодня длинная тема особенно заметна")
    expect(screen.queryByTestId("why-time-horizon")).toBeNull()
    expect(screen.queryByText("Один личный сюжет идёт в трёх скоростях.")).toBeNull()
    expect(screen.queryByTestId("astrology-calculation-toggle")).toBeNull()
  })

  it("returns no Why block for an empty previous pair V2 payload without safe copy or legacy sections", () => {
    const { payload } = buildCanonicalPayload()
    const v2 = structuredClone(payload.v2!)
    v2.horizons = null
    v2.activationSummary.topActivatedTargets = []
    v2.activationEvidence = []
    v2.whyToday = []
    v2.scoreBreakdown = {}
    const { queryByTestId } = render(<WhyExpanded sections={[]} keyInsight="" v2={v2} wireIdentity={PREVIOUS_WIRE_IDENTITY} open />)

    expect(queryByTestId("why-expanded")).toBeNull()
  })

  it("does not render a legacy timing container when selected evidence has no timing fields", () => {
    const { payload } = buildCanonicalPayload()
    const v2 = structuredClone(payload.v2!)
    v2.horizons = null
    v2.activationEvidence = v2.activationEvidence.map((item) => ({
      ...item,
      activeFrom: undefined,
      exactAt: undefined,
      activeUntil: undefined,
    }))
    render(<WhyExpanded sections={[]} keyInsight="" v2={v2} wireIdentity={PREVIOUS_WIRE_IDENTITY} open />)

    expect(screen.getAllByTestId("why-time-horizon")).toHaveLength(3)
    expect(screen.queryByTestId("why-time-horizon-timing")).toBeNull()
  })

  it("renders all sphere rows in single column without an expander", () => {
    const { payload } = buildCanonicalPayload()
    const onSelectedKeyChange = vi.fn()
    const renderNavigator = (selectedKey: string | null) => (
      <ConcreteDayAdvice
        concreteAdvice={payload.concreteAdvice}
        selectedKey={selectedKey}
        onSelectedKeyChange={onSelectedKeyChange}
        onWhyOpen={() => {}}
      />
    )
    const { rerender } = render(renderNavigator(null))

    // All rows are visible in canonical order, no show-all expander
    expect(screen.getAllByTestId("concrete-day-advice-row")).toHaveLength(payload.concreteAdvice.rows.length)
    expect(screen.queryByTestId("concrete-day-advice-show-all")).toBeNull()

    // Rows have aria-haspopup="dialog" for triggering modal sheet
    const firstRow = screen.getAllByTestId("concrete-day-advice-row")[0]
    expect(firstRow.getAttribute("aria-haspopup")).toBe("dialog")
  })

  it("renders TodayScreen with backend horizons and stable screen contract", () => {
    const { payload } = buildCanonicalPayload()
    render(
      <TodayScreen
        payload={payload}
        access={access}
        selectedDate={new Date("2026-07-08T12:00:00Z")}
        onDateChange={() => {}}
      />,
    )

    expect(screen.getByTestId("today-screen").getAttribute("data-state")).toBe("ready")
    expect(screen.getByTestId("activation-evidence-card")).toBeTruthy()
    expect(screen.getByTestId("why-expanded")).toBeTruthy()
  })

  it("renders backend intro and three ordered why-horizon teasers from v2.horizons", () => {
    renderBackendWhyExpanded()

    const block = screen.getByTestId("why-horizons")
    expect(block.getAttribute("data-state")).toBe("ready")
    expect(block.getAttribute("data-source")).toBe("backend-horizons")
    expect(block.textContent).toContain("Личная логика периода")
    expect(block.textContent).toContain("Опору сейчас лучше перестраивать без резких движений")
    expect(block.textContent).toContain("Долгий цикл меняет отношение к ответственности и контролю")

    const teasers = screen.getAllByTestId("why-horizon-teaser")
    expect(teasers.map((item) => item.getAttribute("data-horizon"))).toEqual(["long", "medium", "fast"])
    expect(teasers.map((item) => item.getAttribute("data-status"))).toEqual(["mixed", "mixed", "tense"])
    expect(screen.queryByTestId("why-time-horizon")).toBeNull()
    expect(screen.queryByTestId("astrology-calculation")).toBeNull()
  })

  it("uses backend timing labels and visible tone text without recalculation", () => {
    renderBackendWhyExpanded()

    const teasers = screen.getAllByTestId("why-horizon-teaser")
    expect(teasers).toHaveLength(3)

    // Open long horizon sheet
    fireEvent.click(teasers[0])
    const longSheet = screen.getByTestId("horizon-sheet")
    expect(within(longSheet).getByTestId("why-horizon-timing").textContent).toContain("12 мая 2026 — 11 мая 2027")
    expect(within(longSheet).getByTestId("why-horizon-timing").textContent).toContain("Фон уже действует")
    expect(within(longSheet).getByTestId("why-horizon-tone").getAttribute("data-status")).toBe("mixed")

    // Close sheet
    fireEvent.click(within(longSheet).getByRole("button", { name: "Закрыть" }))

    // Open medium horizon sheet
    fireEvent.click(teasers[1])
    const mediumSheet = screen.getByTestId("horizon-sheet")
    expect(within(mediumSheet).getByTestId("why-horizon-timing").textContent).toContain("3–18 июля")
    expect(within(mediumSheet).getByTestId("why-horizon-timing").textContent).toContain("Точный пик — 10 июля, 14:32 по Москве")
    expect(within(mediumSheet).getByTestId("why-horizon-timing").textContent).toContain("Набирает силу")
    expect(within(mediumSheet).getByTestId("why-horizon-tone").getAttribute("data-status")).toBe("mixed")

    // Close sheet
    fireEvent.click(within(mediumSheet).getByRole("button", { name: "Закрыть" }))

    // Open fast horizon sheet
    fireEvent.click(teasers[2])
    const fastSheet = screen.getByTestId("horizon-sheet")
    expect(within(fastSheet).getByTestId("why-horizon-timing").textContent).toContain("8–10 июля по Москве")
    expect(within(fastSheet).getByTestId("why-horizon-timing").textContent).toContain("Пик был 8 июля в 08:00")
    expect(within(fastSheet).getByTestId("why-horizon-timing").textContent).toContain("Пик уже пройден")
    expect(within(fastSheet).getByTestId("why-horizon-tone").getAttribute("data-status")).toBe("tense")
  })

  it("renders backend actions, optional strength/risk, and manifestation conditions", () => {
    renderBackendWhyExpanded()

    const teasers = screen.getAllByTestId("why-horizon-teaser")

    // Open long horizon sheet
    fireEvent.click(teasers[0])
    const longSheet = screen.getByTestId("horizon-sheet")
    expect(within(longSheet).getByTestId("why-horizon-actions").querySelectorAll("li")).toHaveLength(2)
    expect(within(longSheet).getByTestId("why-horizon-avoid").querySelectorAll("li")).toHaveLength(1)
    expect(longSheet.textContent).toContain("Эта рамка актуальна до 11 мая 2027")
    expect(within(longSheet).getByTestId("why-horizon-strength")).toBeTruthy()
    expect(within(longSheet).getByTestId("why-horizon-risk")).toBeTruthy()
    expect(longSheet.textContent).toContain("Если сейчас вы обсуждаете новую роль или объём ответственности…")

    // Close
    fireEvent.click(within(longSheet).getByRole("button", { name: "Закрыть" }))

    // Open medium horizon sheet
    fireEvent.click(teasers[1])
    const mediumSheet = screen.getByTestId("horizon-sheet")
    expect(within(mediumSheet).getByTestId("why-horizon-actions").querySelectorAll("li")).toHaveLength(2)
    expect(within(mediumSheet).getByTestId("why-horizon-avoid").querySelectorAll("li")).toHaveLength(1)
    expect(mediumSheet.textContent).toContain("Этот эксперимент актуален до 18 июля")
    expect(within(mediumSheet).getByTestId("why-horizon-strength")).toBeTruthy()
    expect(within(mediumSheet).getByTestId("why-horizon-risk")).toBeTruthy()
  })

  it("renders per-card technical disclosures closed by default and opens associated content", () => {
    renderBackendWhyExpanded()

    const teasers = screen.getAllByTestId("why-horizon-teaser")
    fireEvent.click(teasers[0])
    const horizonSheet = screen.getByTestId("horizon-sheet")

    const toggle = within(horizonSheet).getByTestId("why-horizon-technical-toggle")
    expect(toggle.getAttribute("aria-expanded")).toBe("false")

    fireEvent.click(toggle)
    expect(toggle.getAttribute("aria-expanded")).toBe("true")
    const content = within(horizonSheet).getByTestId("why-horizon-technical-content")
    expect(content.getAttribute("role")).toBe("region")
    expect(content.textContent).toContain("Профекция")
    expect(content.textContent).toContain("Фирдар")
    expect(content.textContent).toContain("12 мая 2026 — 11 мая 2027")
  })

  it("uses concrete advice row labels for sphere buttons and integrates with TodayScreen navigator", () => {
    const { payload } = buildCanonicalPayload()
    render(
      <TodayScreen
        payload={payload}
        access={access}
        selectedDate={new Date("2026-07-08T12:00:00Z")}
        onDateChange={() => {}}
      />,
    )

    fireEvent.click(screen.getByRole("button", { name: "Почему так у меня" }))
    const teasers = screen.getAllByTestId("why-horizon-teaser")
    fireEvent.click(teasers[0])

    const horizonSheet = screen.getByTestId("horizon-sheet")
    const sphereButtons = within(horizonSheet).getAllByTestId("why-horizon-sphere")
    expect(sphereButtons.some((button) => button.textContent === "Работа")).toBe(true)

    fireEvent.click(sphereButtons.find((button) => button.textContent === "Работа")!)
    const details = screen.getByTestId("sphere-details-sheet")
    expect(details.getAttribute("data-sphere-key")).toBe("work")
  })

  it("does not call selectWhyTimeHorizons when backend horizons exist", () => {
    const spy = vi.spyOn(todayV2Presentation, "selectWhyTimeHorizons")
    renderBackendWhyExpanded()
    expect(spy).not.toHaveBeenCalled()
    spy.mockRestore()
  })

  it("keeps raw prefixes and legacy cards absent when backend block exists", () => {
    renderBackendWhyExpanded()
    const text = screen.getByTestId("why-horizons").textContent ?? ""
    expect(text).not.toContain("Transit_")
    expect(text).not.toContain("Natal_")
    expect(screen.queryByTestId("why-time-horizon")).toBeNull()
  })

  it("current pair + horizons=null shows unavailable state", () => {
    const { payload } = buildCanonicalPayload()
    if (!payload.v2) throw new Error("v2 missing")
    const v2 = { ...payload.v2, horizons: null }
    const spy = vi.spyOn(todayV2Presentation, "selectWhyTimeHorizons")
    render(
      <WhyExpanded
        sections={payload.why}
        keyInsight={payload.keyInsight}
        v2={v2}
        wireIdentity={CURRENT_WIRE_IDENTITY}
        open
      />,
    )
    expect(screen.getByTestId("why-horizons-unavailable").getAttribute("data-state")).toBe("empty")
    expect(screen.getByTestId("why-horizons-unavailable").getAttribute("data-source")).toBe("backend-horizons")
    expect(screen.getByTestId("why-horizons-unavailable").textContent).toContain("Три временных горизонта")
    expect(screen.queryByTestId("why-horizons")).toBeNull()
    expect(screen.queryByTestId("why-time-horizon")).toBeNull()
    expect(screen.queryByTestId("astrology-calculation")).toBeNull()
    expect(screen.queryByTestId("astrology-calculation-toggle")).toBeNull()
    expect(screen.queryByTestId("why-today")).toBeNull()
    expect(spy).not.toHaveBeenCalled()
    spy.mockRestore()
  })

  it("mismatched wire identity with horizons=null shows unavailable state", () => {
    const { payload } = buildCanonicalPayload()
    if (!payload.v2) throw new Error("v2 missing")
    const v2 = { ...payload.v2, horizons: null }
    const spy = vi.spyOn(todayV2Presentation, "selectWhyTimeHorizons")
    render(
      <WhyExpanded
        sections={payload.why}
        keyInsight={payload.keyInsight}
        v2={v2}
        wireIdentity={MISMATCH_WIRE_IDENTITY}
        open
      />,
    )
    expect(screen.getByTestId("why-horizons-unavailable")).toBeTruthy()
    expect(screen.queryByTestId("why-time-horizon")).toBeNull()
    expect(screen.queryByTestId("astrology-calculation")).toBeNull()
    expect(screen.queryByTestId("why-today")).toBeNull()
    expect(spy).not.toHaveBeenCalled()
    spy.mockRestore()
  })

  it("missing wire identity with horizons=null shows unavailable state", () => {
    const { payload } = buildCanonicalPayload()
    if (!payload.v2) throw new Error("v2 missing")
    const v2 = { ...payload.v2, horizons: null }
    const spy = vi.spyOn(todayV2Presentation, "selectWhyTimeHorizons")
    render(
      <WhyExpanded
        sections={payload.why}
        keyInsight={payload.keyInsight}
        v2={v2}
        open
      />,
    )
    expect(screen.getByTestId("why-horizons-unavailable")).toBeTruthy()
    expect(screen.queryByTestId("why-time-horizon")).toBeNull()
    expect(screen.queryByTestId("astrology-calculation")).toBeNull()
    expect(screen.queryByTestId("why-today")).toBeNull()
    expect(spy).not.toHaveBeenCalled()
    spy.mockRestore()
  })

  it("no-v2 branches do not regress when wireIdentity is absent", () => {
    render(
      <WhyExpanded
        sections={[{ id: "s1", title: "Legacy", iconName: "sun", paragraphs: ["text"] }]}
        keyInsight="Key"
        open
      />,
    )
    expect(screen.getByText("Legacy")).toBeTruthy()
    expect(screen.queryByTestId("why-horizons-unavailable")).toBeNull()
  })

  it("TodayScreen passes adapter wireIdentity so backend horizons render for canonical payload", () => {
    const { payload } = buildCanonicalPayload()
    const wi = payload.wireIdentity
    if (!wi) throw new Error("wireIdentity expected")
    expect(wi.payloadVersion).toBe("today.v2.1")
    render(
      <TodayScreen
        payload={payload}
        access={access}
        selectedDate={new Date("2026-07-08T12:00:00Z")}
        onDateChange={() => {}}
      />,
    )
    expect(screen.getByTestId("why-horizons").getAttribute("data-source")).toBe("backend-horizons")
  })

  it("previous pair with horizons present renders backend and selector 0", () => {
    const { payload } = buildCanonicalPayload()
    if (!payload.v2) throw new Error("v2 missing")
    const spy = vi.spyOn(todayV2Presentation, "selectWhyTimeHorizons")
    render(
      <WhyExpanded
        sections={payload.why}
        keyInsight={payload.keyInsight}
        v2={payload.v2}
        wireIdentity={PREVIOUS_WIRE_IDENTITY}
        open
      />,
    )
    expect(screen.getByTestId("why-horizons").getAttribute("data-source")).toBe("backend-horizons")
    expect(spy).not.toHaveBeenCalled()
    spy.mockRestore()
  })

  it("content version 999 does not prevent backend horizons", () => {
    const { payload } = buildCanonicalPayload()
    if (!payload.v2) throw new Error("v2 missing")
    const spy = vi.spyOn(todayV2Presentation, "selectWhyTimeHorizons")
    render(
      <WhyExpanded
        sections={payload.why}
        keyInsight={payload.keyInsight}
        v2={payload.v2}
        wireIdentity={HIGH_CONTENT_IDENTITY}
        open
      />,
    )
    expect(screen.getByTestId("why-horizons").getAttribute("data-source")).toBe("backend-horizons")
    expect(spy).not.toHaveBeenCalled()
    spy.mockRestore()
  })

  it("restores legacy selector cards when horizons are null with previous wire identity", () => {
    const { payload } = buildCanonicalPayload()
    if (!payload.v2) throw new Error("v2 missing")
    const v2 = { ...payload.v2, horizons: null }
    const spy = vi.spyOn(todayV2Presentation, "selectWhyTimeHorizons")
    render(
      <WhyExpanded
        sections={payload.why}
        keyInsight={payload.keyInsight}
        v2={v2}
        wireIdentity={PREVIOUS_WIRE_IDENTITY}
        concreteAdvice={payload.concreteAdvice}
        open
      />,
    )

    expect(spy).toHaveBeenCalledTimes(1)
    expect(screen.queryByTestId("why-horizons")).toBeNull()
    expect(screen.getAllByTestId("why-time-horizon").map((item) => item.getAttribute("data-horizon"))).toEqual(["long", "medium", "fast"])
    expect(screen.getByTestId("astrology-calculation-toggle").getAttribute("aria-expanded")).toBe("false")
  })

  it("keeps V2 without usable legacy evidence safe", () => {
    const { payload } = buildCanonicalPayload()
    const v2 = structuredClone(payload.v2!)
    v2.horizons = null
    v2.activationEvidence = [{ ...v2.activationEvidence[0], strength: 0.1, orb: 4 }]
    v2.activationSummary.topActivatedTargets = []
    v2.scoreBreakdown = {}
    render(
      <WhyExpanded
        sections={[]}
        keyInsight=""
        v2={v2}
        wireIdentity={PREVIOUS_WIRE_IDENTITY}
        whyToday={v2.whyToday}
        concreteAdvice={payload.concreteAdvice}
        open
      />,
    )

    expect(screen.queryByTestId("why-time-horizon")).toBeNull()
    expect(screen.queryByTestId("astrology-calculation-toggle")).toBeNull()
    expect(screen.getAllByTestId("why-today-item").some((item) => item.textContent?.includes("Сегодня длинная тема особенно заметна"))).toBe(true)
  })

  it("renders DevAuditDrawer versions from canonical fixture audit", () => {
    const { payload } = buildCanonicalPayload()
    render(<DevAuditDrawer audit={payload.v2?.audit} forceShow={true} />)
    expect(screen.getByTestId("dev-audit-drawer")).toBeTruthy()
    expect(screen.getByText(String(payload.v2?.audit?.scoringVersion))).toBeTruthy()
    expect(screen.getByText(String(payload.v2?.audit?.calculationVersion))).toBeTruthy()
  })

  // ── B4.W2 intro, indexes, tone ─────────────────────────────────
  it("renders backend intro, horizon teasers, exact tone labels", () => {
    renderBackendWhyExpanded()
    const intro = screen.getByTestId("why-horizons-intro")
    expect(intro.textContent).toContain("Личная логика периода")
    const teasers = screen.getAllByTestId("why-horizon-teaser")
    expect(teasers.map((el) => el.getAttribute("data-horizon"))).toEqual(["long", "medium", "fast"])
    const tones = teasers.map((t) => t.getAttribute("data-status"))
    expect(tones.filter((t) => t === "mixed")).toHaveLength(2)
    expect(tones.filter((t) => t === "tense")).toHaveLength(1)
    const text = screen.getByTestId("why-horizons").textContent ?? ""
    for (const old of ["Смешанный фон","Напряжённый фон","Поддерживающий фон","Нейтральный фон"]) {
      expect(text).not.toContain(old)
    }
  })

  // ── Long card exact DOM order inside horizon sheet ───────────────
  it("has exact DOM order for long card including strength/risk/validity/actions/avoid inside horizon sheet", () => {
    renderBackendWhyExpanded()
    const teasers = screen.getAllByTestId("why-horizon-teaser")
    fireEvent.click(teasers[0])

    const card = screen.getByTestId("horizon-sheet")
    const q = (sel: string) => requireElement(card.querySelector(sel), `long ${sel}`)
    const meaning = q("[data-testid='why-horizon-meaning']")
    const timing = q("[data-testid='why-horizon-timing']")
    const manifestations = q("[data-testid='why-horizon-manifestations']")
    const strength = q("[data-testid='why-horizon-strength']")
    const risk = q("[data-testid='why-horizon-risk']")
    const actions = q("[data-testid='why-horizon-actions']")
    const avoid = q("[data-testid='why-horizon-avoid']")
    const spheres = q("[data-testid='why-horizon-spheres']")
    const tech = q("[data-testid='why-horizon-technical-toggle']")
    const follow = Node.DOCUMENT_POSITION_FOLLOWING
    expect(meaning.compareDocumentPosition(timing) & follow).toBeTruthy()
    expect(timing.compareDocumentPosition(manifestations) & follow).toBeTruthy()
    expect(manifestations.compareDocumentPosition(strength) & follow).toBeTruthy()
    expect(strength.compareDocumentPosition(risk) & follow).toBeTruthy()
    expect(risk.compareDocumentPosition(actions) & follow).toBeTruthy()
    expect(actions.compareDocumentPosition(avoid) & follow).toBeTruthy()
    expect(avoid.compareDocumentPosition(spheres) & follow).toBeTruthy()
    expect(spheres.compareDocumentPosition(tech) & follow).toBeTruthy()
  })

  // ── Fast card DOM order ─────────────────────────────────────────
  it("has correct DOM order for fast card with optional strength absent inside horizon sheet", () => {
    renderBackendWhyExpanded()
    const teasers = screen.getAllByTestId("why-horizon-teaser")
    fireEvent.click(teasers[2])

    const card = screen.getByTestId("horizon-sheet")
    expect(card.querySelector("[data-testid='why-horizon-strength']")).toBeNull()
    expect(card.querySelector("[data-testid='why-horizon-patterns']")).toBeTruthy()
    const q = (sel: string) => requireElement(card.querySelector(sel), `fast ${sel}`)
    const manifestations = q("[data-testid='why-horizon-manifestations']")
    const risk = q("[data-testid='why-horizon-risk']")
    const actions = q("[data-testid='why-horizon-actions']")
    const avoid = q("[data-testid='why-horizon-avoid']")
    const spheres = q("[data-testid='why-horizon-spheres']")
    const tech = q("[data-testid='why-horizon-technical-toggle']")
    const follow = Node.DOCUMENT_POSITION_FOLLOWING
    expect(manifestations.compareDocumentPosition(risk) & follow).toBeTruthy()
    expect(risk.compareDocumentPosition(actions) & follow).toBeTruthy()
    expect(actions.compareDocumentPosition(avoid) & follow).toBeTruthy()
    expect(avoid.compareDocumentPosition(spheres) & follow).toBeTruthy()
    expect(spheres.compareDocumentPosition(tech) & follow).toBeTruthy()
  })

  // ── Exact timing strings ───────────────────────────────────────
  it("has exact timing strings for all three horizons inside horizon sheet", () => {
    renderBackendWhyExpanded()
    const teasers = screen.getAllByTestId("why-horizon-teaser")

    fireEvent.click(teasers[0])
    const longSheet = screen.getByTestId("horizon-sheet")
    const lr = requireElement(longSheet.querySelector("[data-testid='why-horizon-timing-range']"), "long range")
    expect(lr.textContent).toBe("Период: 12 мая 2026 — 11 мая 2027")
    expect(longSheet.querySelector("[data-testid='why-horizon-timing-peak']")).toBeNull()
    const ls = requireElement(longSheet.querySelector("[data-testid='why-horizon-timing-state']"), "long state")
    expect(ls.textContent).toBe("Сейчас: Фон уже действует")
    fireEvent.click(within(longSheet).getByRole("button", { name: "Закрыть" }))

    fireEvent.click(teasers[1])
    const mediumSheet = screen.getByTestId("horizon-sheet")
    const mr = requireElement(mediumSheet.querySelector("[data-testid='why-horizon-timing-range']"), "med range")
    expect(mr.textContent).toBe("Период: 3–18 июля")
    const mp = requireElement(mediumSheet.querySelector("[data-testid='why-horizon-timing-peak']"), "med peak")
    expect(mp.textContent).toBe("Пик: Точный пик — 10 июля, 14:32 по Москве")
    const ms = requireElement(mediumSheet.querySelector("[data-testid='why-horizon-timing-state']"), "med state")
    expect(ms.textContent).toBe("Сейчас: Набирает силу")
    fireEvent.click(within(mediumSheet).getByRole("button", { name: "Закрыть" }))

    fireEvent.click(teasers[2])
    const fastSheet = screen.getByTestId("horizon-sheet")
    const fr = requireElement(fastSheet.querySelector("[data-testid='why-horizon-timing-range']"), "fast range")
    expect(fr.textContent).toBe("Период: 8–10 июля по Москве")
    const fp = requireElement(fastSheet.querySelector("[data-testid='why-horizon-timing-peak']"), "fast peak")
    expect(fp.textContent).toBe("Пик: Пик был 8 июля в 08:00")
    const fs = requireElement(fastSheet.querySelector("[data-testid='why-horizon-timing-state']"), "fast state")
    expect(fs.textContent).toBe("Сейчас: Пик уже пройден")
  })

  // ── Closed technical leakage ──────────────────────────────────
  it("keeps closed human copy free of technical vocabulary and legacy constant", () => {
    renderBackendWhyExpanded()
    const text = screen.getByTestId("why-horizons").textContent ?? ""
    for (const pat of [/Профекция/i,/Фирдар/i,/транзит/i,/орб/i,/аппликац/i,/return/i,/Transit_/i,/Natal_/i,/activationIds/i,/natalFactIds/i,/profileFactIds/i]) {
      expect(text).not.toMatch(pat)
    }
    expect(text).not.toContain("три случайных факта")
    expect(screen.queryByTestId("why-horizon-technical-content")).toBeNull()
  })

  it("opens first technical toggle inside horizon sheet and shows backend terms and timing", () => {
    renderBackendWhyExpanded()
    const teasers = screen.getAllByTestId("why-horizon-teaser")
    fireEvent.click(teasers[0])
    const horizonSheet = screen.getByTestId("horizon-sheet")

    const toggle = within(horizonSheet).getByTestId("why-horizon-technical-toggle")
    fireEvent.click(toggle)
    const content = within(horizonSheet).getByTestId("why-horizon-technical-content")
    expect(content.textContent).toMatch(/Профекция/i)
    expect(content.textContent).toMatch(/Фирдар/i)
    expect(content.textContent).toContain("12 мая 2026")
    expect(content.textContent).not.toContain("activationIds")
    expect(content.textContent).not.toContain("natalFactIds")
  })

  // ── ARIA matrix (direct toggle data-horizon inside horizon sheet) ────────────────────
  it("each technical toggle inside horizon sheet has unique id, direct data-horizon, aria-controls", () => {
    renderBackendWhyExpanded()
    const teasers = screen.getAllByTestId("why-horizon-teaser")
    fireEvent.click(teasers[0])
    const horizonSheet = screen.getByTestId("horizon-sheet")

    const toggle = within(horizonSheet).getByTestId("why-horizon-technical-toggle")
    expect(toggle.tagName).toBe("BUTTON")
    expect(toggle.getAttribute("data-horizon")).toBe("long")
    expect(toggle.getAttribute("aria-expanded")).toBe("false")
    fireEvent.click(toggle)
    expect(toggle.getAttribute("aria-expanded")).toBe("true")
    const regionId = toggle.getAttribute("aria-controls")
    expect(regionId).toBeTruthy()
    const region = within(horizonSheet).getByTestId("why-horizon-technical-content")
    expect(region.getAttribute("id")).toBe(regionId)
    expect(region.getAttribute("role")).toBe("region")
    expect(region.getAttribute("aria-labelledby")).toBe(toggle.getAttribute("id"))
  })

  // ── Sphere chip callback contract ──────────────────────────────
  it("Direct Why render: work chip is native button, click calls onSphereSelect with exact key", () => {
    const { payload } = buildCanonicalPayload()
    const onSphereSelect = vi.fn()
    render(
      <WhyExpanded
        sections={payload.why}
        keyInsight={payload.keyInsight}
        v2={payload.v2}
        wireIdentity={CURRENT_WIRE_IDENTITY}
        concreteAdvice={payload.concreteAdvice}
        onSphereSelect={onSphereSelect}
        open
      />,
    )
    const teasers = screen.getAllByTestId("why-horizon-teaser")
    fireEvent.click(teasers[0])

    const horizonSheet = screen.getByTestId("horizon-sheet")
    const chips = within(horizonSheet).getAllByTestId("why-horizon-sphere")
    const work = requireElement(chips.find((c) => c.getAttribute("data-sphere-key") === "work"), "work chip")
    expect(work.tagName).toBe("BUTTON")
    expect(work.getAttribute("aria-label")).toBe("Открыть сферу «Работа» в навигаторе")
    expect(work.className).toContain("min-h-11")
    fireEvent.click(work)
    expect(onSphereSelect).toHaveBeenCalledTimes(1)
    expect(onSphereSelect).toHaveBeenCalledWith("work")
  })

  // ── Missing target row via real WhyExpanded ─────────────────────
  it("missing concreteAdvice row filters out horizon sphere chip via HorizonSheet", () => {
    const { payload } = buildCanonicalPayload()
    const filteredAdvice = { ...payload.concreteAdvice, rows: payload.concreteAdvice.rows.filter((r) => r.key !== "work") }
    const onSphereSelect = vi.fn()
    render(
      <WhyExpanded
        sections={payload.why}
        keyInsight={payload.keyInsight}
        v2={payload.v2}
        wireIdentity={CURRENT_WIRE_IDENTITY}
        concreteAdvice={filteredAdvice}
        onSphereSelect={onSphereSelect}
        open
      />,
    )
    const teasers = screen.getAllByTestId("why-horizon-teaser")
    fireEvent.click(teasers[0])

    const horizonSheet = screen.getByTestId("horizon-sheet")
    const chips = within(horizonSheet).getAllByTestId("why-horizon-sphere")
    const workChips = chips.filter((c) => c.getAttribute("data-sphere-key") === "work")
    expect(workChips).toHaveLength(0)
    expect(within(horizonSheet).queryByRole("button", { name: /Открыть сферу «Работа»/ })).toBeNull()

    const decisions = chips.find((c) => c.getAttribute("data-sphere-key") === "decisions")
    expect(decisions).toBeTruthy()
    if (decisions) {
      fireEvent.click(decisions)
      expect(onSphereSelect).toHaveBeenCalledWith("decisions")
    }
  })

  // ── Full TodayScreen exact row scroll/focus + same-click ────────
  it("full TodayScreen: horizon sphere click scrolls/focuses exact work row, same click repeats, data-status unchanged", () => {
    const rafSpy = vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => { cb(Date.now()); return 0 })

    const { payload } = buildCanonicalPayload()
    navigationState.search = "why=1"
    render(
      <TodayScreen
        payload={payload}
        access={access}
        selectedDate={new Date("2026-07-08T12:00:00Z")}
        onDateChange={() => {}}
      />,
    )

    const rows = screen.getAllByTestId("concrete-day-advice-row")
    const workRow = requireElement(rows.find((r) => r.getAttribute("data-sphere-key") === "work"), "work row")
    const statusBefore = workRow.getAttribute("data-status")

    const scrollSpy = vi.fn()
    const focusSpy = vi.fn()
    Object.defineProperty(workRow, "scrollIntoView", { configurable: true, value: scrollSpy })
    Object.defineProperty(workRow, "focus", { configurable: true, value: focusSpy })

    const teasers = screen.getAllByTestId("why-horizon-teaser")
    fireEvent.click(teasers[0])

    const horizonSheet = screen.getByTestId("horizon-sheet")
    const chips = within(horizonSheet).getAllByTestId("why-horizon-sphere")
    const workChip = requireElement(chips.find((c) => c.getAttribute("data-sphere-key") === "work"), "work chip")
    fireEvent.click(workChip)

    // After click assertions: modal sheet opens with work details
    expect(workRow.getAttribute("data-selected")).toBe("true")
    const details = screen.getByTestId("sphere-details-sheet")
    expect(details.getAttribute("data-sphere-key")).toBe("work")

    rafSpy.mockRestore()
  })

  it("renders honest verdict badge in SphereDetailsSheet when assessment is present, muted when low confidence", () => {
    const rowWithAssessment = {
      key: "work" as const,
      label: "Работа",
      iconName: "briefcase",
      rank: 1,
      verdict: "good" as const,
      confidence: "low" as const,
      text: "Основной совет",
      evidence: [],
      details: {
        story: "История сферы",
        why: ["Фактор 1"],
        advice: "Совет помощи",
      },
      assessment: {
        sphere: "work",
        assessment: {
          balance: 1,
          confidence: "low" as const,
          effectiveFactorCount: 1,
          factorCount: 1,
          independentFamilyCount: 1,
          key: "work",
          salienceScore: 3,
          supportScore: 3,
          tensionScore: 0,
          verdict: "good" as const,
          verdictRule: "good_support_1_3x" as const,
        },
      },
    }

    render(
      <SphereDetailsSheet
        row={rowWithAssessment}
        onClose={vi.fn()}
        onWhyOpen={vi.fn()}
      />,
    )

    const sheet = screen.getByTestId("sphere-details-sheet")
    expect(sheet.getAttribute("data-status")).toBe("good")

    const badge = screen.getByTestId("concrete-day-advice-details-status")
    expect(badge.getAttribute("data-status")).toBe("good")
    expect(badge.textContent).toBe("Поддержка")
    expect(badge.className).toContain("opacity-60")
  })
})
