
// ############################################################################
// AI_HEADER: MODULE_NATAL_NATAL_COMPONENT_STATES_TEST
// ROLE: Unit tests for natal-component-states.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for natal-component-statestsx behavior
// owns:
//   - __tests__/natal/natal-component-states.test.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
/**
 * Component render tests for real preview, retry, and backend error states.
 */

import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react"
import React from "react"

import type { NatalPreviewRead } from "@/lib/contracts/natal"

// ---- Mock next/navigation ----

const mockPush = vi.fn()
const mockReplace = vi.fn()
const mockRouter = {
  push: mockPush,
  replace: mockReplace,
  back: vi.fn(),
  forward: vi.fn(),
  refresh: vi.fn(),
  prefetch: vi.fn(),
}

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  usePathname: () => "/readings/natal",
  useSearchParams: () => new URLSearchParams(),
}))

// ---- Mock API client ----

const mockFetchNatalGenerate = vi.fn()
const mockFetchNatalReport = vi.fn()
const mockFetchNatalPreview = vi.fn()

vi.mock("@/lib/api/natal", () => ({
  fetchNatalGenerate: (...args: unknown[]) => mockFetchNatalGenerate(...args),
  fetchNatalReport: (...args: unknown[]) => mockFetchNatalReport(...args),
  fetchNatalPreview: (...args: unknown[]) => mockFetchNatalPreview(...args),
}))

// ---- Mock lucide-react with all needed icons ----

vi.mock("lucide-react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("lucide-react")>()
  const FakeIcon = (props: Record<string, unknown>) =>
    React.createElement("span", { "data-testid": `icon-${String(props?.className || "icon").slice(0, 10)}` })
  return {
    ...actual,
    ChevronLeft: FakeIcon,
    ChevronRight: FakeIcon,
    Sparkles: FakeIcon,
    AlertTriangle: FakeIcon,
    RefreshCw: FakeIcon,
    Lock: FakeIcon,
  }
})

// ---- Mock framer-motion ----

