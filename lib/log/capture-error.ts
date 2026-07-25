// ############################################################################
// AI_HEADER: MODULE_LOG_CAPTURE_ERROR
// ROLE: Privacy-safe frontend error normalization, fingerprinting and deduplication.
// DEPENDENCIES: lib/log/index
// GRACE_ANCHORS: [CAPTURE_FRONTEND_ERROR, NORMALIZE_FRONTEND_ERROR]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-LOG-CAPTURE-ERROR
// purpose: Normalize unknown error inputs into structured, low-PII frontend error payloads,
//   compute deterministic fingerprints, deduplicate occurrences per session, and emit log events.
// owns:
//   - lib/log/capture-error.ts
// inputs:
//   - error: unknown
//   - context: error metadata (event, source, route, operation, etc.)
// outputs:
//   - StructuredFrontendError
//   - side effect: logEvent call
// dependencies:
//   - M-LOG-FRONTEND (logEvent, LogEventName, LogLevel)
// side_effects:
//   - emits logEvent
// invariants:
//   - no raw error messages, raw stacks, or PII in logged envelopes or fingerprints
//   - max 8 sanitized stack frames
//   - deduplicates identical fingerprints up to max 3 times per session (bypassable via force/reset)
// failure_policy:
//   - catches all internal exceptions and returns null without throwing or recursively logging
// END_MODULE_CONTRACT: M-LOG-CAPTURE-ERROR

// START_MODULE_MAP: M-LOG-CAPTURE-ERROR
// public_entrypoints:
//   - captureFrontendError
//   - normalizeFrontendError
//   - sanitizeRoute
//   - sanitizeRouteTemplate
//   - resetFingerprintDeduplicationForTests
// semantic_blocks:
//   - STACK_PARSER: sanitize stack frames and extract low-PII locations.
//   - FINGERPRINT_BUILDER: compute deterministic hashes from safe components.
//   - DEDUP_TRACKER: enforce 3-per-session limit.
//   - CAPTURE_API: normalize and capture frontend error events.
// owned_tests:
//   - __tests__/lib/capture-error.test.ts
// END_MODULE_MAP: M-LOG-CAPTURE-ERROR

import { logEvent, type LogEventName, type LogLevel } from "./index"

export type FrontendErrorSource =
  | "caught"
  | "window.error"
  | "unhandledrejection"
  | "react-boundary"
  | "network"
  | "contract"

export type StackFrame = {
  file: string
  function?: string
  line?: number
  column?: number
}

export type StructuredFrontendError = {
  kind: string
  code?: string
  source: FrontendErrorSource
  fingerprint: string
  stack_frames?: StackFrame[]
  retryable?: boolean
}

export type CaptureErrorContext = {
  event?: LogEventName
  source?: FrontendErrorSource
  level?: LogLevel
  route?: string
  operation?: string
  boundary?: string
  componentArea?: string
  retryable?: boolean
  reasonCode?: string
  attempt?: number
  resetAttempted?: boolean
  contractName?: string
  contractVersion?: string
  missingFields?: string[]
  invalidFieldTypes?: string[]
  payloadShapeHash?: string
  slice?: string
  module?: string
  block?: string
  force?: boolean
  http?: Record<string, unknown>
  duration_ms?: number
  operation_id?: string
  phase?: string
}

const fingerprintCounts = new Map<string, number>()

// START_BLOCK: DEDUP_TRACKER
// START_FUNCTION_CONTRACT: F-M-LOG-CAPTURE-ERROR.resetFingerprintDeduplicationForTests
// purpose: Reset in-memory session fingerprint deduplication counters for unit tests.
// inputs: none
// returns: void
// side_effects: clears fingerprintCounts map
// emitted_logs: none
// error_behavior: none
// END_FUNCTION_CONTRACT: F-M-LOG-CAPTURE-ERROR.resetFingerprintDeduplicationForTests
export function resetFingerprintDeduplicationForTests(): void {
  fingerprintCounts.clear()
}
// END_BLOCK: DEDUP_TRACKER

function isSafeIdentifier(val: string, maxLen = 40): boolean {
  if (!val || typeof val !== "string" || val.length > maxLen) return false
  if (/[@=%\s]/i.test(val) || /bearer|token|secret|key/i.test(val)) return false
  return true
}

