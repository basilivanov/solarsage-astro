/**
 * Wave 5 follow-up: component render tests for retry, demo, and error states.
 *
 * Non-blocking Note 1 from Wave 5 acceptance review:
 * "Component click behavior is still not tested directly."
 *
 * Tests cover:
 * - Generating page: retry button calls fetchNatalGenerate(true)
 * - Report page: retry button handles GENERATING/PENDING from backend
 * - Report page: production /readings/natal/demo shows not_found
 */

import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react"
import React from "react"

// ---- Mock next/navigation ----

const mockPush = vi.fn()
const mockReplace = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/readings/natal",
  useSearchParams: () => new URLSearchParams(),
}))

// ---- Mock IS_DEMO_MODE ----

let mockDemoMode = false

vi.mock("@/lib/demo-mode", () => ({
  get IS_DEMO_MODE() {
    return mockDemoMode
  },
}))

// ---- Mock API client ----

const mockFetchNatalGenerate = vi.fn()
const mockFetchNatalReport = vi.fn()

vi.mock("@/lib/api/natal", () => ({
  fetchNatalGenerate: (...args: unknown[]) => mockFetchNatalGenerate(...args),
  fetchNatalReport: (...args: unknown[]) => mockFetchNatalReport(...args),
  fetchNatalPreview: vi.fn(),
}))

// ---- Mock demo-data ----

vi.mock("@/lib/demo-data", () => ({
  DEMO_NATAL_PREVIEW: {
    meta: { name: "Test", birthDate: "2000-01-01", gender: "female" },
    fullReportPriceKopecks: 99900,
  },
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

describe("NatalGeneratingPage — retry behavior", () => {
  beforeEach(() => {
    mockDemoMode = false
    mockPush.mockReset()
    mockReplace.mockReset()
    mockFetchNatalGenerate.mockReset()
    mockFetchNatalReport.mockReset()
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

    await act(async () => {
      render(
        <React.Suspense fallback={<div>Loading</div>}>
          <NatalGeneratingPage />
        </React.Suspense>
      )
    })

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
    mockDemoMode = false
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
