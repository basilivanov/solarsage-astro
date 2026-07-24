// ############################################################################
// AI_HEADER: MODULE_LIB_LOGGER_TEST
// ROLE: Unit tests for lib/log/index.ts (Slice 18)
// DEPENDENCIES: vitest, lib/log/index, lib/log/shipper
// GRACE_ANCHORS: [LOGGER_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-LOGGER
// purpose: Validate envelope creation, sampling rules, level filtering, PII redaction, and correlation management for frontend logger.
// owns:
//   - __tests__/lib/logger.test.ts
// inputs: mock shipper enqueue, log events and sampling options
// outputs: Vitest assertion results
// dependencies:
//   - M-LOG-FRONTEND (lib/log)
//   - M-LOG-SHIPPER (getLogShipper mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-LOGGER

// START_MODULE_MAP: M-TESTS-LOGGER
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - SAMPLING_TESTS: test deterministic sampling rates, NaN/Infinity fail-open, and error/fatal bypass
//   - ENVELOPE_TESTS: test envelope creation, error/http/phase meta, and correlation ID
//   - REDACTION_TESTS: test PII redaction in msg and payload
// owned_tests:
//   - __tests__/lib/logger.test.ts
// END_MODULE_MAP: M-TESTS-LOGGER

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

const { mockEnqueue } = vi.hoisted(() => ({
  mockEnqueue: vi.fn(),
}))

vi.mock("@/lib/log/shipper", () => ({
  getLogShipper: () => ({ enqueue: mockEnqueue }),
}))

import {
  logger,
  logEvent,
  logStart,
  logSuccess,
  logFailure,
  setCorrelationId,
  getCorrelationId,
  setLogContext,
} from "@/lib/log"

let consoleLogSpy: any

beforeEach(() => {
  mockEnqueue.mockClear()
  setCorrelationId("")
  setLogContext("", "", "")
  consoleLogSpy = vi.spyOn(console, "log").mockImplementation(() => {})
})

afterEach(() => {
  setLogContext("", "", "")
  setCorrelationId("")
  vi.unstubAllEnvs()
  vi.restoreAllMocks()
})

describe("Logger — Sampling & Deterministic Rules (Slice 18)", () => {
  it("drops info/warn event when sample_rate is 0 without calling Math.random", () => {
    const randomSpy = vi.spyOn(Math, "random")

    logEvent("ui.fetch_started", {}, { level: "info", sample_rate: 0 })
    expect(mockEnqueue).not.toHaveBeenCalled()
    expect(randomSpy).not.toHaveBeenCalled()

    logEvent("ui.fetch_started", {}, { level: "warn", sample_rate: 0 })
    expect(mockEnqueue).not.toHaveBeenCalled()
  })

  it("always emits info event when sample_rate is 1", () => {
    logEvent("ui.fetch_started", {}, { level: "info", sample_rate: 1 })
    expect(mockEnqueue).toHaveBeenCalledTimes(1)
  })

  it("emits iff Math.random() < sample_rate when 0 < sample_rate < 1", () => {
    // Below rate -> emit
    vi.spyOn(Math, "random").mockReturnValue(0.3)
    logEvent("ui.fetch_started", {}, { level: "info", sample_rate: 0.5 })
    expect(mockEnqueue).toHaveBeenCalledTimes(1)

    mockEnqueue.mockClear()

    // Equal to rate -> drop
    vi.spyOn(Math, "random").mockReturnValue(0.5)
    logEvent("ui.fetch_started", {}, { level: "info", sample_rate: 0.5 })
    expect(mockEnqueue).not.toHaveBeenCalled()

    // Above rate -> drop
    vi.spyOn(Math, "random").mockReturnValue(0.8)
    logEvent("ui.fetch_started", {}, { level: "info", sample_rate: 0.5 })
    expect(mockEnqueue).not.toHaveBeenCalled()
  })

  it("fails open and emits event when sample_rate is NaN or Infinity", () => {
    logEvent("ui.fetch_started", {}, { level: "info", sample_rate: NaN })
    expect(mockEnqueue).toHaveBeenCalledTimes(1)

    mockEnqueue.mockClear()

    logEvent("ui.fetch_started", {}, { level: "info", sample_rate: Infinity })
    expect(mockEnqueue).toHaveBeenCalledTimes(1)
  })

  it("never samples error or fatal events even when sample_rate is 0", () => {
    const randomSpy = vi.spyOn(Math, "random")

    logEvent("frontend.runtime_failed", {}, { level: "error", sample_rate: 0 })
    expect(mockEnqueue).toHaveBeenCalledTimes(1)

    mockEnqueue.mockClear()

    logEvent("frontend.runtime_failed", {}, { level: "fatal", sample_rate: 0 })
    expect(mockEnqueue).toHaveBeenCalledTimes(1)

    expect(randomSpy).not.toHaveBeenCalled()
  })
})