function sanitizeSafeString(val: unknown, maxLen = 40, pattern = /^[a-zA-Z0-9_.-]{1,40}$/): string | undefined {
  if (typeof val !== "string") return undefined
  const trimmed = val.trim()
  if (!isSafeIdentifier(trimmed, maxLen)) return undefined
  if (!pattern.test(trimmed)) return undefined
  return trimmed
}

// START_BLOCK: ROUTE_SANITIZER
// START_FUNCTION_CONTRACT: F-M-LOG-CAPTURE-ERROR.sanitizeRoute
// purpose: Sanitize route path string replacing UUID, date, numeric or PII segments while preserving safe placeholders.
// inputs: rawRoute — optional route path string
// returns: string | undefined — sanitized route path
// side_effects: none
// emitted_logs: none
// error_behavior: returns undefined for invalid/empty input
// END_FUNCTION_CONTRACT: F-M-LOG-CAPTURE-ERROR.sanitizeRoute
export function sanitizeRoute(rawRoute?: string): string | undefined {
  if (!rawRoute || typeof rawRoute !== "string") return undefined
  const pathOnly = rawRoute.split("?")[0].split("#")[0]
  const segments = pathOnly.split("/")
  const sanitizedSegments = segments.map((seg) => {
    if (!seg) return seg
    // Preserve safe placeholders like {date}, {id}, {user_id}
    if (/^\{[a-zA-Z0-9_-]{1,30}\}$/.test(seg)) {
      return seg
    }
    // Percent-encoded, @, secret, non-ascii, spaces or unallowed characters -> :id
    if (seg.includes("%") || seg.includes("@") || /[@=:\s]/i.test(seg) || /bearer|token|secret|key/i.test(seg)) {
      return ":id"
    }
    // UUID check
    if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(seg)) {
      return ":id"
    }
    // Date YYYY-MM-DD check
    if (/^\d{4}-\d{2}-\d{2}$/.test(seg)) {
      return ":date"
    }
    // Pure numeric ID check
    if (/^\d+$/.test(seg)) {
      return ":id"
    }
    // Long segment (> 24 chars) or not clean static segment
    if (seg.length > 24 || !/^[a-z0-9_-]+$/i.test(seg)) {
      return ":id"
    }
    return seg
  })
  return sanitizedSegments.join("/")
}

// START_FUNCTION_CONTRACT: F-M-LOG-CAPTURE-ERROR.sanitizeRouteTemplate
// purpose: Sanitize full route template string containing optional HTTP method prefix and path placeholders.
// inputs: rawTemplate — optional route template string
// returns: string | undefined — sanitized route template
// side_effects: none
// emitted_logs: none
// error_behavior: returns undefined for invalid/empty input
// END_FUNCTION_CONTRACT: F-M-LOG-CAPTURE-ERROR.sanitizeRouteTemplate
export function sanitizeRouteTemplate(rawTemplate?: string): string | undefined {
  if (!rawTemplate || typeof rawTemplate !== "string") return undefined
  const trimmed = rawTemplate.trim()
  if (!trimmed) return undefined

  let methodPrefix = ""
  let pathPart = trimmed

  const methodMatch = trimmed.match(/^([A-Za-z]{1,10})\s+(.+)$/)
  if (methodMatch) {
    methodPrefix = methodMatch[1].toUpperCase() + " "
    pathPart = methodMatch[2]
  }

  const pathOnly = pathPart.split("?")[0].split("#")[0]
  const segments = pathOnly.split("/")
  const sanitizedSegments = segments.map((seg) => {
    if (!seg) return seg
    // Preserve safe placeholders like {date}, {id}, {user_id}
    if (/^\{[a-zA-Z0-9_-]{1,30}\}$/.test(seg)) {
      return seg
    }
    // Percent-encoded, @, secret, non-ascii, spaces or unallowed characters -> :id
    if (seg.includes("%") || seg.includes("@") || /[@=:\s]/i.test(seg) || /bearer|token|secret|key/i.test(seg)) {
      return ":id"
    }
    // UUID check
    if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(seg)) {
      return ":id"
    }
    // Date YYYY-MM-DD check
    if (/^\d{4}-\d{2}-\d{2}$/.test(seg)) {
      return ":date"
    }
    // Pure numeric ID check
    if (/^\d+$/.test(seg)) {
      return ":id"
    }
    // Long segment (> 24 chars) or not clean static segment
    if (seg.length > 24 || !/^[a-z0-9_-]+$/i.test(seg)) {
      return ":id"
    }
    return seg
  })

  return methodPrefix + sanitizedSegments.join("/")
}
// END_BLOCK: ROUTE_SANITIZER

