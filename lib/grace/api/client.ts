
// ############################################################################
// AI_HEADER: MODULE_API_CLIENT — API client with runtime contract schema validation.
// ROLE: API client for backend endpoints. Handles day/calendar HTTP requests.
// DEPENDENCIES: local modules, packages/contracts
// ############################################################################

// START_MODULE_CONTRACT: M-WEB-API-CLIENT
// purpose: API client for backend endpoints with type-safe contracts.
// owns:
//   - lib/grace/api/client.ts
// inputs: Endpoint params plus explicit browser runtime facts for Today preview marking.
// outputs: Parsed response / typed data.
// dependencies: packages/contracts, packages/contracts/runtime.
// side_effects: Network calls to API.
// emitted_logs: none.
// invariants:
//   - All day payloads are validated at the fetch boundary.
//   - Invalid day payloads throw ApiContractError.
//   - Only fetchDay may emit the exact Today preview marker.
//   - Marker emission requires a development browser on localhost/loopback port 3003.
//   - Production, SSR, public hosts, other ports, calendar, and other clients fail closed.
// failure_policy: Throws ApiError for HTTP failures and ApiContractError for contract mismatches; network and JSON parsing errors propagate.
// END_MODULE_CONTRACT: M-WEB-API-CLIENT

// START_MODULE_MAP: M-WEB-API-CLIENT
// public_entrypoints:
//   - fetchDay
//   - fetchCalendar
//   - shouldEmitTodayPreviewMarker
//   - TODAY_PREVIEW_HEADER_NAME / TODAY_PREVIEW_HEADER_VALUE / TODAY_PREVIEW_PORT
//   - ApiError
//   - ApiContractError
// semantic_blocks:
//   - TODAY_PREVIEW_MARKER: pure closed browser runtime decision.
//   - API_CLIENT_LOGIC: handles day and calendar network calls.
//   - ERROR_TYPES: custom API and contract error classes.
// END_MODULE_MAP: M-WEB-API-CLIENT

import type { TodayPayload, CalendarPayload } from '@/packages/contracts';
import { TodayPayloadWireSchema } from '@/packages/contracts/runtime';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

// START_BLOCK: TODAY_PREVIEW_MARKER
export const TODAY_PREVIEW_HEADER_NAME = 'X-SolarSage-Preview-Mode';
export const TODAY_PREVIEW_HEADER_VALUE = 'today-v2-real';
export const TODAY_PREVIEW_PORT = 3003;

export type TodayPreviewBrowserRuntime = {
  nodeEnv: string | undefined;
  hostname: string;
  port: string;
};

// START_FUNCTION_CONTRACT: F-M-WEB-API-CLIENT.shouldEmitTodayPreviewMarker
// purpose: Decide whether explicit browser runtime facts authorize the closed Today preview marker.
// inputs: runtime - node environment plus browser hostname and port at fetchDay call time.
// returns: boolean true only for development localhost/loopback on exact port 3003.
// side_effects: none.
// emitted_logs: none.
// error_behavior: malformed or unexpected runtime facts return false.
// END_FUNCTION_CONTRACT: F-M-WEB-API-CLIENT.shouldEmitTodayPreviewMarker
export function shouldEmitTodayPreviewMarker(
  runtime: TodayPreviewBrowserRuntime,
): boolean {
  if (runtime.nodeEnv !== 'development' || runtime.port !== String(TODAY_PREVIEW_PORT)) {
    return false;
  }

  const normalized = runtime.hostname.trim().toLowerCase();
  const hostname = normalized.startsWith('[') && normalized.endsWith(']')
    ? normalized.slice(1, -1)
    : normalized;
  if (hostname === 'localhost' || hostname === '::1' || hostname === '0:0:0:0:0:0:0:1') {
    return true;
  }

  const octets = hostname.split('.');
  if (octets.length !== 4 || !octets.every((octet) => /^\d{1,3}$/.test(octet))) {
    return false;
  }
  const numericOctets = octets.map(Number);
  return numericOctets.every((octet) => octet >= 0 && octet <= 255)
    && numericOctets[0] === 127;
}
// END_BLOCK: TODAY_PREVIEW_MARKER

