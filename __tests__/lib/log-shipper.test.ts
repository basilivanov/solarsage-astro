// ############################################################################
// AI_HEADER: MODULE_LIB_LOG_SHIPPER_TEST
// ROLE: Unit tests for log-shipper.ts (Slice 19)
// DEPENDENCIES: vitest, lib/log/shipper
// GRACE_ANCHORS: [LOG_SHIPPER_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-LOG-SHIPPER
// purpose: Validate envelope batching, retries, exponential backoff, jitter, notBefore bounds, unload sendBeacon/fetch fallbacks, and test reset cleanup for LogShipper.
// owns:
//   - __tests__/lib/log-shipper.test.ts
// inputs: mock fetch, mock sendBeacon, CanonEnvelope fixtures
// outputs: Vitest assertion results
// dependencies:
//   - M-LOG-SHIPPER (lib/log/shipper)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-LOG-SHIPPER

// START_MODULE_MAP: M-TESTS-LOG-SHIPPER
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - BATCHING_TESTS: test maxBatchSize and wait timer batching
//   - UNLOAD_TESTS: test sendBeacon success, false fallback, throw fallback, and buffer preservation
//   - RETRY_TESTS: test automatic retry on network/429/5xx, non-retryable 4xx, and 5 attempt max limit
//   - BACKOFF_TESTS: test exponential backoff calculation and jitter bounds
// owned_tests:
//   - __tests__/lib/log-shipper.test.ts
// END_MODULE_MAP: M-TESTS-LOG-SHIPPER

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { getLogShipper, resetLogShipperForTests, CanonEnvelope, LogShipper } from "@/lib/log/shipper"

const mockFetch = vi.fn()
const mockSendBeacon = vi.fn().mockReturnValue(true)
const capturedHandlers: Record<string, Array<() => void>> = {}

const originalSendBeaconDescriptor = typeof navigator !== "undefined"
  ? Object.getOwnPropertyDescriptor(navigator, "sendBeacon")
  : undefined

function envelope(msg: string, payload?: Record<string, unknown>): CanonEnvelope {
  return {
    ts: new Date().toISOString(),
    level: "info",
    env: "test",
    service: "web",
    service_version: "test",
    slice: "W-TEST",
    module: "M-TEST-SHIPPER",
    block: "TEST_ENVELOPE",
    event: "system.request",
    correlation_id: "test-corr-id",
    msg,
    payload,
  }
}

