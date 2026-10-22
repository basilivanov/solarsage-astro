// ############################################################################
// AI_HEADER: MODULE_TESTS_RELEASE_VERSION_CHECK
// ROLE: Unit tests for build/server release sha comparison and the manual update banner.
// DEPENDENCIES: vitest, @testing-library/react, components/release-version-check
// GRACE_ANCHORS: [RELEASE_VERSION_CHECK_TESTS]
// WAVE: W-CACHE-DELIVERY-HARDENING
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-RELEASE-VERSION-CHECK
// purpose: Verify mismatch/ match/ unknown-sha/ fetch-failure behavior and the
//   mount plus visibilitychange probes of ReleaseVersionCheck.
// owns:
//   - __tests__/components/release-version-check.test.tsx
// inputs: mocked NEXT_PUBLIC_RELEASE_SHA, /api/health fetch, document visibility events
// outputs: Vitest assertions
// dependencies:
//   - M-RELEASE-VERSION-CHECK (ReleaseVersionCheck)
// side_effects: none (test harness)
// emitted_logs: none
// invariants:
//   - banner appears only when both shas are known and differ
//   - click calls window.location.reload
//   - fetch errors never surface
// failure_policy: raise assertion failures
// END_MODULE_CONTRACT: M-TESTS-RELEASE-VERSION-CHECK

// START_MODULE_MAP: M-TESTS-RELEASE-VERSION-CHECK
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - MISMATCH_BANNER: banner and reload click
//   - MATCH_NO_BANNER: equal release shas
//   - UNKNOWN_NO_FETCH: empty/unknown build sha
//   - FAILURE_SILENT: rejected health request
//   - VISIBILITY_RECHECK: resume probe
// owned_tests:
//   - __tests__/components/release-version-check.test.tsx
// END_MODULE_MAP: M-TESTS-RELEASE-VERSION-CHECK

import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { ReleaseVersionCheck } from "@/components/release-version-check"

const originalBuildSha = process.env.NEXT_PUBLIC_RELEASE_SHA

function setBuildSha(value: string | undefined): void {
  if (value === undefined) {
    delete process.env.NEXT_PUBLIC_RELEASE_SHA
    return
  }
  process.env.NEXT_PUBLIC_RELEASE_SHA = value
}

function healthResponse(releaseSha: string): Response {
  return {
    ok: true,
    json: async () => ({ release_sha: releaseSha }),
  } as Response
}

beforeEach(() => {
  setBuildSha("build-sha")
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  setBuildSha(originalBuildSha)
})

describe("ReleaseVersionCheck", () => {
  it("shows the banner on a release mismatch and reloads only on click", async () => {
    const fetchMock = vi.fn().mockResolvedValue(healthResponse("server-sha"))
    vi.stubGlobal("fetch", fetchMock)

    render(<ReleaseVersionCheck />)

    const banner = await screen.findByTestId("release-update-banner")
    expect(banner.getAttribute("role")).toBe("status")
    expect(banner.textContent).toContain("Доступна новая версия")
    expect(fetchMock).toHaveBeenCalledWith("/api/health", { cache: "no-store" })

    const reload = vi.fn()
    vi.stubGlobal("window", {
      ...window,
      location: { ...window.location, reload },
    })

    fireEvent.click(screen.getByTestId("release-update-reload"))
    expect(reload).toHaveBeenCalledTimes(1)
  })

  it("does not show the banner when build and server shas match", async () => {
    const fetchMock = vi.fn().mockResolvedValue(healthResponse("build-sha"))
    vi.stubGlobal("fetch", fetchMock)

    render(<ReleaseVersionCheck />)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    expect(screen.queryByTestId("release-update-banner")).toBeNull()
  })

  it.each([
    ["empty", ""],
    ["unknown", "unknown"],
  ])("does not fetch when build sha is %s", async (_label, buildSha) => {
    setBuildSha(buildSha)
    const fetchMock = vi.fn()
    vi.stubGlobal("fetch", fetchMock)

    render(<ReleaseVersionCheck />)

    expect(fetchMock).not.toHaveBeenCalled()
    expect(screen.queryByTestId("release-update-banner")).toBeNull()
  })

  it("keeps the app unchanged when the health request fails", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error("network unavailable"))
    vi.stubGlobal("fetch", fetchMock)

    render(<ReleaseVersionCheck />)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    expect(screen.queryByTestId("release-update-banner")).toBeNull()
  })

  it("rechecks the release when the document becomes visible", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(healthResponse("build-sha"))
      .mockResolvedValueOnce(healthResponse("new-server-sha"))
    vi.stubGlobal("fetch", fetchMock)

    render(<ReleaseVersionCheck />)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    expect(screen.queryByTestId("release-update-banner")).toBeNull()

    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"))
    })

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(await screen.findByTestId("release-update-banner")).toBeTruthy()
  })
})
