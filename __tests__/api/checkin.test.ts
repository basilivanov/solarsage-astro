// ############################################################################
// AI_HEADER: TEST_API_CHECKIN_V2 — Yesterday recap and observed-spheres client tests.
// ROLE: Verifies generated YesterdayCheckinResponse parsing and canonical POST payload wiring.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-API-CHECKIN-V2
// purpose: Test the check-in client against the snapshot-aware Yesterday envelope.
// owns:
//   - __tests__/api/checkin.test.ts
// inputs: generated Yesterday fixtures, mocked instrumented fetch, and local dates.
// outputs: parsed recap, observed sphere request, date helper, and error assertions.
// dependencies: lib/api/checkin, generated fixture barrel, instrumentedFetch.
// side_effects: none.
// invariants: forecastRecap is validated at the boundary; observed spheres use canonical keys and camelCase wire naming.
// failure_policy: fail on HTTP, schema, or date-lineage drift.
// END_MODULE_CONTRACT: M-TEST-API-CHECKIN-V2

// START_MODULE_MAP: M-TEST-API-CHECKIN-V2
// public_entrypoints:
//   - Yesterday response parsing
//   - check-in create payload
//   - local-date helpers
// semantic_blocks:
//   - YESTERDAY_RESPONSE
//   - CREATE_PAYLOAD
//   - DATE_RESOLUTION
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-API-CHECKIN-V2

import { beforeEach, describe, expect, it, vi } from "vitest";
import { yesterdayPostSubmit, yesterdayPreSubmit } from "../fixtures/today_convergence_v2";

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}));

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}));

import {
  createCheckin,
  formatDateInTimeZone,
  getYesterdayCheckin,
  resolveCheckinTargetDate,
} from "@/lib/api/checkin";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  vi.clearAllMocks();
});

// START_BLOCK: YESTERDAY_RESPONSE
describe("getYesterdayCheckin snapshot recap", () => {
  it("parses pre-submit response without exposing recap", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, yesterdayPreSubmit));

    const result = await getYesterdayCheckin();

    expect(result.forecastAvailable).toBe(true);
    expect(result.forecastRecap).toBeNull();
    expect(result.checkin).toBeNull();
    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "checkin.get_yesterday",
        routeTemplate: "GET /api/checkin/yesterday",
        url: "/api/checkin/yesterday",
      }),
    );
  });

  it("parses post-submit recap with tone and sphere keys", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, yesterdayPostSubmit));

    const result = await getYesterdayCheckin();

    expect(result.forecastRecap).toEqual({
      snapshotId: "snap_v1_00000000000000000000000000000161",
      state: "quiet_day",
      dayTone: "steady",
      sphereKeys: ["work", "communication"],
    });
  });

  it("rejects malformed Yesterday envelopes", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, {
      targetDate: "2026-08-01",
      hadCheckin: false,
      forecastRecap: { state: "quiet_day" },
    }));

    await expect(getYesterdayCheckin()).rejects.toThrow("неверный формат");
  });
});
// END_BLOCK: YESTERDAY_RESPONSE

// START_BLOCK: CREATE_PAYLOAD
describe("createCheckin observed spheres", () => {
  it("sends canonical observedSpheres in the real POST payload", async () => {
    const response = {
      id: 91,
      targetDate: "2026-08-01",
      mood: 4,
      accuracy: 2,
      energy: 3,
      tags: [],
      note: null,
      streak: 2,
      filledAt: "2026-08-01T21:15:00+03:00",
      createdAt: "2026-08-01T21:15:00+03:00",
      observedSpheres: ["work", "communication"],
    };
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, response));

    await createCheckin({
      targetDate: "2026-08-01",
      mood: 4,
      accuracy: 2,
      energy: 3,
      tags: [],
      note: null,
      observedSpheres: ["work", "communication"],
    });

    const request = mockInstrumentedFetch.mock.calls[0][0];
    expect(request.init.method).toBe("POST");
    expect(JSON.parse(request.init.body)).toMatchObject({
      targetDate: "2026-08-01",
      observedSpheres: ["work", "communication"],
    });
    expect(request.init.credentials).toBe("include");
  });

  it("preserves backend error messages", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(422, {
      detail: "Check-in is closed",
    }));

    await expect(createCheckin({ mood: 3, targetDate: "2026-08-01" })).rejects.toThrow("Check-in is closed");
  });
});
// END_BLOCK: CREATE_PAYLOAD

// START_BLOCK: DATE_RESOLUTION
describe("check-in local-date resolution", () => {
  it("formats the same instant according to the user timezone", () => {
    const value = new Date("2026-08-01T23:30:00Z");
    expect(formatDateInTimeZone(value, "Europe/Moscow")).toBe("2026-08-02");
    expect(formatDateInTimeZone(value, "America/Los_Angeles")).toBe("2026-08-01");
  });

  it("resolves yesterday across a month boundary and preserves explicit ISO target", () => {
    const value = new Date("2026-08-01T00:30:00Z");
    expect(resolveCheckinTargetDate(value, "Europe/Moscow", "yesterday")).toBe("2026-07-31");
    expect(resolveCheckinTargetDate(value, "Europe/Moscow", "2026-07-15")).toBe("2026-07-15");
  });
});
// END_BLOCK: DATE_RESOLUTION
