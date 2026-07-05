// ############################################################################
// AI_HEADER: MODULE_HOOKS_USEACCESS_TEST
// ROLE: Unit tests for useAccess.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
import { beforeEach, describe, expect, it, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"

const { getAccess } = vi.hoisted(() => ({
  getAccess: vi.fn(),
}))

vi.mock("@/lib/api/access", () => ({
  getAccess,
}))

import { useAccess } from "@/hooks/use-access"

describe("useAccess", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getAccess.mockResolvedValue({
      state: "trial",
      hasAccess: true,
      accessStart: new Date("2026-07-01T00:00:00"),
      accessEnd: new Date("2026-07-08T00:00:00"),
      daysLeft: 8,
    })
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: vi.fn(() => "subscription"),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      },
      writable: true,
    })
  })

  it("loads real access state from the API", async () => {
    const { result } = renderHook(() => useAccess())

    await waitFor(() => expect(result.current.loaded).toBe(true))

    expect(getAccess).toHaveBeenCalledTimes(1)
    expect(result.current.state).toBe("trial")
    expect(result.current.access.daysLeft).toBe(8)
  })

  it("does not read or write localStorage access state", async () => {
    const { result } = renderHook(() => useAccess())
    await waitFor(() => expect(result.current.loaded).toBe(true))

    expect(window.localStorage.getItem).not.toHaveBeenCalled()
    expect(window.localStorage.setItem).not.toHaveBeenCalled()
  })

  it("exposes API failures and a closed access fallback", async () => {
    getAccess.mockRejectedValue(new Error("Session expired"))

    const { result } = renderHook(() => useAccess())
    await waitFor(() => expect(result.current.loaded).toBe(true))

    expect(result.current.error).toBe("Session expired")
    expect(result.current.state).toBe("none")
    expect(result.current.access.hasAccess).toBe(false)
  })
})
