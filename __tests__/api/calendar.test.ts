// ############################################################################
// AI_HEADER: TEST_API_CALENDAR_V2 — calendar v2 client boundary tests.
// ROLE: Verifies generated calendar parsing, request instrumentation, and typed malformed-payload errors.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-API-CALENDAR-V2
// purpose: Validate fetchCalendar against the generated calendar/v2 envelope.
// owns:
//   - __tests__/api/calendar.test.ts
// inputs: instrumented fetch responses and generated CalendarPayload fixtures.
// outputs: parsed payloads or ApiContractError assertions.
// dependencies: lib/grace/api/client, generated runtime schema, instrumentedFetch.
// side_effects: none.
// emitted_logs: none.
// invariants: dayState is the only calendar state axis; all three values remain parseable.
// failure_policy: fail on request/schema contract drift.
// END_MODULE_CONTRACT: M-TEST-API-CALENDAR-V2

// START_MODULE_MAP: M-TEST-API-CALENDAR-V2
// public_entrypoints:
//   - fetchCalendar request and schema tests
// semantic_blocks:
//   - REQUEST_AND_PARSE
//   - ERROR_BOUNDARY
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-API-CALENDAR-V2

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CalendarPayload } from "@/packages/contracts";

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}));

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}));

import { ApiContractError, fetchCalendar } from "@/lib/grace/api/client";

const calendarPayload: CalendarPayload = {
  allowedRange: { from: "2026-01-01", to: "2026-12-31" },
  days: [
    {
      access: { state: "full" },
      date: "2026-08-01",
      dayNumber: 1,
      dayState: "hero",
      disabled: false,
      isCurrentMonth: true,
      isToday: false,
    },
    {
      access: { state: "full" },
      date: "2026-08-02",
      dayNumber: 2,
      dayState: "ordinary",
      disabled: false,
      isCurrentMonth: true,
      isToday: false,
    },
    {
      access: { state: "full" },
      date: "2026-08-03",
      dayNumber: 3,
      dayState: "not-computed",
      disabled: false,
      isCurrentMonth: true,
      isToday: false,
    },
  ],
  meta: {
    contractVersion: 2,
    generatedAt: "2026-07-31T00:00:00Z",
    schemaVersion: "calendar/v2",
  },
  month: "2026-08",
  title: "Август 2026",
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  vi.clearAllMocks();
});

// START_BLOCK: REQUEST_AND_PARSE
describe("fetchCalendar calendar/v2 boundary", () => {
  it("fetches and returns generated dayState payload", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, calendarPayload));

    const result = await fetchCalendar("2026-08");

    expect(result.days.map((day) => day.dayState)).toEqual([
      "hero",
      "ordinary",
      "not-computed",
    ]);
    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "calendar.fetch",
        routeTemplate: "GET /api/calendar",
        url: "/api/calendar?month=2026-08",
        responseContract: expect.objectContaining({
          contractName: "CalendarPayload",
        }),
      }),
    );
    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract;
    expect(contract.validate(calendarPayload)).toEqual({ valid: true });
    expect(contract.validate({ ...calendarPayload, days: [] })).toEqual({ valid: true });
  });
});
// END_BLOCK: REQUEST_AND_PARSE

// START_BLOCK: ERROR_BOUNDARY
describe("fetchCalendar error boundary", () => {
  it("rejects malformed generated payloads with a typed contract error", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, {
      ...calendarPayload,
      days: [{ ...calendarPayload.days[0], dayState: "unknown" }],
    }));

    await expect(fetchCalendar("2026-08")).rejects.toBeInstanceOf(ApiContractError);
  });

  it("preserves typed HTTP failure status", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(503, { detail: "Calendar unavailable" }));

    await expect(fetchCalendar("2026-08")).rejects.toMatchObject({ status: 503 });
  });
});
// END_BLOCK: ERROR_BOUNDARY
