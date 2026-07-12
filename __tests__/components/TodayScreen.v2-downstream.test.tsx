// ############################################################################
// AI_HEADER: MODULE_TODAYSCREEN_V2_DOWNSTREAM_TEST
// ROLE: Focused frontend tests for Stage B1 backend-owned horizons and legacy fallback.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-TODAYSCREEN-V2-DOWNSTREAM
// purpose: Prove TodayScreen/WhyExpanded preserve the original downstream matrix while extending it with backend-owned horizons coverage.
// owns:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// inputs: tracked downstream fixture, canonical dayPayloadV2 fixture, TodayScreen, WhyExpanded, ConcreteDayAdvice, presentation helpers.
// outputs: vitest assertions.
// dependencies: testing-library, vitest, fs/path, tracked fixture validator, canonical fixture, TodayScreen, WhyExpanded.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - backend horizons are authoritative when present.
//   - legacy selector remains reachable only when horizons are null/absent.
//   - original downstream audit/legacy assertions remain covered.
// failure_policy: test failure.
// END_MODULE_CONTRACT: M-TEST-TODAYSCREEN-V2-DOWNSTREAM

// START_MODULE_MAP: M-TEST-TODAYSCREEN-V2-DOWNSTREAM
// public_entrypoints: describe/it blocks
// semantic_blocks:
//   - FIXTURE_LOADING: tracked audit fixture loader and canonical fixture adapter.
//   - LEGACY_MATRIX: original downstream legacy scenarios preserved.
//   - BACKEND_HORIZONS_MATRIX: B1 backend-owned horizons coverage.
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP: M-TEST-TODAYSCREEN-V2-DOWNSTREAM