// START_BLOCK: STACK_PARSER
const KNOWN_ROOTS = ["app/", "components/", "lib/", ".next/", "node_modules/"]

function isSafeSegment(seg: string): boolean {
  if (!seg || seg.length > 60) return false
  if (seg.includes("%") || seg.includes("@") || /[@=:\s]/i.test(seg) || /bearer|token|secret|key/i.test(seg)) return false
  return /^[A-Za-z0-9_.-]+$/.test(seg)
}

function cleanFilePath(rawPath: string): string {
  if (!rawPath || typeof rawPath !== "string") return "unknown"
  let cleaned = rawPath.split("?")[0].split("#")[0]
  cleaned = cleaned.replace(/^https?:\/\/[^/]+/, "")

  let relPath = ""
  for (const root of KNOWN_ROOTS) {
    const idx = cleaned.indexOf(root)
    if (idx !== -1) {
      relPath = cleaned.slice(idx)
      break
    }
  }
  if (!relPath) {
    const parts = cleaned.split("/")
    relPath = parts[parts.length - 1] || "unknown"
  }

  const parts = relPath.split("/")
  const safeParts = parts.map((p, idx) => {
    if (idx === parts.length - 1) {
      const fileBase = p.split(":")[0]
      if (isSafeSegment(fileBase)) return p
      return ":file"
    }
    if (isSafeSegment(p)) return p
    return ":param"
  })

  return safeParts.join("/")
}

function parseStackFrames(stackStr?: string): StackFrame[] | undefined {
  if (!stackStr || typeof stackStr !== "string") return undefined
  const lines = stackStr.split("\n")
  const frames: StackFrame[] = []

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed.startsWith("at ")) continue

    const matchWithFn = trimmed.match(/^at\s+([^\s]+)\s+\((.+)\)$/)
    const matchWithoutFn = trimmed.match(/^at\s+(.+)$/)

    let rawFn: string | undefined = undefined
    let rawLocation = ""

    if (matchWithFn) {
      rawFn = matchWithFn[1]
      rawLocation = matchWithFn[2]
    } else if (matchWithoutFn) {
      rawLocation = matchWithoutFn[1]
    }

    if (!rawLocation) continue

    const cleanFile = cleanFilePath(rawLocation)
    const lineColMatch = rawLocation.match(/:(\d+):(\d+)$/)
    let lineNum: number | undefined = undefined
    let colNum: number | undefined = undefined

    if (lineColMatch) {
      lineNum = parseInt(lineColMatch[1], 10)
      colNum = parseInt(lineColMatch[2], 10)
    }

    let cleanFn: string | undefined = undefined
    if (rawFn && isSafeIdentifier(rawFn, 40)) {
      cleanFn = rawFn
    }

    frames.push({
      file: cleanFile,
      function: cleanFn,
      line: lineNum,
      column: colNum,
    })

    if (frames.length >= 8) break
  }

  return frames.length > 0 ? frames : undefined
}
// END_BLOCK: STACK_PARSER

// START_BLOCK: FINGERPRINT_BUILDER
function simpleHash(str: string): string {
  let hash = 5381
  for (let i = 0; i < str.length; i++) {
    hash = (hash * 33) ^ str.charCodeAt(i)
  }
  return (hash >>> 0).toString(16).padStart(8, "0")
}

function computeFingerprint(kind: string, code: string | undefined, source: FrontendErrorSource, frames?: StackFrame[]): string {
  const frameSig = frames
    ? frames.map((f) => `${f.file}:${f.function || ""}`).join("|")
    : ""
  const rawSig = `${kind}:${code || ""}:${source}:${frameSig}`
  return simpleHash(rawSig)
}
// END_BLOCK: FINGERPRINT_BUILDER