describe("Logger — v2 observability extension", () => {
  it("includes error, http, operation_id, and phase top-level in envelope", () => {
    logEvent("frontend.runtime_failed", { route: "/test" }, {
      level: "error",
      msg: "Test error",
      error: { kind: "TestError", secret: "secret@example.com" },
      http: { method: "POST", route_template: "/api/test", status: 500 },
      operation_id: "op-123",
      phase: "render",
    })

    expect(mockEnqueue).toHaveBeenCalledTimes(1)
    const env = mockEnqueue.mock.calls[0][0]
    expect(env.error).toBeDefined()
    expect(env.error?.kind).toBe("TestError")
    expect(env.error?.secret).toBe("[redacted]")
    expect(env.http).toEqual({ method: "POST", route_template: "/api/test", status: 500 })
    expect(env.operation_id).toBe("op-123")
    expect(env.phase).toBe("render")
  })
})

describe("Logger — envelope creation", () => {
  it("info creates envelope with correct fields", () => {
    logger.info("test msg", { correlation_id: "corr-1", extra: { a: 1 } })
    expect(mockEnqueue).toHaveBeenCalledTimes(1)
    const env = mockEnqueue.mock.calls[0][0]
    expect(env.level).toBe("info")
    expect(env.msg).toBe("test msg")
    expect(env.correlation_id).toBe("corr-1")
    expect(env.payload).toEqual({ a: 1 })
    expect(env.ts).toBeTruthy()
    expect(env.event).toBe("system.request")
    expect(env.slice).toBeTruthy()
    expect(env.module).toBeTruthy()
    expect(env.block).toBeTruthy()
    expect(env.service).toBe("web")
    expect(env.env).toBeTruthy()
  })

  it("warn creates envelope", () => {
    logger.warn("caution")
    const env = mockEnqueue.mock.calls[0][0]
    expect(env.level).toBe("warn")
  })

  it("error creates envelope", () => {
    logger.error("boom", { extra: { code: 500 } })
    const env = mockEnqueue.mock.calls[0][0]
    expect(env.level).toBe("error")
    expect(env.payload).toEqual({ code: 500 })
  })

  it("logStart, logSuccess, and logFailure convenience wrappers emit valid events", () => {
    logStart("ui.fetch_started", { route: "/api/test" })
    expect(mockEnqueue).toHaveBeenCalledTimes(1)
    expect(mockEnqueue.mock.calls[0][0].event).toBe("ui.fetch_started")

    mockEnqueue.mockClear()
    logSuccess("ui.fetch_started", { status: 200 })
    expect(mockEnqueue).toHaveBeenCalledTimes(1)
    expect(mockEnqueue.mock.calls[0][0].event).toBe("ui.fetch_succeeded")

    mockEnqueue.mockClear()
    logFailure("ui.fetch_failed", new Error("Fetch failed"))
    expect(mockEnqueue).toHaveBeenCalledTimes(1)
    expect(mockEnqueue.mock.calls[0][0].event).toBe("ui.fetch_failed")
    expect(mockEnqueue.mock.calls[0][0].level).toBe("error")
  })
})