import { beforeEach, describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen, within } from "@testing-library/react"
import React from "react"
import fs from "node:fs"
import path from "node:path"
import type { AccessInfo } from "@/lib/contracts/access"
import { validateAdaptedTodayPayload } from "@/lib/contracts/today"
import { TodayScreen } from "@/components/today/today-screen"
import { ConcreteDayAdvice, normalizeConcreteAdviceVerdict } from "@/components/today/concrete-day-advice"
import { WhyExpanded } from "@/components/today/why-expanded"
import { DevAuditDrawer } from "@/components/today/dev-audit-drawer"
import { dayPayloadV2 } from "@/e2e/mock-visual/fixtures/day-v2-2026-07-08"
import { adaptTodayPayload } from "@/lib/adapters/today-payload"
import * as todayV2Presentation from "@/lib/presentation/today-v2"

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
    render(<WhyExpanded sections={[]} keyInsight="" v2={v2} />)

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
    render(<WhyExpanded sections={[]} keyInsight="" v2={v2} open />)

    expect(screen.getByTestId("why-today-item").textContent).toContain("Сегодня длинная тема особенно заметна")
    expect(screen.queryByTestId("why-time-horizon")).toBeNull()
    expect(screen.queryByText("Один личный сюжет идёт в трёх скоростях.")).toBeNull()
    expect(screen.queryByTestId("astrology-calculation-toggle")).toBeNull()
  })

  it("returns no Why block for an empty V2 payload without safe copy or legacy sections", () => {
    const { payload } = buildCanonicalPayload()
    const v2 = structuredClone(payload.v2!)
    v2.horizons = null
    v2.activationSummary.topActivatedTargets = []
    v2.activationEvidence = []
    v2.whyToday = []
    v2.scoreBreakdown = {}
    const { queryByTestId } = render(<WhyExpanded sections={[]} keyInsight="" v2={v2} open />)

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
    render(<WhyExpanded sections={[]} keyInsight="" v2={v2} open />)

    expect(screen.getAllByTestId("why-time-horizon")).toHaveLength(3)
    expect(screen.queryByTestId("why-time-horizon-timing")).toBeNull()
  })

  it("renders normalized visible verdict statuses on compact rows and expanded details", () => {
    const { payload } = buildCanonicalPayload()
    const expected = {
      good: { compact: "Поддержка", details: "Поддерживающий фон" },
      neutral: { compact: "Ровно", details: "Нейтральный фон" },
      caution: { compact: "Внимание", details: "Требует внимания" },
      avoid: { compact: "Отложить", details: "Высокое напряжение · лучше отложить" },
    } as const
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

    for (const [verdict, copy] of Object.entries(expected)) {
      const row = screen.getAllByTestId("concrete-day-advice-row").find((element) => element.getAttribute("data-status") === verdict)!
      const status = row.querySelector('[data-testid="concrete-day-advice-row-status"]')
      expect(status?.getAttribute("data-status")).toBe(verdict)
      expect(status?.textContent).toBe(copy.compact)
    }
    expect(normalizeConcreteAdviceVerdict("unknown_backend_value")).toBe("neutral")

    for (const [verdict, copy] of Object.entries(expected)) {
      const selectedRow = screen.getAllByTestId("concrete-day-advice-row").find((element) => element.getAttribute("data-status") === verdict)!
      const selectedKey = selectedRow.getAttribute("data-sphere-key")!
      rerender(renderNavigator(selectedKey))
      const details = screen.getByTestId("concrete-day-advice-details")
      const badge = screen.getByTestId("concrete-day-advice-details-status")
      const currentRow = screen.getAllByTestId("concrete-day-advice-row").find((element) => element.getAttribute("data-sphere-key") === selectedKey)!
      expect(details.getAttribute("data-status")).toBe(verdict)
      expect(badge.getAttribute("data-status")).toBe(verdict)
      expect(badge.textContent).toBe(copy.details)
      expect(currentRow.getAttribute("aria-expanded")).toBe("true")
      expect(currentRow.getAttribute("aria-controls")).toBe(details.getAttribute("id"))
    }
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

  it("renders backend intro and three ordered why-horizon cards from v2.horizons", () => {
    renderBackendWhyExpanded()

    const block = screen.getByTestId("why-horizons")
    expect(block.getAttribute("data-state")).toBe("ready")
    expect(block.getAttribute("data-source")).toBe("backend-horizons")
    expect(block.textContent).toContain("Личная логика периода")
    expect(block.textContent).toContain("Опору сейчас лучше перестраивать без резких движений")
    expect(block.textContent).toContain("Долгий цикл меняет отношение к ответственности и контролю")

    const cards = screen.getAllByTestId("why-horizon")
    expect(cards.map((item) => item.getAttribute("data-horizon"))).toEqual(["long", "medium", "fast"])
    expect(cards.map((item) => item.getAttribute("data-status"))).toEqual(["mixed", "mixed", "tense"])
    expect(cards.map((item) => item.getAttribute("data-timing-state"))).toEqual(["background", "building", "peaked"])
    expect(screen.queryByTestId("why-time-horizon")).toBeNull()
    expect(screen.queryByTestId("astrology-calculation")).toBeNull()
  })

  it("uses backend timing labels and visible tone text without recalculation", () => {
    renderBackendWhyExpanded()

    const [longCard, mediumCard, fastCard] = screen.getAllByTestId("why-horizon")
    expect(within(longCard).getByTestId("why-horizon-timing").textContent).toContain("12 мая 2026 — 11 мая 2027")
    expect(within(longCard).getByTestId("why-horizon-timing").textContent).toContain("Фон уже действует")
    expect(within(mediumCard).getByTestId("why-horizon-timing").textContent).toContain("3–18 июля")
    expect(within(mediumCard).getByTestId("why-horizon-timing").textContent).toContain("Точный пик — 10 июля, 14:32 по Москве")
    expect(within(mediumCard).getByTestId("why-horizon-timing").textContent).toContain("Набирает силу")
    expect(within(fastCard).getByTestId("why-horizon-timing").textContent).toContain("8–10 июля по Москве")
    expect(within(fastCard).getByTestId("why-horizon-timing").textContent).toContain("Пик был 8 июля в 08:00")
    expect(within(fastCard).getByTestId("why-horizon-timing").textContent).toContain("Пик уже пройден")
    expect(within(longCard).getByTestId("why-horizon-tone").getAttribute("data-status")).toBe("mixed")
    expect(within(mediumCard).getByTestId("why-horizon-tone").getAttribute("data-status")).toBe("mixed")
    expect(within(fastCard).getByTestId("why-horizon-tone").getAttribute("data-status")).toBe("tense")
    expect(screen.getAllByText("Смешанный фон")).toHaveLength(2)
    expect(screen.getByText("Напряжённый фон")).toBeTruthy()
  })

  it("renders backend actions, optional strength/risk, and manifestation conditions", () => {
    renderBackendWhyExpanded()

    const [longCard, mediumCard, fastCard] = screen.getAllByTestId("why-horizon")
    expect(within(longCard).getByTestId("why-horizon-actions").querySelectorAll("li")).toHaveLength(2)
    expect(within(longCard).getByTestId("why-horizon-avoid").querySelectorAll("li")).toHaveLength(1)
    expect(longCard.textContent).toContain("Эта рамка актуальна до 11 мая 2027")
    expect(within(longCard).getByTestId("why-horizon-strength")).toBeTruthy()
    expect(within(longCard).getByTestId("why-horizon-risk")).toBeTruthy()
    expect(longCard.textContent).toContain("Если сейчас вы обсуждаете новую роль или объём ответственности…")

    expect(within(mediumCard).getByTestId("why-horizon-actions").querySelectorAll("li")).toHaveLength(2)
    expect(within(mediumCard).getByTestId("why-horizon-avoid").querySelectorAll("li")).toHaveLength(1)
    expect(mediumCard.textContent).toContain("Этот эксперимент актуален до 18 июля")
    expect(within(mediumCard).getByTestId("why-horizon-strength")).toBeTruthy()
    expect(within(mediumCard).getByTestId("why-horizon-risk")).toBeTruthy()

    expect(within(fastCard).getByTestId("why-horizon-actions").querySelectorAll("li")).toHaveLength(1)
    expect(within(fastCard).getByTestId("why-horizon-avoid").querySelectorAll("li")).toHaveLength(1)
    expect(screen.queryAllByTestId("why-horizon-strength")).toHaveLength(2)
    expect(within(fastCard).getByTestId("why-horizon-risk")).toBeTruthy()
  })

  it("renders per-card technical disclosures closed by default and opens associated content", () => {
    renderBackendWhyExpanded()

    const toggles = screen.getAllByTestId("why-horizon-technical-toggle")
    expect(toggles).toHaveLength(3)
    for (const toggle of toggles) {
      expect(toggle.getAttribute("aria-expanded")).toBe("false")
    }

    fireEvent.click(toggles[0])
    expect(toggles[0].getAttribute("aria-expanded")).toBe("true")
    const content = screen.getByTestId("why-horizon-technical-content")
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

    fireEvent.click(screen.getByRole("button", { name: "Почему именно у меня" }))
    const sphereButtons = screen.getAllByTestId("why-horizon-sphere")
    expect(sphereButtons.some((button) => button.textContent === "Работа")).toBe(true)

    fireEvent.click(sphereButtons.find((button) => button.textContent === "Работа")!)
    const details = screen.getByTestId("concrete-day-advice-details")
    expect(details.getAttribute("data-sphere-key")).toBe("work")
    expect(details.textContent).toContain("Не форсируйте разговор о статусе")
  })

  it("does not call selectWhyTimeHorizons when backend horizons exist", () => {
    const spy = vi.spyOn(todayV2Presentation, "selectWhyTimeHorizons")
    renderBackendWhyExpanded()
    expect(spy).not.toHaveBeenCalled()
  })

  it("keeps raw prefixes and legacy cards absent when backend block exists", () => {
    renderBackendWhyExpanded()
    const text = screen.getByTestId("why-horizons").textContent ?? ""
    expect(text).not.toContain("Transit_")
    expect(text).not.toContain("Natal_")
    expect(screen.queryByTestId("why-time-horizon")).toBeNull()
  })

  it("restores legacy selector cards when horizons are null", () => {
    const { payload } = buildCanonicalPayload()
    const v2 = structuredClone(payload.v2!)
    v2.horizons = null
    const spy = vi.spyOn(todayV2Presentation, "selectWhyTimeHorizons")
    render(
      <WhyExpanded
        sections={payload.why}
        keyInsight={payload.keyInsight}
        v2={v2}
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
})
