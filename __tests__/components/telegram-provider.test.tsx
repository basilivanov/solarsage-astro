// ############################################################################
// AI_HEADER: MODULE_TESTS_TELEGRAM_PROVIDER
// ROLE: Unit tests for TelegramProvider initData resolution (hash fallback, late initData, script src)
// DEPENDENCIES: vitest, @testing-library/react, components/telegram-provider, lib/telegram/init-data
// GRACE_ANCHORS: [TELEGRAM_PROVIDER_TESTS]
// WAVE: W-AUTH-TIMEOUT-RACE-FIX
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-TELEGRAM-PROVIDER
// purpose: Validate that inTelegram does not depend on a single SDK load moment — hash fallback, late initData re-checks, failure/timeout paths and the self-hosted SDK src.
// owns:
//   - __tests__/components/telegram-provider.test.tsx
// inputs: jsdom window.Telegram fixtures, URL hash, synthetic script load/error events, fake timers
// outputs: Vitest test execution assertions
// dependencies:
//   - M-TELEGRAM-PROVIDER (TelegramProvider, useTelegram)
//   - M-TELEGRAM-INIT-DATA (parseTgWebAppDataFromHash)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-TELEGRAM-PROVIDER

// START_MODULE_MAP: M-TESTS-TELEGRAM-PROVIDER
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - HASH_FALLBACK: tgWebAppData in hash without SDK initData
//   - LATE_INIT_DATA: initData appears after the SDK resolved empty
//   - LOAD_FAILURE: missing Telegram + script error/timeout
//   - SELF_HOSTED_SRC: vendored SDK served from our origin
// owned_tests:
//   - __tests__/components/telegram-provider.test.tsx
// END_MODULE_MAP: M-TESTS-TELEGRAM-PROVIDER

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent, act, cleanup } from "@testing-library/react"

import { TelegramProvider, useTelegram } from "@/components/telegram-provider"
import { parseTgWebAppDataFromHash } from "@/lib/telegram/init-data"

const SCRIPT_ID = "telegram-web-app-sdk"

function Probe() {
  const { webApp, loaded, inTelegram } = useTelegram()
  return (
    <div
      data-testid="probe"
      data-loaded={String(loaded)}
      data-in-telegram={String(inTelegram)}
      data-has-web-app={String(!!webApp)}
    />
  )
}

function renderProvider() {
  render(
    <TelegramProvider>
      <Probe />
    </TelegramProvider>,
  )
}

function probe() {
  return screen.getByTestId("probe")
}

function injectedScript(): HTMLScriptElement {
  const script = document.getElementById(SCRIPT_ID)
  if (!script) throw new Error("Telegram SDK script was not injected")
  return script as HTMLScriptElement
}

function resetWindow() {
  delete (window as { Telegram?: unknown }).Telegram
  window.history.replaceState({}, "", "/")
  document.getElementById(SCRIPT_ID)?.remove()
}

beforeEach(() => {
  resetWindow()
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.restoreAllMocks()
  resetWindow()
})

describe("M-TELEGRAM-INIT-DATA — hash parsing", () => {
  it("decodes percent-encoded tgWebAppData from the location hash", () => {
    const initData = "auth_date=1700000000&user=%7B%22id%22%3A7%7D&hash=abc123"
    window.history.replaceState({}, "", `/#tgWebAppData=${encodeURIComponent(initData)}&tgWebAppVersion=7.0`)

    expect(parseTgWebAppDataFromHash()).toBe(initData)
  })

  it("returns an empty string when the hash has no tgWebAppData", () => {
    window.history.replaceState({}, "", "/#tgWebAppVersion=7.0")

    expect(parseTgWebAppDataFromHash()).toBe("")
  })
})

describe("TelegramProvider — initData without a single load moment", () => {
  it("is hydration-safe: no Telegram context before the SDK script resolves", () => {
    renderProvider()

    expect(probe().getAttribute("data-loaded")).toBe("false")
    expect(probe().getAttribute("data-in-telegram")).toBe("false")
    expect(probe().getAttribute("data-has-web-app")).toBe("false")
  })

  it("detects Telegram from the tgWebAppData hash even when the SDK sets no initData", () => {
    const initData = "auth_date=1700000000&user=%7B%22id%22%3A7%7D&hash=abc123"
    window.history.replaceState({}, "", `/today#tgWebAppData=${encodeURIComponent(initData)}`)

    renderProvider()

    // Hash fallback is only published once the SDK script resolves.
    expect(probe().getAttribute("data-loaded")).toBe("false")
    fireEvent.load(injectedScript())

    expect(probe().getAttribute("data-loaded")).toBe("true")
    expect(probe().getAttribute("data-in-telegram")).toBe("true")
  })

  it("flips inTelegram to true when initData appears after an empty SDK resolve", () => {
    vi.useFakeTimers()
    const webApp = { initData: "" }
    ;(window as { Telegram?: unknown }).Telegram = { WebApp: webApp }

    renderProvider()

    expect(probe().getAttribute("data-loaded")).toBe("true")
    expect(probe().getAttribute("data-in-telegram")).toBe("false")

    webApp.initData = "auth_date=1700000000&hash=late-signature"

    act(() => {
      vi.advanceTimersByTime(250)
    })

    expect(probe().getAttribute("data-in-telegram")).toBe("true")
  })

  it("keeps inTelegram false while initData never appears", () => {
    vi.useFakeTimers()
    ;(window as { Telegram?: unknown }).Telegram = { WebApp: { initData: "" } }

    renderProvider()

    act(() => {
      vi.advanceTimersByTime(2_000)
    })

    expect(probe().getAttribute("data-loaded")).toBe("true")
    expect(probe().getAttribute("data-in-telegram")).toBe("false")
  })

  it("marks loaded without inTelegram when the script fails to load", () => {
    renderProvider()

    fireEvent.error(injectedScript())

    expect(probe().getAttribute("data-loaded")).toBe("true")
    expect(probe().getAttribute("data-in-telegram")).toBe("false")
  })

  it("marks loaded without inTelegram after the 10s safety timeout", () => {
    vi.useFakeTimers()

    renderProvider()

    expect(probe().getAttribute("data-loaded")).toBe("false")

    act(() => {
      vi.advanceTimersByTime(10_000)
    })

    expect(probe().getAttribute("data-loaded")).toBe("true")
    expect(probe().getAttribute("data-in-telegram")).toBe("false")
  })

  it("loads the vendored SDK from our own origin", () => {
    renderProvider()

    const script = injectedScript()

    expect(script.getAttribute("src")).toBe("/telegram-web-app.js")
    expect(script.getAttribute("src")).not.toContain("telegram.org")
    expect(script.getAttribute("async")).toBe("true")
  })
})