// START_BLOCK: CAPTURE_API
// START_FUNCTION_CONTRACT: F-M-LOG-CAPTURE-ERROR.normalizeFrontendError
// purpose: Convert unknown error inputs into a safe, normalized StructuredFrontendError object.
// inputs: error — unknown error, source — FrontendErrorSource, retryable — optional boolean
// returns: StructuredFrontendError
// side_effects: none
// emitted_logs: none
// error_behavior: handles primitive, null, or malformed error objects safely
// END_FUNCTION_CONTRACT: F-M-LOG-CAPTURE-ERROR.normalizeFrontendError
export function normalizeFrontendError(
  error: unknown,
  source: FrontendErrorSource = "caught",
  retryable?: boolean
): StructuredFrontendError {
  let kind = "Error"
  let code: string | undefined = undefined
  let stackStr: string | undefined = undefined

  if (error instanceof Error) {
    kind = error.name || "Error"
    if (!isSafeIdentifier(kind, 40) || !/^[A-Za-z0-9_<>-]{1,40}$/.test(kind)) {
      kind = "Error"
    }
    const rawCode = (error as any).code
    if (typeof rawCode === "string" && isSafeIdentifier(rawCode, 40) && /^[A-Z0-9_]{1,40}$/.test(rawCode)) {
      code = rawCode
    }
    stackStr = error.stack
  } else if (typeof error === "string") {
    kind = "StringRejection"
  } else if (error && typeof error === "object") {
    kind = (error as any).name || (error as any).constructor?.name || "ObjectRejection"
    if (!isSafeIdentifier(kind, 40) || !/^[A-Za-z0-9_<>-]{1,40}$/.test(kind)) {
      kind = "ObjectRejection"
    }
  }

  const frames = parseStackFrames(stackStr)
  const fingerprint = computeFingerprint(kind, code, source, frames)

  return {
    kind,
    code,
    source,
    fingerprint,
    stack_frames: frames,
    retryable,
  }
}