vi.mock("framer-motion", () => ({
  motion: {
    button: React.forwardRef(({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>, ref: React.Ref<HTMLButtonElement>) =>
      React.createElement("button", { ...props, ref }, children)),
    div: React.forwardRef(({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>, ref: React.Ref<HTMLDivElement>) =>
      React.createElement("div", { ...props, ref }, children)),
  },
  AnimatePresence: ({ children }: React.PropsWithChildren) => children,
}))

// ---- Mock child components used by the pages ----

vi.mock("@/components/readings/natal-preview/natal-generating-screen", () => ({
  NatalGeneratingScreen: ({ onComplete, isLive }: { onComplete: () => void; isLive: boolean }) =>
    React.createElement("div", { "data-testid": "generating-screen" },
      React.createElement("span", null, `isLive=${isLive}`),
      React.createElement("button", { onClick: onComplete, "data-testid": "demo-complete" }, "Complete")
    ),
}))

// ============================================================
// Tests
// ============================================================

const VALID_PREVIEW_WITH_CHART: NatalPreviewRead = {
  meta: {
    name: "Backend User",
    birthDate: "2000-01-01",
    birthCity: "Moscow",
    houseSystem: "Placidus",
    ascSign: "Aries",
    gender: "female",
  },
  chart: {
    houseSystem: "Placidus",
    planets: [
      { name: "Sun", sign: "Aries", degree: 10, house: 1, retrograde: false, longitude: 10 },
      { name: "Moon", sign: "Leo", degree: 10, house: 5, retrograde: false, longitude: 130 },
    ],
    houses: [
      { number: 1, sign: "Aries", degree: 0, longitude: 0 },
      { number: 2, sign: "Taurus", degree: 0, longitude: 30 },
    ],
    aspects: [
      { planetA: "Sun", planetB: "Moon", aspectType: "trine", orb: 1.2, applying: null },
    ],
    angles: [
      { name: "ASC", sign: "Aries", degree: 15, longitude: 15 },
      { name: "MC", sign: "Capricorn", degree: 10, longitude: 280 },
    ],
  },
  highlights: [
    { id: "sun", title: "Солнце", value: "Овен", description: "Ядро личности" },
    { id: "moon", title: "Луна", value: "Лев", description: "Эмоциональный тон" },
  ],
  spheres: [
    { id: "self", title: "Личность", score: 4.5, rank: 1, description: "Сильная сфера" },
  ],
  planets: [
    { id: "sun", name: "Солнце", sign: "Овен", house: 1, score: null, description: "Солнце в Овне" },
  ],
  chapters: [
    { id: "portrait", eyebrow: "Полный разбор", title: "Портрет", locked: true, description: "Описание" },
  ],
  personalHook: "Ты собрана",
  calculationStats: {
    planetsCount: 2,
    housesCount: 2,
    aspectsCount: 1,
    spheresCount: 1,
    specialPointsCount: 0,
    scoringFactorsCount: 0,
    dignityFactorsCount: 0,
    totalFactorsCount: 6,
    displayLabel: "6 факторов",
  },
  salesBullets: ["Поймёшь себя"],
  fullReportAvailable: false,
  fullReportPriceKopecks: 99900,
}

describe("NatalChartWheel — supplied chart rendering", () => {
  it("renders SVG content from supplied backend chart only", async () => {
    const { NatalChartWheel } = await import("@/components/readings/natal-chart-wheel")

    render(<NatalChartWheel chart={VALID_PREVIEW_WITH_CHART.chart} birthLabel="2000-01-01" />)

    const chart = screen.getByTestId("natal-chart")
    expect(chart.querySelector("svg")).toBeTruthy()
    expect(chart.textContent).toContain("☉")
    expect(chart.textContent).toContain("Placidus")
    expect(chart.querySelectorAll("line").length).toBeGreaterThan(0)
  })

  it("renders supplied angle markers for ASC and MC", async () => {
    const { NatalChartWheel } = await import("@/components/readings/natal-chart-wheel")

    render(<NatalChartWheel chart={VALID_PREVIEW_WITH_CHART.chart} birthLabel="2000-01-01" />)

    expect(screen.getByTestId("natal-angle-ASC").textContent).toContain("ASC")
    expect(screen.getByTestId("natal-angle-MC").textContent).toContain("MC")
  })

  it("does not fabricate angle markers when they are absent from the payload", async () => {
    const { NatalChartWheel } = await import("@/components/readings/natal-chart-wheel")

    render(
      <NatalChartWheel
        chart={{
          ...VALID_PREVIEW_WITH_CHART.chart!,
          angles: [{ name: "ASC", sign: "Aries", degree: 15, longitude: 15 }],
        }}
      />,
    )

    expect(screen.getByTestId("natal-angle-ASC").textContent).toContain("ASC")
    expect(screen.queryByTestId("natal-angle-MC")).toBeNull()
  })

  it("renders an unavailable state when chart is absent", async () => {
    const { NatalChartWheel } = await import("@/components/readings/natal-chart-wheel")

    render(<NatalChartWheel chart={null} />)

    expect(screen.getByTestId("natal-chart-unavailable").textContent).toContain("Натальная карта недоступна")
  })
})

describe("NatalReadingPage — natal chart preview", () => {
  beforeEach(() => {
    mockPush.mockReset()
    mockReplace.mockReset()
    mockFetchNatalPreview.mockReset()
  })

  it("renders the chart wheel from real preview.chart data", async () => {
    const NatalReadingPage = (await import("@/app/(grace)/readings/natal/page")).default

    mockFetchNatalPreview.mockResolvedValue({
      ok: true,
      data: VALID_PREVIEW_WITH_CHART,
    })

    render(<NatalReadingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("natal-chart")).toBeTruthy()
    })
  })

  it("keeps the full report CTA disabled while fulfillment is unavailable", async () => {
    const NatalReadingPage = (await import("@/app/(grace)/readings/natal/page")).default

    mockFetchNatalPreview.mockResolvedValue({
      ok: true,
      data: VALID_PREVIEW_WITH_CHART,
    })

    render(<NatalReadingPage />)

    const button = await screen.findByRole("button", { name: "Полный отчёт скоро появится" })
    expect((button as HTMLButtonElement).disabled).toBe(true)

    fireEvent.click(button)
    expect(mockPush).not.toHaveBeenCalled()
  })
})

