// ############################################################################
// AI_HEADER: MODULE_LOG_INSTRUMENTED_FETCH
// ROLE: Instrumented fetch wrapper for product API clients.
// DEPENDENCIES: lib/log/index, lib/log/capture-error
// GRACE_ANCHORS: [INSTRUMENTED_FETCH]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-LOG-INSTRUMENTED-FETCH
// purpose: Wrap window.fetch for product API clients with X-Correlation-Id headers, lifecycle logs,
//   privacy-safe error classification, timeout/abort handling, and optional response contract validation.
// owns:
//   - lib/log/instrumented-fetch.ts
// inputs:
//   - InstrumentedFetchOptions
// outputs:
//   - Promise<Response>
// dependencies:
//   - M-LOG-FRONTEND (logEvent, getCorrelationId, setCorrelationId)
//   - M-LOG-CAPTURE-ERROR (captureFrontendError, sanitizeRouteTemplate)
// side_effects:
//   - network fetch call
//   - emits logEvents (ui.fetch_started, ui.fetch_succeeded, frontend.api_request_failed, frontend.api_response_invalid)
// invariants:
//   - no raw URLs, query strings, headers, or request/response bodies in logs or error envelopes
//   - safe correlation ID validation: 1..128 safe chars, no secret/token/bearer
//   - preserves existing fetch RequestInit, headers, credentials, and caller AbortSignal
//   - timeout cleanup occurs on both success and failure
//   - never intercepts /api/_log calls to prevent recursion
// failure_policy:
//   - logs failures then rethrows network/abort exceptions or returns HTTP error response as-is
// END_MODULE_CONTRACT: M-LOG-INSTRUMENTED-FETCH

// START_MODULE_MAP: M-LOG-INSTRUMENTED-FETCH
// public_entrypoints:
//   - instrumentedFetch
//   - isApiLogPath
// semantic_blocks:
//   - INSTRUMENTED_FETCH_CORE: fetch wrapper logic
// owned_tests:
//   - __tests__/lib/instrumented-fetch.test.ts
// END_MODULE_MAP: M-LOG-INSTRUMENTED-FETCH

import { logEvent, getCorrelationId, setCorrelationId } from "./index"
import { captureFrontendError, sanitizeRouteTemplate } from "./capture-error"

export type InstrumentedFetchOptions = {
  operation: string
  routeTemplate: string
  url: string
  init?: RequestInit
  timeoutMs?: number
  attempt?: number
  fetchImpl?: typeof fetch
  responseContract?: {
    contractName: string
    contractVersion: string
    validate: (json: unknown) => { valid: boolean; missingFields?: string[]; invalidFieldTypes?: string[]; shapeHash?: string }
  }
}

function parseMethod(init?: RequestInit): string {
  return (init?.method || "GET").toUpperCase()
}

function generateSafeId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16)
  })
}

function isSafeCorrelationId(val: unknown): val is string {
  if (typeof val !== "string") return false
  const trimmed = val.trim()
  if (trimmed.length < 1 || trimmed.length > 128) return false
  if (!/^[A-Za-z0-9._:-]{1,128}$/.test(trimmed)) return false
  if (/bearer|token|secret/i.test(trimmed)) return false
  return true
}

// START_FUNCTION_CONTRACT: F-M-LOG-INSTRUMENTED-FETCH.isApiLogPath
// purpose: Determine whether URL pathname matches /api/_log to bypass instrumentation and avoid recursive logging loops.
// inputs: url — URL string
// returns: boolean
// side_effects: none
// emitted_logs: none
// error_behavior: returns false on invalid inputs
// END_FUNCTION_CONTRACT: F-M-LOG-INSTRUMENTED-FETCH.isApiLogPath
export function isApiLogPath(url: string): boolean {
  if (!url || typeof url !== "string") return false
  try {
    const parsed = new URL(url, "http://localhost")
    return parsed.pathname === "/api/_log" || parsed.pathname === "/api/_log/"
  } catch {
    const pathOnly = url.split("?")[0].split("#")[0]
    return pathOnly === "/api/_log" || pathOnly === "/api/_log/" || pathOnly.endsWith("/api/_log")
  }
}

