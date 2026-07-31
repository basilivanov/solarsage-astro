// ############################################################################
// AI_HEADER: TEST_CONTRACT_CALENDAR_V2 — generated calendar state validation tests.
// ROLE: Keeps the calendar contract on hero/ordinary/not-computed without reviving legacy fields.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-CONTRACT-CALENDAR-V2
// purpose: Validate the generated calendar/v2 schema and its three dayState values.
// owns:
//   - __tests__/contracts/calendar.test.ts
// inputs: generated CalendarPayload fixture variants.
// outputs: safeParse success/failure assertions.
// dependencies: packages/contracts/runtime CalendarPayloadWireSchema.
// side_effects: none.
// invariants: the legacy validator remains untouched for W9 cleanup; active tests use generated dayState.
// failure_policy: fail on generated contract drift.
// END_MODULE_CONTRACT: M-TEST-CONTRACT-CALENDAR-V2

// START_MODULE_MAP: M-TEST-CONTRACT-CALENDAR-V2
// public_entrypoints:
//   - calendar/v2 schema assertions
// semantic_blocks:
//   - DAY_STATE_VALUES
//   - PAYLOAD_BOUNDARY
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-CONTRACT-CALENDAR-V2

import { describe, expect, it } from "vitest";
import { CalendarPayloadWireSchema } from "@/packages/contracts/runtime";

const basePayload = {
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
  ],
  meta: {
    contractVersion: 2,
    generatedAt: "2026-07-31T00:00:00Z",
    schemaVersion: "calendar/v2",
  },
  month: "2026-08",
  title: "Август 2026",
};

// START_BLOCK: DAY_STATE_VALUES
describe("CalendarPayloadWireSchema dayState", () => {
  it.each(["hero", "ordinary", "not-computed"])("accepts %s", (dayState) => {
    const result = CalendarPayloadWireSchema.safeParse({
      ...basePayload,
      days: [{ ...basePayload.days[0], dayState }],
    });
    expect(result.success).toBe(true);
  });
});
// END_BLOCK: DAY_STATE_VALUES

// START_BLOCK: PAYLOAD_BOUNDARY
describe("CalendarPayloadWireSchema payload boundary", () => {
  it("accepts the complete generated payload", () => {
    expect(CalendarPayloadWireSchema.parse(basePayload).meta.schemaVersion).toBe("calendar/v2");
  });

  it("rejects an unknown day state and an incomplete day", () => {
    expect(CalendarPayloadWireSchema.safeParse({
      ...basePayload,
      days: [{ ...basePayload.days[0], dayState: "missing" }],
    }).success).toBe(false);
    expect(CalendarPayloadWireSchema.safeParse({
      ...basePayload,
      days: [{ date: "2026-08-01" }],
    }).success).toBe(false);
  });
});
// END_BLOCK: PAYLOAD_BOUNDARY