describe("Logger — correlation_id & context", () => {
  it("global correlation_id auto-included when set", () => {
    setCorrelationId("global-abc")
    logger.info("with global")
    const env = mockEnqueue.mock.calls[0][0]
    expect(env.correlation_id).toBe("global-abc")
  })

  it("options correlation_id overrides global", () => {
    setCorrelationId("global-abc")
    logger.info("override", { correlation_id: "opt-xyz" })
    const env = mockEnqueue.mock.calls[0][0]
    expect(env.correlation_id).toBe("opt-xyz")
  })

  it("getCorrelationId returns set value", () => {
    setCorrelationId("check-id")
    expect(getCorrelationId()).toBe("check-id")
  })

  it("setLogContext sets default slice, module, block", () => {
    setLogContext("W-TEST-SLICE", "M-TEST-MODULE", "TEST_BLOCK")
    logEvent("ui.fetch_started")
    const env = mockEnqueue.mock.calls[0][0]
    expect(env.slice).toBe("W-TEST-SLICE")
    expect(env.module).toBe("M-TEST-MODULE")
    expect(env.block).toBe("TEST_BLOCK")
  })
})

describe("Logger — console output", () => {
  it("console.log called with [CORR][LEVEL] format", () => {
    setCorrelationId("abcdef01-9999")
    logger.warn("watch out", { extra: { hint: "careful" } })
    expect(consoleLogSpy).toHaveBeenCalledWith(
      "[abcdef01][WARN ]",
      "watch out",
      "(redacted)"
    )
  })
})

describe("Logger — log level filtering", () => {
  it("debug is filtered when NEXT_PUBLIC_LOG_LEVEL=info", async () => {
    vi.resetModules()
    vi.stubEnv("NEXT_PUBLIC_LOG_LEVEL", "info")
    vi.doMock("@/lib/log/shipper", () => ({
      getLogShipper: () => ({ enqueue: mockEnqueue }),
    }))
    mockEnqueue.mockClear()

    const mod = await import("@/lib/log")
    mod.setCorrelationId("filter-test")
    mod.logger.debug("should be skipped")
    expect(mockEnqueue).not.toHaveBeenCalled()

    mod.logger.info("should pass")
    expect(mockEnqueue).toHaveBeenCalledTimes(1)
  })

  it("debug passes when NEXT_PUBLIC_LOG_LEVEL=debug", async () => {
    vi.resetModules()
    vi.stubEnv("NEXT_PUBLIC_LOG_LEVEL", "debug")
    vi.doMock("@/lib/log/shipper", () => ({
      getLogShipper: () => ({ enqueue: mockEnqueue }),
    }))
    mockEnqueue.mockClear()

    const mod = await import("@/lib/log")
    mod.logger.debug("should pass")
    expect(mockEnqueue).toHaveBeenCalledTimes(1)
  })
})

describe("Logger — fresh state", () => {
  it("getCorrelationId returns null on clean import", async () => {
    vi.resetModules()
    vi.doMock("@/lib/log/shipper", () => ({
      getLogShipper: () => ({ enqueue: vi.fn() }),
    }))
    const mod = await import("@/lib/log")
    expect(mod.getCorrelationId()).toBeNull()
  })

  it("setCorrelationId + getCorrelationId round-trip", async () => {
    vi.resetModules()
    vi.doMock("@/lib/log/shipper", () => ({
      getLogShipper: () => ({ enqueue: vi.fn() }),
    }))
    const mod = await import("@/lib/log")
    mod.setCorrelationId("round-trip")
    expect(mod.getCorrelationId()).toBe("round-trip")
  })

  it("console.log format without correlation_id", async () => {
    vi.resetModules()
    vi.doMock("@/lib/log/shipper", () => ({
      getLogShipper: () => ({ enqueue: vi.fn() }),
    }))
    const cSpy = vi.spyOn(console, "log").mockImplementation(() => {})
    const mod = await import("@/lib/log")
    mod.logger.info("hello world")
    expect(cSpy).toHaveBeenCalledWith("[INFO ]", "hello world", "")
  })
})

describe("Logger — frontend redaction", () => {
  it("redacts PII keys and patterns before shipping", () => {
    logger.info("User email test@example.com", {
      correlation_id: "corr-xyz",
      extra: {
        email: "secret@example.com",
        birthDate: "1990-01-15",
      },
    })

    expect(mockEnqueue).toHaveBeenCalledTimes(1)
    const env = mockEnqueue.mock.calls[0][0]

    expect(env.msg).toContain("[redacted-email]")
    expect(env.msg).not.toContain("test@example.com")

    expect(env.payload.email).toBe("[redacted]")
    expect(env.payload.birthDate).toBe("[redacted]")
    expect(env.correlation_id).toBe("corr-xyz")
  })
})