// START_BLOCK: ERROR_TYPES
/**
 * Custom error class for API errors with status code and optional error code
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Custom error class for API contract validation errors
 */
export class ApiContractError extends ApiError {
  // START_FUNCTION_CONTRACT: F-M-WEB-API-CLIENT.ApiContractError.constructor
  // purpose: Construct a safe public error for an invalid Today API payload.
  // inputs: none.
  // returns: ApiContractError with fixed name/status/code/message.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: none.
  // END_FUNCTION_CONTRACT: F-M-WEB-API-CLIENT.ApiContractError.constructor
  constructor() {
    super('Invalid Today payload format from backend', 502, 'SCHEMA_VALIDATION_ERROR');
    this.name = 'ApiContractError';
  }
}
// END_BLOCK: ERROR_TYPES

// START_BLOCK: API_CLIENT_LOGIC
// START_FUNCTION_CONTRACT: F-M-WEB-API-CLIENT.fetchDay
// purpose: Fetch day data for a specific date and validate it against TodayPayloadWireSchema.
// inputs: date - ISO date string (YYYY-MM-DD)
// returns: Promise<TodayPayload>
// side_effects: Network call to /api/day/${date}
// emitted_logs: none.
// error_behavior: throws ApiError on HTTP failures; throws ApiContractError on schema mismatches.
// END_FUNCTION_CONTRACT: F-M-WEB-API-CLIENT.fetchDay
export async function fetchDay(date: string): Promise<TodayPayload> {
  const headers: Record<string, string> = {
    'Accept': 'application/json',
  };
  if (typeof window !== 'undefined' && shouldEmitTodayPreviewMarker({
    nodeEnv: process.env.NODE_ENV,
    hostname: window.location.hostname,
    port: window.location.port,
  })) {
    headers[TODAY_PREVIEW_HEADER_NAME] = TODAY_PREVIEW_HEADER_VALUE;
  }

  const res = await fetch(`${API_BASE}/api/day/${date}`, {
    credentials: 'include', // Send session cookie for auth
    headers,
  });

  if (!res.ok) {
    let errorMessage = 'Failed to fetch day';
    let errorCode: string | undefined;

    try {
      const error = await res.json();
      errorMessage = error.detail?.message || error.detail || errorMessage;
      errorCode = error.detail?.code;
    } catch {
      // If response is not JSON, use status text
      errorMessage = res.statusText || errorMessage;
    }

    throw new ApiError(errorMessage, res.status, errorCode);
  }

  const rawJson: unknown = await res.json();
  const parsed = TodayPayloadWireSchema.safeParse(rawJson);
  if (!parsed.success) {
    throw new ApiContractError();
  }

  return parsed.data;
}

// START_FUNCTION_CONTRACT: F-M-WEB-API-CLIENT.fetchCalendar
// purpose: Fetch calendar data for a specific month.
// inputs: month - Month string (YYYY-MM)
// returns: Promise<CalendarPayload>
// side_effects: Network call to /api/calendar?month=${month}
// emitted_logs: none.
// error_behavior: throws ApiError on HTTP failures.
// END_FUNCTION_CONTRACT: F-M-WEB-API-CLIENT.fetchCalendar
export async function fetchCalendar(month: string): Promise<CalendarPayload> {
  const res = await fetch(`${API_BASE}/api/calendar?month=${month}`, {
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!res.ok) {
    let errorMessage = 'Failed to fetch calendar';
    let errorCode: string | undefined;

    try {
      const error = await res.json();
      errorMessage = error.detail?.message || error.detail || errorMessage;
      errorCode = error.detail?.code;
    } catch {
      errorMessage = res.statusText || errorMessage;
    }

    throw new ApiError(errorMessage, res.status, errorCode);
  }

  return res.json();
}
// END_BLOCK: API_CLIENT_LOGIC