// START_FUNCTION_CONTRACT: F-M-LOG-CAPTURE-ERROR.captureFrontendError
// purpose: Normalize unknown error input, apply session deduplication, and emit structured frontend error log event.
// inputs: error — unknown error, context — CaptureErrorContext options
// returns: StructuredFrontendError | null
// side_effects: emits logEvent
// emitted_logs: frontend.runtime_failed, frontend.render_failed, frontend.promise_rejected, frontend.api_request_failed, frontend.api_response_invalid
// error_behavior: catches internal failures safely without throwing
// END_FUNCTION_CONTRACT: F-M-LOG-CAPTURE-ERROR.captureFrontendError
export function captureFrontendError(
  error: unknown,
  context: CaptureErrorContext = {}
): StructuredFrontendError | null {
  try {
    const source = context.source || "caught"
    const normalized = normalizeFrontendError(error, source, context.retryable)

    const sanitizedRoute = sanitizeRoute(context.route)
    const sanitizedOperation = sanitizeSafeString(context.operation, 60, /^[a-zA-Z0-9_.-]{1,60}$/)
    const sanitizedBoundary = sanitizeSafeString(context.boundary, 40, /^[a-zA-Z0-9_.-]{1,40}$/)
    const sanitizedComponentArea = sanitizeSafeString(context.componentArea, 40, /^[a-zA-Z0-9_.-]{1,40}$/)
    const sanitizedReasonCode = sanitizeSafeString(context.reasonCode, 40, /^[a-zA-Z0-9_.-]{1,40}$/)
    const sanitizedContractName = sanitizeSafeString(context.contractName, 60, /^[a-zA-Z0-9_.-]{1,60}$/)
    const sanitizedContractVersion = sanitizeSafeString(context.contractVersion, 20, /^[a-zA-Z0-9_.-]{1,20}$/)
    const sanitizedShapeHash = sanitizeSafeString(context.payloadShapeHash, 40, /^[a-zA-Z0-9_.-]{1,40}$/)
    const sanitizedSlice = sanitizeSafeString(context.slice, 40, /^[a-zA-Z0-9_-]{1,40}$/) || "W-FRONTEND"
    const sanitizedModule = sanitizeSafeString(context.module, 40, /^[a-zA-Z0-9_-]{1,40}$/) || "M-LOG-CAPTURE-ERROR"
    const sanitizedBlock = sanitizeSafeString(context.block, 40, /^[a-zA-Z0-9_-]{1,40}$/) || "CAPTURE_API"

    const sanitizedMissingFields = Array.isArray(context.missingFields)
      ? context.missingFields.slice(0, 10).map((f) => sanitizeSafeString(f, 40)).filter((f): f is string => Boolean(f))
      : undefined

    const sanitizedInvalidFieldTypes = Array.isArray(context.invalidFieldTypes)
      ? context.invalidFieldTypes.slice(0, 10).map((f) => sanitizeSafeString(f, 40)).filter((f): f is string => Boolean(f))
      : undefined

    const dedupKey = `${normalized.fingerprint}:${sanitizedOperation || ""}:${sanitizedBoundary || ""}:${sanitizedRoute || ""}`
    const currentCount = fingerprintCounts.get(dedupKey) || 0

    // Deduplication check (max 3 times per dedupKey per session, unless force or resetAttempted)
    if (!context.force && !context.resetAttempted && currentCount >= 3) {
      return normalized
    }

    fingerprintCounts.set(dedupKey, currentCount + 1)

    const eventName: LogEventName =
      context.event ||
      (source === "react-boundary"
        ? "frontend.render_failed"
        : source === "unhandledrejection"
        ? "frontend.promise_rejected"
        : source === "network"
        ? "frontend.api_request_failed"
        : source === "contract"
        ? "frontend.api_response_invalid"
        : "frontend.runtime_failed")

    const level: LogLevel = context.level || (eventName.endsWith("_failed") || eventName.endsWith("_rejected") ? "error" : "info")

    const payload: Record<string, unknown> = {}
    if (sanitizedRoute) payload.route = sanitizedRoute
    if (sanitizedOperation) payload.operation = sanitizedOperation
    if (sanitizedBoundary) payload.boundary = sanitizedBoundary
    if (sanitizedComponentArea) payload.component_area = sanitizedComponentArea
    if (context.retryable !== undefined) payload.retryable = context.retryable
    if (sanitizedReasonCode) payload.reason_code = sanitizedReasonCode
    if (context.attempt !== undefined) payload.attempt = context.attempt
    if (context.resetAttempted !== undefined) payload.reset_attempted = context.resetAttempted
    if (sanitizedContractName) payload.contract_name = sanitizedContractName
    if (sanitizedContractVersion) payload.contract_version = sanitizedContractVersion
    if (sanitizedMissingFields && sanitizedMissingFields.length > 0) payload.missing_fields = sanitizedMissingFields
    if (sanitizedInvalidFieldTypes && sanitizedInvalidFieldTypes.length > 0) payload.invalid_field_types = sanitizedInvalidFieldTypes
    if (sanitizedShapeHash) payload.payload_shape_hash = sanitizedShapeHash

    // Sanitize top-level meta fields before logEvent
    let sanitizedHttp: Record<string, unknown> | undefined = undefined
    if (context.http && typeof context.http === "object") {
      const rawMethod = (context.http as Record<string, unknown>).method
      const rawRoute = (context.http as Record<string, unknown>).route_template
      const rawStatus = (context.http as Record<string, unknown>).status

      const cleanMethod = typeof rawMethod === "string" && /^[A-Za-z]{1,10}$/.test(rawMethod.trim())
        ? rawMethod.trim().toUpperCase()
        : undefined
      const cleanRoute = typeof rawRoute === "string"
        ? sanitizeRouteTemplate(rawRoute)
        : undefined
      const cleanStatus = typeof rawStatus === "number" && Number.isInteger(rawStatus) && rawStatus >= 100 && rawStatus <= 599
        ? rawStatus
        : undefined

      if (cleanMethod || cleanRoute || cleanStatus !== undefined) {
        sanitizedHttp = {}
        if (cleanMethod) sanitizedHttp.method = cleanMethod
        if (cleanRoute) sanitizedHttp.route_template = cleanRoute
        if (cleanStatus !== undefined) sanitizedHttp.status = cleanStatus
      }
    }

    const sanitizedDurationMs = typeof context.duration_ms === "number" && Number.isFinite(context.duration_ms) && context.duration_ms >= 0
      ? context.duration_ms
      : undefined

    const sanitizedOperationId = sanitizeSafeString(context.operation_id, 60, /^[a-zA-Z0-9_.-]{1,60}$/)

    const ALLOWED_PHASES = new Set(["request", "response", "failure", "contract-validation"])
    const sanitizedPhase = typeof context.phase === "string"
      ? (ALLOWED_PHASES.has(context.phase) ? context.phase : sanitizeSafeString(context.phase, 40))
      : undefined

    logEvent(
      eventName,
      Object.keys(payload).length > 0 ? payload : undefined,
      {
        level,
        slice: sanitizedSlice,
        module: sanitizedModule,
        block: sanitizedBlock,
        error: normalized as unknown as Record<string, unknown>,
        http: sanitizedHttp,
        duration_ms: sanitizedDurationMs,
        operation_id: sanitizedOperationId,
        phase: sanitizedPhase,
      }
    )

    return normalized
  } catch {
    return null
  }
}
// END_BLOCK: CAPTURE_API