describe("NatalGeneratingPage — retry behavior", () => {
  beforeEach(() => {
    mockPush.mockReset()
    mockReplace.mockReset()
    mockFetchNatalGenerate.mockReset()
    mockFetchNatalReport.mockReset()
    mockFetchNatalPreview.mockReset()
    mockFetchNatalPreview.mockResolvedValue({
      ok: true,
      data: {
        meta: { name: "Backend User", birthDate: "2000-01-01", gender: "female" },
        fullReportPriceKopecks: 99900,
      },
    })
  })

  it("loads real preview data before starting generation", async () => {
    const NatalGeneratingPage = (await import("@/app/(grace)/readings/natal/generating/page")).default

    mockFetchNatalGenerate.mockResolvedValue({
      ok: true,
      data: { reportId: "gen-123", status: "GENERATING" },
    })

    render(<NatalGeneratingPage />)

    await waitFor(() => {
      expect(mockFetchNatalPreview).toHaveBeenCalledTimes(1)
      expect(mockFetchNatalGenerate).toHaveBeenCalledWith(false)
    })
    expect(screen.getByText(/Backend User/)).toBeTruthy()
  })

  it("renders an error when real preview data is unavailable", async () => {
    const NatalGeneratingPage = (await import("@/app/(grace)/readings/natal/generating/page")).default

    mockFetchNatalPreview.mockResolvedValueOnce({
      ok: false,
      error: { type: "error", message: "Preview unavailable" },
    })

    render(<NatalGeneratingPage />)

    await waitFor(() => {
      expect(screen.getAllByText(/Preview unavailable/).length).toBeGreaterThan(0)
    })
    expect(mockFetchNatalGenerate).not.toHaveBeenCalled()
  })

  it("retry button calls fetchNatalGenerate(true) after FAILED_RETRYABLE", async () => {
    const NatalGeneratingPage = (await import("@/app/(grace)/readings/natal/generating/page")).default

    // First call: initial generation returns FAILED_RETRYABLE
    mockFetchNatalGenerate.mockResolvedValueOnce({
      ok: true,
      data: {
        reportId: "fail-123",
        status: "FAILED_RETRYABLE",
        errorMessage: "LLM timeout",
      },
    })

    // Second call: retry with forceRegenerate=true returns READY
    mockFetchNatalGenerate.mockResolvedValueOnce({
      ok: true,
      data: {
        reportId: "new-456",
        status: "READY",
      },
    })

    // Default: safe fallback for any additional calls
    mockFetchNatalGenerate.mockResolvedValue({
      ok: true,
      data: { reportId: "default", status: "GENERATING" },
    })

    render(<NatalGeneratingPage />)

    // Wait for the failed_retryable state to appear
    await waitFor(() => {
      expect(screen.getByText(/Ошибка генерации/i)).toBeTruthy()
    }, { timeout: 10000 })

    // Click retry button
    const retryBtn = screen.getByText(/Попробовать ещё раз/i)
    await act(async () => {
      fireEvent.click(retryBtn)
    })

    // Verify fetchNatalGenerate was called with forceRegenerate=true
    expect(mockFetchNatalGenerate).toHaveBeenCalledWith(true)
    // Verify redirect to the new report
    expect(mockReplace).toHaveBeenCalledWith("/readings/natal/new-456")
  }, 15000)
})