describe("LogShipper — Slice 19 Unload Fallbacks & GRACE", () => {
  beforeEach(() => {
    vi.resetModules()
    resetLogShipperForTests()
    mockFetch.mockReset().mockResolvedValue({ ok: true, status: 200 })
    mockSendBeacon.mockReset().mockReturnValue(true)

    vi.stubGlobal("fetch", mockFetch)

    Object.defineProperty(navigator, "sendBeacon", {
      value: mockSendBeacon,
      writable: true,
      configurable: true,
    })

    Object.keys(capturedHandlers).forEach((k) => delete capturedHandlers[k])
    vi.spyOn(window, "addEventListener").mockImplementation((event: string, handler: any) => {
      if (!capturedHandlers[event]) capturedHandlers[event] = []
      capturedHandlers[event].push(handler)
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    resetLogShipperForTests()
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()

    if (originalSendBeaconDescriptor) {
      Object.defineProperty(navigator, "sendBeacon", originalSendBeaconDescriptor)
    } else {
      delete (navigator as any).sendBeacon
    }
  })

  async function createShipper(opts?: { shipping?: boolean; logLevel?: string }): Promise<LogShipper> {
    vi.stubEnv("NEXT_PUBLIC_GRACE_LOG_SHIPPING", opts?.shipping !== false ? "true" : "false")
    vi.stubEnv("NEXT_PUBLIC_LOG_LEVEL", opts?.logLevel || "info")
    resetLogShipperForTests()
    return getLogShipper()
  }

  it("enqueue adds to buffer without flushing (under batch size)", async () => {
    const shipper = await createShipper()
    shipper.enqueue(envelope("hello"))
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it("flush sends batch to /api/_log", async () => {
    const shipper = await createShipper()
    shipper.enqueue(envelope("hello"))
    await shipper.flush()
    expect(mockFetch).toHaveBeenCalledTimes(1)
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toBe("/api/_log")
    const body = JSON.parse(init.body)
    expect(body.envelopes).toHaveLength(1)
    expect(body.envelopes[0].msg).toBe("hello")
  })

  it("batch flushes when maxBatchSize reached (50)", async () => {
    const shipper = await createShipper()
    for (let i = 0; i < 50; i++) {
      shipper.enqueue(envelope(`msg-${i}`))
    }
    expect(mockFetch).toHaveBeenCalledTimes(1)
    const body = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(body.envelopes).toHaveLength(50)
  })

  it("timer flushes after maxWaitMs (5000)", async () => {
    vi.useFakeTimers()
    const shipper = await createShipper()
    shipper.enqueue(envelope("tick"))
    expect(mockFetch).not.toHaveBeenCalled()
    vi.advanceTimersByTime(5000)
    expect(mockFetch).toHaveBeenCalledTimes(1)
    const body = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(body.envelopes).toHaveLength(1)
  })

  it("flushSync uses sendBeacon on beforeunload with canonical envelopes only (no attempt/notBefore) when sendBeacon returns true", async () => {
    const shipper = await createShipper()
    shipper.enqueue(envelope("goodbye"))
    expect(mockSendBeacon).not.toHaveBeenCalled()

    const handlers = capturedHandlers["beforeunload"] ?? []
    expect(handlers.length).toBeGreaterThanOrEqual(1)
    handlers[0]()

    expect(mockSendBeacon).toHaveBeenCalledTimes(1)
    expect(mockFetch).not.toHaveBeenCalled()

    const [url, blob] = mockSendBeacon.mock.calls[0]
    expect(url).toBe("/api/_log")

    const bodyText = await new Promise<string>((resolve) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as string)
      reader.readAsText(blob as Blob)
    })

    const parsed = JSON.parse(bodyText)
    expect(parsed.envelopes).toBeDefined()
    expect(parsed.envelopes).toHaveLength(1)
    expect(parsed.envelopes[0].msg).toBe("goodbye")
    expect(parsed.envelopes[0]).not.toHaveProperty("attempt")
    expect(parsed.envelopes[0]).not.toHaveProperty("notBefore")
  })

  it("flushSync falls back to keepalive fetch when sendBeacon returns false", async () => {
    mockSendBeacon.mockReturnValue(false)
    const shipper = await createShipper()

    shipper.enqueue(envelope("fallback-msg"))

    const handlers = capturedHandlers["pagehide"] ?? []
    expect(handlers.length).toBeGreaterThanOrEqual(1)
    handlers[0]()

    expect(mockSendBeacon).toHaveBeenCalledTimes(1)
    expect(mockFetch).toHaveBeenCalledTimes(1)

    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toBe("/api/_log")
    expect(init.method).toBe("POST")
    expect(init.keepalive).toBe(true)
    expect(init.credentials).toBe("include")

    const body = JSON.parse(init.body)
    expect(body.envelopes).toHaveLength(1)
    expect(body.envelopes[0].msg).toBe("fallback-msg")
  })

  it("flushSync falls back to keepalive fetch when sendBeacon throws an error", async () => {
    mockSendBeacon.mockImplementation(() => {
      throw new Error("QuotaExceededError")
    })
    const shipper = await createShipper()

    shipper.enqueue(envelope("throw-fallback"))

    const handlers = capturedHandlers["beforeunload"] ?? []
    expect(handlers.length).toBeGreaterThanOrEqual(1)
    handlers[0]()

    expect(mockSendBeacon).toHaveBeenCalledTimes(1)
    expect(mockFetch).toHaveBeenCalledTimes(1)

    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toBe("/api/_log")
    expect(init.keepalive).toBe(true)
    expect(JSON.parse(init.body).envelopes[0].msg).toBe("throw-fallback")
  })

  it("flushSync safely returns batch to buffer on JSON serialization failure without throwing", async () => {
    const shipper = await createShipper()

    // Create invalid envelope with BigInt payload
    const invalidEnvelope = envelope("broken", { badNum: BigInt(100) as any })
    shipper.enqueue(invalidEnvelope)

    const handlers = capturedHandlers["beforeunload"] ?? []
    expect(handlers.length).toBeGreaterThanOrEqual(1)

    // Must NOT throw
    expect(() => handlers[0]()).not.toThrow()

    // Envelope preserved in buffer! Replace invalid payload with valid one to verify buffer intact
    invalidEnvelope.payload = { fixed: true }
    await shipper.flush()

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const body = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(body.envelopes[0].msg).toBe("broken")
    expect(body.envelopes[0].payload).toEqual({ fixed: true })
  })

  it("flushSync safely returns batch to buffer when fallback fetch throws synchronously", async () => {
    mockSendBeacon.mockReturnValue(false)
    mockFetch.mockImplementationOnce(() => {
      throw new Error("Sync fetch failure")
    })

    const shipper = await createShipper()
    shipper.enqueue(envelope("fetch-sync-fail"))

    const handlers = capturedHandlers["beforeunload"] ?? []
    expect(() => handlers[0]()).not.toThrow()

    // Batch preserved in buffer for next flush!
    mockFetch.mockResolvedValueOnce({ ok: true, status: 200 })
    await shipper.flush()

    expect(mockFetch).toHaveBeenCalledTimes(2)
    const body = JSON.parse(mockFetch.mock.calls[1][1].body)
    expect(body.envelopes[0].msg).toBe("fetch-sync-fail")
  })

  it("debug mode flushes each eligible enqueue immediately, producing 2 requests for 2 sequential enqueues after completion", async () => {
    const shipper = await createShipper({ logLevel: "debug" })

    shipper.enqueue(envelope("debug-1"))
    await shipper.flush()
    expect(mockFetch).toHaveBeenCalledTimes(1)

    shipper.enqueue(envelope("debug-2"))
    await shipper.flush()
    expect(mockFetch).toHaveBeenCalledTimes(2)

    const body1 = JSON.parse(mockFetch.mock.calls[0][1].body)
    const body2 = JSON.parse(mockFetch.mock.calls[1][1].body)
    expect(body1.envelopes[0].msg).toBe("debug-1")
    expect(body2.envelopes[0].msg).toBe("debug-2")
  })

  it("calculates exponential backoff with bounded jitter (attempt 1 ≈ 1s, attempt 2 ≈ 2s)", async () => {
    const shipper = await createShipper()

    expect(shipper.calculateBackoff(1, 0)).toBe(800)
    expect(shipper.calculateBackoff(1, 0.5)).toBe(1000)
    expect(shipper.calculateBackoff(1, 1)).toBe(1200)

    expect(shipper.calculateBackoff(2, 0)).toBe(1600)
    expect(shipper.calculateBackoff(2, 0.5)).toBe(2000)
    expect(shipper.calculateBackoff(2, 1)).toBe(2400)

    expect(shipper.calculateBackoff(3, 0.5)).toBe(4000)
    expect(shipper.calculateBackoff(10, 0.5)).toBe(30000)
  })

  it("automatically retries on network error, 429, and 5xx", async () => {
    vi.useFakeTimers()
    const shipper = await createShipper()

    mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"))
    shipper.enqueue(envelope("network-fail"))
    await shipper.flush()
    expect(mockFetch).toHaveBeenCalledTimes(1)

    mockFetch.mockResolvedValueOnce({ ok: false, status: 429 })
    await vi.advanceTimersByTimeAsync(1500)
    expect(mockFetch).toHaveBeenCalledTimes(2)

    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 })
    await vi.advanceTimersByTimeAsync(3000)
    expect(mockFetch).toHaveBeenCalledTimes(3)

    mockFetch.mockResolvedValueOnce({ ok: true, status: 200 })
    await vi.advanceTimersByTimeAsync(5000)
    expect(mockFetch).toHaveBeenCalledTimes(4)
  })

  it("drops non-retryable 4xx errors (e.g. 400, 404) immediately without retry", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 404 })
    const shipper = await createShipper()

    shipper.enqueue(envelope("not-found"))
    await shipper.flush()
    expect(mockFetch).toHaveBeenCalledTimes(1)

    mockFetch.mockResolvedValueOnce({ ok: true, status: 200 })
    shipper.enqueue(envelope("fresh-msg"))
    await shipper.flush()
    expect(mockFetch).toHaveBeenCalledTimes(2)

    const body = JSON.parse(mockFetch.mock.calls[1][1].body)
    expect(body.envelopes).toHaveLength(1)
    expect(body.envelopes[0].msg).toBe("fresh-msg")
  })

  it("drops envelope silently after maximum 5 send attempts", async () => {
    vi.useFakeTimers()
    const shipper = await createShipper()

    for (let i = 0; i < 5; i++) {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 })
    }

    shipper.enqueue(envelope("drop-me"))

    await shipper.flush()
    expect(mockFetch).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(1500)
    await vi.advanceTimersByTimeAsync(3000)
    await vi.advanceTimersByTimeAsync(6000)
    await vi.advanceTimersByTimeAsync(12000)
    expect(mockFetch).toHaveBeenCalledTimes(5)

    mockFetch.mockClear()
    await vi.advanceTimersByTimeAsync(30000)
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it("automatically sends fresh enqueue on standard 5s timer without manual flush while old retry has backoff >5s", async () => {
    vi.useFakeTimers()
    const shipper = await createShipper()

    vi.spyOn(shipper, "calculateBackoff").mockReturnValue(8000)

    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 })
    shipper.enqueue(envelope("old-retryable"))
    await shipper.flush()
    expect(mockFetch).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(1000)

    mockFetch.mockResolvedValueOnce({ ok: true, status: 200 })
    shipper.enqueue(envelope("fresh-event"))

    await vi.advanceTimersByTimeAsync(5000)

    expect(mockFetch).toHaveBeenCalledTimes(2)
    const body2 = JSON.parse(mockFetch.mock.calls[1][1].body)
    expect(body2.envelopes).toHaveLength(1)
    expect(body2.envelopes[0].msg).toBe("fresh-event")

    mockFetch.mockResolvedValueOnce({ ok: true, status: 200 })
    await vi.advanceTimersByTimeAsync(3000)

    expect(mockFetch).toHaveBeenCalledTimes(3)
    const body3 = JSON.parse(mockFetch.mock.calls[2][1].body)
    expect(body3.envelopes).toHaveLength(1)
    expect(body3.envelopes[0].msg).toBe("old-retryable")
  })

  it("prevents duplicate concurrent flush calls during in-flight HTTP request", async () => {
    let resolveFetch: any
    const fetchPromise = new Promise((resolve) => {
      resolveFetch = resolve
    })
    mockFetch.mockReturnValue(fetchPromise)

    const shipper = await createShipper()
    shipper.enqueue(envelope("concurrent-1"))

    const p1 = shipper.flush()
    const p2 = shipper.flush()

    expect(mockFetch).toHaveBeenCalledTimes(1)

    resolveFetch({ ok: true, status: 200 })
    await Promise.all([p1, p2])
  })

  it("does not lose events enqueued during in-flight HTTP request", async () => {
    let resolveFetch: any
    mockFetch.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve
        })
    )

    const shipper = await createShipper()
    shipper.enqueue(envelope("in-flight-1"))

    const flushPromise = shipper.flush()
    expect(mockFetch).toHaveBeenCalledTimes(1)

    shipper.enqueue(envelope("in-flight-2"))

    mockFetch.mockResolvedValueOnce({ ok: true, status: 200 })
    resolveFetch({ ok: true, status: 200 })

    await flushPromise

    await shipper.flush()
    expect(mockFetch).toHaveBeenCalledTimes(2)
    const body2 = JSON.parse(mockFetch.mock.calls[1][1].body)
    expect(body2.envelopes[0].msg).toBe("in-flight-2")
  })

  it("resetLogShipperForTests clears timers and event listeners without error", async () => {
    vi.useFakeTimers()
    const removeSpy = vi.spyOn(window, "removeEventListener")

    const shipper = await createShipper()
    shipper.enqueue(envelope("reset-me"))

    resetLogShipperForTests()

    expect(removeSpy).toHaveBeenCalledWith("beforeunload", expect.any(Function))
    expect(removeSpy).toHaveBeenCalledWith("pagehide", expect.any(Function))

    vi.advanceTimersByTime(10000)
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it("enabled=false skips shipping", async () => {
    const shipper = await createShipper({ shipping: false })
    shipper.enqueue(envelope("secret"))
    expect(mockFetch).not.toHaveBeenCalled()
    await shipper.flush()
    expect(mockFetch).not.toHaveBeenCalled()
  })
})
