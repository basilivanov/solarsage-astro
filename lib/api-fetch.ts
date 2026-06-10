// ############################################################################
// AI_HEADER: MODULE_API_FETCH
// ROLE: Typed fetch wrapper with correlation ID propagation and logging.
// GRACE_ANCHORS: [API_FETCH, LOG_EVENT]
// WAVE: W-1.6
// ############################################################################

// START_MODULE_CONTRACT: M-API-FETCH
// purpose: Provide a typed fetch wrapper that:
//   - adds/creates correlation_id (X-Correlation-Id header)
//   - logs ui.fetch_started / ui.fetch_succeeded / ui.fetch_failed
//   - uses templated route labels, not raw URLs
//   - reads response header X-Correlation-Id for back-front join
// owns:
//   - lib/api-fetch.ts
// inputs:
//   - route: templated label (e.g. "GET /api/profile")
//   - url: actual URL to fetch
//   - options: standard fetch options
// outputs:
//   - typed Response
// side_effects:
//   - writes log events (fetch_started, fetch_succeeded, fetch_failed)
//   - sets X-Correlation-Id header on outgoing requests
// invariants:
//   - correlation_id is minted if not set globally
//   - route is a templated label, never a raw URL with query params
//   - fetch_failed logs the HTTP method + route + status
// END_MODULE_CONTRACT: M-API-FETCH

import { logEvent, getCorrelationId, setCorrelationId } from "./log/index";

interface ApiFetchOptions extends Omit<RequestInit, "headers"> {
  headers?: Record<string, string>;
  /** Timeout in ms (default 30000). */
  timeout?: number;
}

export async function apiFetch(
  routeLabel: string,
  url: string,
  options: ApiFetchOptions = {},
): Promise<Response> {
  let correlationId = getCorrelationId();
  if (!correlationId) {
    correlationId = crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setCorrelationId(correlationId);
  }

  const headers: Record<string, string> = {
    ...options.headers,
    "X-Correlation-Id": correlationId,
  };

  const startTime = Date.now();

  logEvent("ui.fetch_started", {
    route: routeLabel,
    method: options.method ?? "GET",
  });

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout ?? 30000);

    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    const durationMs = Date.now() - startTime;

    // Read response correlation ID
    const responseCorrId = response.headers.get("X-Correlation-Id");
    if (responseCorrId && responseCorrId !== correlationId) {
      setCorrelationId(responseCorrId);
    }

    if (!response.ok) {
      logEvent("ui.fetch_failed", {
        route: routeLabel,
        method: options.method ?? "GET",
        status: response.status,
      }, { level: "error", duration_ms: durationMs });
    } else {
      logEvent("ui.fetch_succeeded", {
        route: routeLabel,
        method: options.method ?? "GET",
        status: response.status,
      }, { duration_ms: durationMs });
    }

    return response;
  } catch (error: any) {
    const durationMs = Date.now() - startTime;

    logEvent("ui.fetch_failed", {
      route: routeLabel,
      method: options.method ?? "GET",
    }, {
      level: "error",
      duration_ms: durationMs,
    });

    throw error;
  }
}
