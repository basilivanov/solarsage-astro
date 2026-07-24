// ############################################################################
// AI_HEADER: MODULE_API_FETCH — typed fetch facade over instrumentedFetch.
// ROLE: Compatibility fetch wrapper used across API services.
// DEPENDENCIES: lib/log/instrumented-fetch
// GRACE_ANCHORS: [API_FETCH]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-API-FETCH
// purpose: Provide a typed compatibility fetch wrapper over instrumentedFetch that handles route label method normalization and timeout separation.
// owns:
//   - lib/api-fetch.ts
// inputs:
//   - routeLabel: templated label (e.g. "GET /api/profile" or "/api/profile")
//   - url: actual URL to fetch
//   - options: custom ApiFetchOptions (including optional timeout in ms)
// outputs:
//   - Promise<Response>
// dependencies:
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch)
// side_effects:
//   - network requests via instrumentedFetch
//   - emits log events (ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed)
// invariants:
//   - timeout is never passed inside native RequestInit
//   - input options object is never mutated
//   - method prefix in routeTemplate is uppercase and never duplicated
// failure_policy:
//   - exceptions and Response objects from instrumentedFetch pass through transparently
// END_MODULE_CONTRACT: M-API-FETCH

// START_MODULE_MAP: M-API-FETCH
// public_entrypoints:
//   - apiFetch
// semantic_blocks:
//   - API_FETCH_FACADE: method normalization, option separation and instrumentedFetch delegation
// owned_tests:
//   - __tests__/lib/api-fetch.test.ts
// END_MODULE_MAP: M-API-FETCH

import { instrumentedFetch } from "./log/instrumented-fetch"

export interface ApiFetchOptions extends Omit<RequestInit, "headers"> {
  headers?: Record<string, string>
  /** Timeout in ms (default 30000). */
  timeout?: number
}

const KNOWN_METHODS = /^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(.+)$/i

// START_BLOCK: API_FETCH_FACADE
export async function apiFetch(
  routeLabel: string,
  url: string,
  options: ApiFetchOptions = {}
): Promise<Response> {
  // START_FUNCTION_CONTRACT: F-M-API-FETCH.apiFetch
  // purpose: Delegate fetch requests to instrumentedFetch while normalizing route method prefixes and stripping custom timeout from init.
  // inputs: routeLabel — template route label string, url — actual URL, options — ApiFetchOptions
  // returns: Promise<Response>
  // side_effects: delegates to instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-API-FETCH.apiFetch

  // Separate custom timeout option from native RequestInit fields without mutating options
  const { timeout, ...init } = options

  const trimmedLabel = routeLabel.trim()
  const match = trimmedLabel.match(KNOWN_METHODS)

  let routeTemplate: string
  if (match) {
    const methodPrefix = match[1].toUpperCase()
    const pathPart = match[2]
    routeTemplate = `${methodPrefix} ${pathPart}`
  } else {
    const fallbackMethod = (options.method || "GET").toUpperCase()
    routeTemplate = `${fallbackMethod} ${trimmedLabel}`
  }

  return instrumentedFetch({
    operation: routeLabel,
    routeTemplate,
    url,
    init: init as RequestInit,
    timeoutMs: timeout ?? 30000,
  })
}
// END_BLOCK: API_FETCH_FACADE