describe("NatalReportPage — retry and demo isolation", () => {
  beforeEach(() => {
    mockPush.mockReset()
    mockReplace.mockReset()
    mockFetchNatalGenerate.mockReset()
    mockFetchNatalReport.mockReset()
    // Default: return a safe fallback so unhandled calls don't throw
    mockFetchNatalGenerate.mockResolvedValue({
      ok: true,
      data: { reportId: "default", status: "GENERATING" },
    })
    mockFetchNatalReport.mockResolvedValue({
      ok: true,
      data: { id: "default", status: "GENERATING", accessState: "FREE_PREVIEW", meta: { houseSystem: "Placidus", promptVersion: "1" }, sections: [] },
    })
  })

  it("shows not_found for demo reportId in production", async () => {
    const NatalReportPage = (await import("@/app/(grace)/readings/natal/[id]/page")).default

    // fetchNatalReport("demo") returns not_found in production
    mockFetchNatalReport.mockResolvedValueOnce({
      ok: false,
      error: { type: "not_found", message: "Report not found" },
    })

    // Create a wrapper that provides params as Promise (Next.js 15 style)
    function Wrapper() {
      const params = Promise.resolve({ id: "demo" })
      return React.createElement(NatalReportPage, { params })
    }

    await act(async () => {
      render(
        <React.Suspense fallback={<div>Loading</div>}>
          <Wrapper />
        </React.Suspense>
      )
    })

    await waitFor(() => {
      expect(screen.getByText(/Отчёт не найден/i)).toBeTruthy()
    }, { timeout: 5000 })
  })

  it("retry button handles GENERATING status from backend", async () => {
    const NatalReportPage = (await import("@/app/(grace)/readings/natal/[id]/page")).default

    // First: report page loads a FAILED_RETRYABLE report
    mockFetchNatalReport.mockResolvedValueOnce({
      ok: true,
      data: {
        id: "fail-123",
        status: "FAILED_RETRYABLE",
        accessState: "FREE_PREVIEW",
        meta: { houseSystem: "Placidus", promptVersion: "1" },
        sections: [],
        errorMessage: "Generation failed",
      },
    })

    // Then: retry calls generate, which returns GENERATING
    mockFetchNatalGenerate.mockResolvedValueOnce({
      ok: true,
      data: {
        reportId: "gen-456",
        status: "GENERATING",
        sectionsAvailable: false,
      },
    })

    function Wrapper() {
      const params = Promise.resolve({ id: "fail-123" })
      return React.createElement(NatalReportPage, { params })
    }

    await act(async () => {
      render(
        <React.Suspense fallback={<div>Loading</div>}>
          <Wrapper />
        </React.Suspense>
      )
    })

    // Wait for failed state
    await waitFor(() => {
      expect(screen.getByText(/Не удалось создать разбор/i)).toBeTruthy()
    }, { timeout: 5000 })

    // Click retry
    const retryBtn = screen.getByText(/Попробовать ещё раз/i)
    await act(async () => {
      fireEvent.click(retryBtn)
    })

    // Should show "generating" state (not generic error)
    await waitFor(() => {
      expect(screen.getByText(/Отчёт ещё генерируется/i)).toBeTruthy()
    }, { timeout: 5000 })
  })

  it("retry button handles FAILED_PERMANENT from backend", async () => {
    const NatalReportPage = (await import("@/app/(grace)/readings/natal/[id]/page")).default

    // Report loads as FAILED_RETRYABLE
    mockFetchNatalReport.mockResolvedValueOnce({
      ok: true,
      data: {
        id: "fail-789",
        status: "FAILED_RETRYABLE",
        accessState: "FREE_PREVIEW",
        meta: { houseSystem: "Placidus", promptVersion: "1" },
        sections: [],
        errorMessage: "Temporary failure",
      },
    })

    // Retry returns FAILED_PERMANENT
    mockFetchNatalGenerate.mockResolvedValueOnce({
      ok: true,
      data: {
        reportId: "perm-789",
        status: "FAILED_PERMANENT",
        errorMessage: "Profile missing",
      },
    })

    function Wrapper() {
      const params = Promise.resolve({ id: "fail-789" })
      return React.createElement(NatalReportPage, { params })
    }

    await act(async () => {
      render(
        <React.Suspense fallback={<div>Loading</div>}>
          <Wrapper />
        </React.Suspense>
      )
    })

    // Wait for initial failed state
    await waitFor(() => {
      expect(screen.getByText(/Не удалось создать разбор/i)).toBeTruthy()
    }, { timeout: 5000 })

    // Click retry
    const retryBtn = screen.getByText(/Попробовать ещё раз/i)
    await act(async () => {
      fireEvent.click(retryBtn)
    })

    // After FAILED_PERMANENT, the retry button should disappear (retryable=false)
    await waitFor(() => {
      expect(screen.queryByText(/Попробовать ещё раз/i)).toBeNull()
    }, { timeout: 5000 })

    // The permanent failure message should be shown
    expect(screen.getByText(/Profile missing/i)).toBeTruthy()
  })

  it("handles GENERATING report on initial load", async () => {
    const NatalReportPage = (await import("@/app/(grace)/readings/natal/[id]/page")).default

    mockFetchNatalReport.mockResolvedValueOnce({
      ok: true,
      data: {
        id: "gen-123",
        status: "GENERATING",
        accessState: "FREE_PREVIEW",
        meta: { houseSystem: "Placidus", promptVersion: "1" },
        sections: [],
      },
    })

    function Wrapper() {
      const params = Promise.resolve({ id: "gen-123" })
      return React.createElement(NatalReportPage, { params })
    }

    await act(async () => {
      render(
        <React.Suspense fallback={<div>Loading</div>}>
          <Wrapper />
        </React.Suspense>
      )
    })

    await waitFor(() => {
      expect(screen.getByText(/Отчёт ещё генерируется/i)).toBeTruthy()
    }, { timeout: 5000 })
  })
})