function simpleShapeHash(obj: unknown): string {
  if (obj === null || obj === undefined) return "null"
  if (Array.isArray(obj)) {
    return `array[${obj.length > 0 ? simpleShapeHash(obj[0]) : ""}]`
  }
  if (typeof obj === "object") {
    const keys = Object.keys(obj as object).sort()
    const shapeStr = keys.map((k) => `${k}:${typeof (obj as Record<string, unknown>)[k]}`).join(";")
    let hash = 5381
    for (let i = 0; i < shapeStr.length; i++) {
      hash = (hash * 33) ^ shapeStr.charCodeAt(i)
    }
    return (hash >>> 0).toString(16).padStart(8, "0")
  }
  return typeof obj
}

// START_BLOCK: INSTRUMENTED_FETCH_CORE
// START_FUNCTION_CONTRACT: F-M-LOG-INSTRUMENTED-FETCH.instrumentedFetch
// purpose: Main fetch wrapper adding correlation IDs, timeout handling, lifecycle log events, and response contract validation.
// inputs: options — InstrumentedFetchOptions
// returns: Promise<Response>
// side_effects: network fetch call, emits log events
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_request_failed, frontend.api_response_invalid
// error_behavior: logs errors via captureFrontendError; rethrows network/timeout/abort errors or returns HTTP response
// END_FUNCTION_CONTRACT: F-M-LOG-INSTRUMENTED-FETCH.instrumentedFetch
export async function instrumentedFetch(options: InstrumentedFetchOptions): Promise<Response> {
  const {
    operation,
    routeTemplate,
    url,
    init,
    timeoutMs,
    attempt = 1,
    responseContract,
  } = options

  const fetchImpl = options.fetchImpl || (typeof window !== "undefined" && window.fetch ? window.fetch.bind(window) : fetch)

  // Bypass /api/_log entirely to avoid recursive logging loop (pathname check)
  if (isApiLogPath(url)) {
    return fetchImpl(url, init)
  }

  const method = parseMethod(init)
  const cleanRouteTemplate = sanitizeRouteTemplate(routeTemplate) || routeTemplate
  const cleanPathRoute = cleanRouteTemplate.replace(/^[A-Za-z]{1,10}\s+/, "")
  const operationId = generateSafeId()
  const isDev = process.env.NODE_ENV !== "production"
  const sampleRate = isDev ? 1.0 : 0.2

  // Extract caller headers and check for safe X-Correlation-Id
  const reqHeaders: Record<string, string> = {}
  let rawCallerCorr: string | undefined = undefined

  if (init?.headers) {
    if (typeof Headers !== "undefined" && init.headers instanceof Headers) {
      init.headers.forEach((v, k) => {
        if (k.toLowerCase() === "x-correlation-id") rawCallerCorr = v
        else reqHeaders[k] = v
      })
    } else if (Array.isArray(init.headers)) {
      for (const [k, v] of init.headers) {
        if (k.toLowerCase() === "x-correlation-id") rawCallerCorr = v
        else reqHeaders[k] = v
      }
    } else {
      for (const k of Object.keys(init.headers)) {
        if (k.toLowerCase() === "x-correlation-id") rawCallerCorr = (init.headers as Record<string, string>)[k]
        else reqHeaders[k] = (init.headers as Record<string, string>)[k]
      }
    }
  }

  let selectedCorrelationId: string

  if (isSafeCorrelationId(rawCallerCorr)) {
    selectedCorrelationId = rawCallerCorr.trim()
    setCorrelationId(selectedCorrelationId)
  } else {
    const currentLoggerCorr = getCorrelationId()
    if (isSafeCorrelationId(currentLoggerCorr)) {
      selectedCorrelationId = currentLoggerCorr.trim()
    } else {
      selectedCorrelationId = generateSafeId()
      setCorrelationId(selectedCorrelationId)
    }
  }

  // Remove any remaining case-insensitive correlation headers and attach single canonical X-Correlation-Id
  for (const k of Object.keys(reqHeaders)) {
    if (k.toLowerCase() === "x-correlation-id") {
      delete reqHeaders[k]
    }
  }
  reqHeaders["X-Correlation-Id"] = selectedCorrelationId

  // Setup timeout and external signal combination
  let timeoutId: ReturnType<typeof setTimeout> | null = null
  const controller = new AbortController()
  let isTimeout = false

  if (timeoutMs && timeoutMs > 0) {
    timeoutId = setTimeout(() => {
      isTimeout = true
      controller.abort(new Error("Timeout"))
    }, timeoutMs)
  }

  const externalSignal = init?.signal
  const onExternalAbort = () => {
    controller.abort(externalSignal?.reason)
  }

  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort(externalSignal.reason)
    } else {
      externalSignal.addEventListener("abort", onExternalAbort)
    }
  }

  const startTime = typeof performance !== "undefined" ? performance.now() : Date.now()

  // Log start with exact XML payload { route, method }
  logEvent("ui.fetch_started", { route: cleanRouteTemplate, method }, {
    level: "info",
    slice: "W-FRONTEND",
    module: "M-LOG-INSTRUMENTED-FETCH",
    block: "INSTRUMENTED_FETCH_CORE",
    http: { method, route_template: cleanRouteTemplate },
    operation_id: operationId,
    phase: "request",
    sample_rate: sampleRate,
  })

  try {
    const res = await fetchImpl(url, {
      ...init,
      headers: reqHeaders,
      signal: controller.signal,
    })

    const durationMs = (typeof performance !== "undefined" ? performance.now() : Date.now()) - startTime

    // Read back X-Correlation-Id header if returned BEFORE response logs (adopt only if safe)
    const rawResCorrelation = res.headers && typeof res.headers.get === "function"
      ? (res.headers.get("X-Correlation-Id") || res.headers.get("x-correlation-id"))
      : null

    if (isSafeCorrelationId(rawResCorrelation)) {
      setCorrelationId(rawResCorrelation.trim())
    }

    if (!res.ok) {
      // Log HTTP failure
      captureFrontendError(new Error(`HTTP ${res.status} for ${operation}`), {
        event: "frontend.api_request_failed",
        source: "network",
        level: "error",
        operation,
        route: cleanPathRoute,
        reasonCode: "http",
        attempt,
        retryable: res.status === 429 || res.status >= 500,
        slice: "W-FRONTEND",
        module: "M-LOG-INSTRUMENTED-FETCH",
        block: "INSTRUMENTED_FETCH_CORE",
        http: { method, route_template: cleanRouteTemplate, status: res.status },
        duration_ms: durationMs,
        operation_id: operationId,
        phase: "failure",
      })

      logEvent("ui.fetch_failed", { route: cleanRouteTemplate, method, status: res.status }, {
        level: "error",
        slice: "W-FRONTEND",
        module: "M-LOG-INSTRUMENTED-FETCH",
        block: "INSTRUMENTED_FETCH_CORE",
        http: { method, route_template: cleanRouteTemplate, status: res.status },
        operation_id: operationId,
        phase: "failure",
        duration_ms: durationMs,
      })

      return res
    }

    // Response contract validation if provided (clones response, never consumes original)
    if (responseContract) {
      try {
        const clone = res.clone()
        let json: unknown = null
        let parseFailed = false
        try {
          json = await clone.json()
        } catch {
          parseFailed = true
        }

        if (parseFailed) {
          captureFrontendError(new Error(`JSON parse failed for contract ${responseContract.contractName}`), {
            event: "frontend.api_response_invalid",
            source: "contract",
            level: "error",
            operation,
            route: cleanPathRoute,
            contractName: responseContract.contractName,
            contractVersion: responseContract.contractVersion,
            reasonCode: "invalid_json",
            slice: "W-FRONTEND",
            module: "M-LOG-INSTRUMENTED-FETCH",
            block: "RESPONSE_CONTRACT_VALIDATOR",
            http: { method, route_template: cleanRouteTemplate, status: res.status },
            duration_ms: durationMs,
            operation_id: operationId,
            phase: "contract-validation",
          })
        } else {
          let validation: { valid: boolean; missingFields?: string[]; invalidFieldTypes?: string[]; shapeHash?: string } = { valid: false }
          let validationThrew = false
          try {
            validation = responseContract.validate(json)
          } catch {
            validationThrew = true
          }

          if (validationThrew || !validation.valid) {
            captureFrontendError(new Error(`Contract validation failed for ${responseContract.contractName}`), {
              event: "frontend.api_response_invalid",
              source: "contract",
              level: "error",
              operation,
              route: cleanPathRoute,
              contractName: responseContract.contractName,
              contractVersion: responseContract.contractVersion,
              missingFields: validation.missingFields,
              invalidFieldTypes: validation.invalidFieldTypes,
              payloadShapeHash: validation.shapeHash || simpleShapeHash(json),
              slice: "W-FRONTEND",
              module: "M-LOG-INSTRUMENTED-FETCH",
              block: "RESPONSE_CONTRACT_VALIDATOR",
              http: { method, route_template: cleanRouteTemplate, status: res.status },
              duration_ms: durationMs,
              operation_id: operationId,
              phase: "contract-validation",
            })
          }
        }
      } catch {
        // Safe fail-catch for clone validation
      }
    }

    // Log success
    logEvent("ui.fetch_succeeded", { route: cleanRouteTemplate, method, status: res.status }, {
      level: "info",
      slice: "W-FRONTEND",
      module: "M-LOG-INSTRUMENTED-FETCH",
      block: "INSTRUMENTED_FETCH_CORE",
      http: { method, route_template: cleanRouteTemplate, status: res.status },
      operation_id: operationId,
      phase: "response",
      duration_ms: durationMs,
      sample_rate: sampleRate,
    })

    return res
  } catch (err) {
    const durationMs = (typeof performance !== "undefined" ? performance.now() : Date.now()) - startTime

    let reasonCode = "network"
    if (isTimeout) {
      reasonCode = "timeout"
    } else if (externalSignal?.aborted || (err instanceof Error && err.name === "AbortError")) {
      reasonCode = "aborted"
    }

    const isAbort = reasonCode === "aborted"
    const level = isAbort ? "warn" : "error"

    captureFrontendError(err, {
      event: "frontend.api_request_failed",
      source: "network",
      level,
      operation,
      route: cleanPathRoute,
      reasonCode,
      attempt,
      retryable: reasonCode === "network" || reasonCode === "timeout",
      slice: "W-FRONTEND",
      module: "M-LOG-INSTRUMENTED-FETCH",
      block: "INSTRUMENTED_FETCH_CORE",
      http: { method, route_template: cleanRouteTemplate },
      duration_ms: durationMs,
      operation_id: operationId,
      phase: "failure",
    })

    logEvent("ui.fetch_failed", { route: cleanRouteTemplate, method }, {
      level,
      slice: "W-FRONTEND",
      module: "M-LOG-INSTRUMENTED-FETCH",
      block: "INSTRUMENTED_FETCH_CORE",
      http: { method, route_template: cleanRouteTemplate },
      operation_id: operationId,
      phase: "failure",
      duration_ms: durationMs,
    })

    throw err
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    if (externalSignal) {
      externalSignal.removeEventListener("abort", onExternalAbort)
    }
  }
}
// END_BLOCK: INSTRUMENTED_FETCH_CORE
