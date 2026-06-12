
// ############################################################################
// AI_HEADER: MODULE_API_CLIENT
// ROLE: Lib — client.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-LOGGING-SPINE
// ############################################################################
// START_MODULE_CONTRACT
// purpose: API client for client
// owns:
//   - lib/grace/api/client.ts
// inputs: Endpoint params, request body
// outputs: Parsed response / typed data
// dependencies: local modules
// side_effects: Network calls to API
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-WEB-API-CLIENT
// wave: W-2.1
// purpose: API client for backend endpoints with type-safe contracts

import { IS_DEMO_MODE } from '@/lib/demo-mode';
import { DEMO_TODAY_RESPONSE, DEMO_CALENDAR_RESPONSE } from '@/lib/demo-data';
import type { TodayPayload, CalendarPayload } from '@/packages/contracts';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

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
 * Fetch day data for a specific date
 * @param date - ISO date string (YYYY-MM-DD)
 * @returns TodayPayload with full day data
 * @throws ApiError on HTTP errors
 */
export async function fetchDay(date: string): Promise<TodayPayload> {
  if (IS_DEMO_MODE) return DEMO_TODAY_RESPONSE as unknown as TodayPayload;

  const res = await fetch(`${API_BASE}/api/day/${date}`, {
    credentials: 'include', // Send session cookie for auth
    headers: {
      'Accept': 'application/json',
    },
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

  return res.json();
}

/**
 * Fetch calendar data for a specific month
 * @param month - Month string (YYYY-MM)
 * @returns CalendarPayload with calendar days
 * @throws ApiError on HTTP errors
 */
export async function fetchCalendar(month: string): Promise<CalendarPayload> {
  if (IS_DEMO_MODE) return DEMO_CALENDAR_RESPONSE as unknown as CalendarPayload;

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
