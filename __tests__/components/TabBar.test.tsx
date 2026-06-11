// ############################################################################
// AI_HEADER: TabBar.test — TabBar component unit tests
// ROLE: Verifies TabBar renders all 5 navigation tabs with correct labels,
//   hrefs, data-testid attributes, aria-current active state based on pathname,
//   and title attributes matching visible labels. 18 tests total.
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Provides comprehensive unit-test coverage for the TabBar component.
//   Vitest + @testing-library/react assertions. Covers pathname matching,
//   accessibility attributes, fallback behaviour, and all 5 tab states.
// inputs: TabBar component from @/components/today/tab-bar.
//   returns: 18 test cases, all expect pass.
// side_effects: Mocks next/navigation, lucide-react, @/lib/log, @/lib/today, @/lib/date.
// emitted_logs: None (logger is mocked).
// error_behavior: N/A (tests, not production code).
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - describe: TabBar
//   - test: renders nav with today-tab-bar data-testid
//   - test: renders all 5 tabs
//   - test: highlights "Сегодня" tab as active when pathname is /
//   - test: has correct hrefs for all tabs
//   - test: renders correct tab labels
//   - test: highlights "Календарь" tab as active when pathname is /calendar
//   - test: highlights "Спросить" tab as active when pathname is /chat
//   - test: falls back to "/" when usePathname returns null
//   - test: has data-testid on each tab link
//   - test: sets aria-current="page" on the active tab
//   - test: highlights "Профиль" tab as active when pathname is /profile
//   - test: has title attribute equal to visible label on every tab link
//   - test: active tab has aria-label with "текущий раздел" suffix
//   - test: inactive tab link has plain label as aria-label
//   - test: all 5 tab links have aria-label attribute
//   - test: highlights "Календарь" — aria-label changes when active
//   - test: highlights "Спросить" — aria-label changes when active
//   - test: highlights "Профиль" — all tabs have correct aria-label
// END_MODULE_MAP

import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import React from "react"

vi.mock("@/lib/log", () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

// START_BLOCK_MOCKS
const { mockPathname } = vi.hoisted(() => ({
  mockPathname: vi.fn(() => "/"),
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }),
  usePathname: () => mockPathname(),
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
}))

vi.mock("lucide-react", () => ({
  Sun: () => <span data-testid="icon-sun" />,
  CalendarDays: () => <span data-testid="icon-calendar" />,
  BookOpen: () => <span data-testid="icon-book" />,
  User: () => <span data-testid="icon-user" />,
  MessageCircle: () => <span data-testid="icon-message" />,
}))

vi.mock("@/lib/today", () => ({
  TODAY: new Date("2026-06-01T12:00:00Z"),
}))

vi.mock("@/lib/date", () => ({
  toDateParam: () => "2026-06-01",
}))
// END_BLOCK_MOCKS

import { TabBar } from "@/components/today/tab-bar"

// START_BLOCK_TESTS
describe("TabBar", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockPathname.mockReturnValue("/")
  })

  // START_FUNCTION_CONTRACT
  // name: renders nav with today-tab-bar data-testid
  // purpose: Confirms the nav element carries the expected testid.
  // END_FUNCTION_CONTRACT
  it("renders nav with today-tab-bar data-testid", () => {
    render(<TabBar />)
    expect(screen.getByTestId("today-tab-bar")).toBeTruthy()
  })

  // START_FUNCTION_CONTRACT
  // name: renders all 5 tabs
  // purpose: Verifies each Russian label string appears in the DOM.
  // END_FUNCTION_CONTRACT
  it("renders all 5 tabs", () => {
    render(<TabBar />)
    expect(screen.getByText("Сегодня")).toBeTruthy()
    expect(screen.getByText("Календарь")).toBeTruthy()
    expect(screen.getByText("Разборы")).toBeTruthy()
    expect(screen.getByText("Спросить")).toBeTruthy()
    expect(screen.getByText("Профиль")).toBeTruthy()
  })

  // START_FUNCTION_CONTRACT
  // name: highlights "Сегодня" tab as active when pathname is /
  // purpose: Checks aria-current="page" on today tab and null on calendar tab.
  // END_FUNCTION_CONTRACT
  it("highlights \"Сегодня\" tab as active when pathname is /", () => {
    render(<TabBar />)
    const todayLink = screen.getByText("Сегодня").closest("a")
    expect(todayLink?.getAttribute("aria-current")).toBe("page")
    const calendarLink = screen.getByText("Календарь").closest("a")
    expect(calendarLink?.getAttribute("aria-current")).toBeNull()
  })

  // START_FUNCTION_CONTRACT
  // name: has correct hrefs for all tabs
  // purpose: Ensures all 5 link href values are present in the DOM.
  // END_FUNCTION_CONTRACT
  it("has correct hrefs for all tabs", () => {
    render(<TabBar />)
    const links = screen.getAllByRole("link")
    const hrefs = links.map((l) => l.getAttribute("href"))
    expect(hrefs).toContain("/calendar")
    expect(hrefs).toContain("/readings")
    expect(hrefs).toContain("/chat")
    expect(hrefs).toContain("/profile")
  })

  // START_FUNCTION_CONTRACT
  // name: renders correct tab labels
  // purpose: Double-checks the 5 Russian labels render without crashing.
  // END_FUNCTION_CONTRACT
  it("renders correct tab labels", () => {
    render(<TabBar />)
    const labels = ["Сегодня", "Календарь", "Разборы", "Спросить", "Профиль"]
    for (const label of labels) {
      expect(screen.getByText(label)).toBeTruthy()
    }
  })

  // START_FUNCTION_CONTRACT
  // name: highlights "Календарь" tab as active when pathname is /calendar
  // purpose: Verifies calendar tab gets aria-current="page" and today tab loses it.
  // END_FUNCTION_CONTRACT
  it("highlights \"Календарь\" tab as active when pathname is /calendar", () => {
    mockPathname.mockReturnValue("/calendar")
    render(<TabBar />)
    const calendarLink = screen.getByText("Календарь").closest("a")
    expect(calendarLink?.getAttribute("aria-current")).toBe("page")
    const todayLink = screen.getByText("Сегодня").closest("a")
    expect(todayLink?.getAttribute("aria-current")).toBeNull()
  })

  // START_FUNCTION_CONTRACT
  // name: highlights "Спросить" tab as active when pathname is /chat
  // purpose: Verifies chat tab gets aria-current="page" on /chat path.
  // END_FUNCTION_CONTRACT
  it("highlights \"Спросить\" tab as active when pathname is /chat", () => {
    mockPathname.mockReturnValue("/chat")
    render(<TabBar />)
    const chatLink = screen.getByText("Спросить").closest("a")
    expect(chatLink?.getAttribute("aria-current")).toBe("page")
  })

  // START_FUNCTION_CONTRACT
  // name: falls back to "/" when usePathname returns null
  // purpose: Ensures null pathname falls back to "/" which matches today tab.
  // END_FUNCTION_CONTRACT
  it("falls back to \"/\" when usePathname returns null", () => {
    mockPathname.mockReturnValue(null as any)
    render(<TabBar />)
    const todayLink = screen.getByText("Сегодня").closest("a")
    expect(todayLink?.getAttribute("aria-current")).toBe("page")
  })

  // START_FUNCTION_CONTRACT
  // name: has data-testid on each tab link
  // purpose: Ensures every tab link has a unique data-testid for E2E selectors.
  // END_FUNCTION_CONTRACT
  it("has data-testid on each tab link", () => {
    render(<TabBar />)
    expect(screen.getByTestId("today-tab-today")).toBeTruthy()
    expect(screen.getByTestId("today-tab-calendar")).toBeTruthy()
    expect(screen.getByTestId("today-tab-readings")).toBeTruthy()
    expect(screen.getByTestId("today-tab-chat")).toBeTruthy()
    expect(screen.getByTestId("today-tab-profile")).toBeTruthy()
  })

  // START_FUNCTION_CONTRACT
  // name: sets aria-current="page" on the active tab
  // purpose: On "/", today tab has aria-current="page", others have null.
  // END_FUNCTION_CONTRACT
  it("sets aria-current=\"page\" on the active tab", () => {
    render(<TabBar />)
    const todayLink = screen.getByText("Сегодня").closest("a")
    expect(todayLink?.getAttribute("aria-current")).toBe("page")
    const calendarLink = screen.getByText("Календарь").closest("a")
    expect(calendarLink?.getAttribute("aria-current")).toBeNull()
    const chatLink = screen.getByText("Спросить").closest("a")
    expect(chatLink?.getAttribute("aria-current")).toBeNull()
  })

  // START_FUNCTION_CONTRACT
  // name: highlights "Профиль" tab as active when pathname is /profile
  // purpose: Verifies profile tab has aria-current and all others are null.
  // END_FUNCTION_CONTRACT
  it("highlights \"Профиль\" tab as active when pathname is /profile", () => {
    mockPathname.mockReturnValue("/profile")
    render(<TabBar />)
    expect(screen.getByTestId("today-tab-profile").getAttribute("aria-current")).toBe("page")
    expect(screen.getByTestId("today-tab-today").getAttribute("aria-current")).toBeNull()
    expect(screen.getByTestId("today-tab-calendar").getAttribute("aria-current")).toBeNull()
    expect(screen.getByTestId("today-tab-readings").getAttribute("aria-current")).toBeNull()
    expect(screen.getByTestId("today-tab-chat").getAttribute("aria-current")).toBeNull()
  })

  // START_FUNCTION_CONTRACT
  // name: has title attribute equal to visible label on every tab link
  // purpose: Ensures each tab link has a title matching its Russian label for a11y.
  // END_FUNCTION_CONTRACT
  it("has title attribute equal to visible label on every tab link", () => {
    render(<TabBar />)
    const expectations: Record<string, string> = {
      "today-tab-today": "Сегодня",
      "today-tab-calendar": "Календарь",
      "today-tab-readings": "Разборы",
      "today-tab-chat": "Спросить",
      "today-tab-profile": "Профиль",
    }
    for (const [testId, expectedTitle] of Object.entries(expectations)) {
      const link = screen.getByTestId(testId)
      expect(link.getAttribute("title")).toBe(expectedTitle)
    }
  })

  // START_FUNCTION_CONTRACT
  // name: active tab has aria-label with "текущий раздел" suffix
  // purpose: On pathname /, the today tab aria-label includes "текущий раздел".
  // END_FUNCTION_CONTRACT
  it("active tab has aria-label with \"текущий раздел\" suffix", () => {
    render(<TabBar />)
    const todayLink = screen.getByTestId("today-tab-today")
    expect(todayLink.getAttribute("aria-label")).toBe("Сегодня, текущий раздел")
  })

  // START_FUNCTION_CONTRACT
  // name: inactive tab link has plain label as aria-label
  // purpose: On pathname /, non-active tabs have plain label as aria-label.
  // END_FUNCTION_CONTRACT
  it("inactive tab link has plain label as aria-label", () => {
    render(<TabBar />)
    const calendarLink = screen.getByTestId("today-tab-calendar")
    expect(calendarLink.getAttribute("aria-label")).toBe("Календарь")
  })

  // START_FUNCTION_CONTRACT
  // name: all 5 tab links have aria-label attribute
  // purpose: Ensures every tab link sets aria-label regardless of active state.
  // END_FUNCTION_CONTRACT
  it("all 5 tab links have aria-label attribute", () => {
    render(<TabBar />)
    const ids = ["today-tab-today", "today-tab-calendar", "today-tab-readings", "today-tab-chat", "today-tab-profile"]
    for (const id of ids) {
      expect(screen.getByTestId(id).getAttribute("aria-label")).toBeTruthy()
    }
  })

  // START_FUNCTION_CONTRACT
  // name: highlights "Календарь" — aria-label changes when active
  // purpose: On /calendar, calendar tab gets suffix; today tab gets plain label.
  // END_FUNCTION_CONTRACT
  it("highlights \"Календарь\" — aria-label changes when active", () => {
    mockPathname.mockReturnValue("/calendar")
    render(<TabBar />)
    expect(screen.getByTestId("today-tab-calendar").getAttribute("aria-label")).toBe("Календарь, текущий раздел")
    expect(screen.getByTestId("today-tab-today").getAttribute("aria-label")).toBe("Сегодня")
  })

  // START_FUNCTION_CONTRACT
  // name: highlights "Спросить" — aria-label changes when active
  // purpose: On /chat, chat tab gets suffix; today tab stays plain.
  // END_FUNCTION_CONTRACT
  it("highlights \"Спросить\" — aria-label changes when active", () => {
    mockPathname.mockReturnValue("/chat")
    render(<TabBar />)
    expect(screen.getByTestId("today-tab-chat").getAttribute("aria-label")).toBe("Спросить, текущий раздел")
    expect(screen.getByTestId("today-tab-today").getAttribute("aria-label")).toBe("Сегодня")
  })

  // START_FUNCTION_CONTRACT
  // name: highlights "Профиль" — all tabs have correct aria-label
  // purpose: On /profile, only profile tab has suffix; all others plain.
  // END_FUNCTION_CONTRACT
  it("highlights \"Профиль\" — all tabs have correct aria-label", () => {
    mockPathname.mockReturnValue("/profile")
    render(<TabBar />)
    expect(screen.getByTestId("today-tab-profile").getAttribute("aria-label")).toBe("Профиль, текущий раздел")
    expect(screen.getByTestId("today-tab-today").getAttribute("aria-label")).toBe("Сегодня")
    expect(screen.getByTestId("today-tab-calendar").getAttribute("aria-label")).toBe("Календарь")
    expect(screen.getByTestId("today-tab-readings").getAttribute("aria-label")).toBe("Разборы")
    expect(screen.getByTestId("today-tab-chat").getAttribute("aria-label")).toBe("Спросить")
  })
})
// END_BLOCK_TESTS
