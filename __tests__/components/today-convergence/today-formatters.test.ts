// ############################################################################
// AI_HEADER: TEST_TODAY_CONVERGENCE_FORMATTERS — branch acceptance for Today presentation helpers.
// ROLE: Exercises pure formatter fallbacks (malformed dates, absolute instants, window ladders) without rendering.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-FORMATTERS
// purpose: Cover the deterministic fallback branches of today-formatters that fixture rendering does not reach.
// owns:
//   - __tests__/components/today-convergence/today-formatters.test.ts
// inputs: synthetic TodayConvergenceEventTime values, sphere keys, target dates.
// outputs: Vitest assertions on returned Russian labels and EventTimeParts.
// dependencies: components/today-convergence/today-formatters.tsx.
// side_effects: none.
// emitted_logs: none.
// invariants: expectations are timezone-independent (wire-local rendering paths only).
// failure_policy: any drift in fallback copy fails the test.
// END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-FORMATTERS

// START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-FORMATTERS
// public_entrypoints:
//   - vitest suite
// semantic_blocks:
//   - TARGET_DATE: malformed and out-of-range payload dates.
//   - LABELS: sphere label fallback for unknown keys.
//   - EVENT_TIME_ABSOLUTE: absolute instant/window rendering and degradation.
//   - EVENT_TIME_PARTS: peak/window/fallback ladder of formatEventTimeParts.
// owned_tests: none (this file is the test).
// END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-FORMATTERS

import { describe, expect, it } from "vitest";

import {
  formatEventTime,
  formatEventTimeParts,
  formatTargetDateRu,
  getEventTimeDateTime,
  getTodaySphereLabel,
} from "@/components/today-convergence/today-formatters";

// START_BLOCK: TARGET_DATE
describe("formatTargetDateRu", () => {
  it("keeps malformed and out-of-range dates unchanged", () => {
    expect(formatTargetDateRu("2026-08-03")).toBe("3 августа");
    expect(formatTargetDateRu("03.08.2026")).toBe("03.08.2026");
    expect(formatTargetDateRu("2026-13-01")).toBe("2026-13-01");
    expect(formatTargetDateRu("2026-02-32")).toBe("2026-02-32");
  });
});
// END_BLOCK: TARGET_DATE

// START_BLOCK: LABELS
describe("getTodaySphereLabel", () => {
  it("labels canonical keys and degrades unknown keys", () => {
    expect(getTodaySphereLabel("finance")).toBe("Финансы");
    expect(getTodaySphereLabel("quantum")).toBe("Другая сфера");
  });
});
// END_BLOCK: LABELS

// START_BLOCK: EVENT_TIME_ABSOLUTE
describe("getEventTimeDateTime", () => {
  it("returns the absolute peak instant when present", () => {
    expect(
      getEventTimeDateTime({ mode: "exact", peakAt: "2026-08-01T11:34:00+03:00" }),
    ).toBe("2026-08-01T11:34:00+03:00");
    expect(getEventTimeDateTime({ mode: "exact", peak: "09:30" })).toBeUndefined();
  });
});

describe("formatEventTime absolute fallbacks", () => {
  it("renders absolute peak and window from wire-local values", () => {
    expect(
      formatEventTime({
        mode: "exact",
        peakAt: "2026-08-01T11:34:00+03:00",
        startAt: "2026-08-01T08:00:00+03:00",
        endAt: "2026-08-01T18:00:00+03:00",
      }),
    ).toBe("пик 1 августа, 11:34, окно: с 1 августа, 08:00 до 1 августа, 18:00");
  });

  it("renders one-sided absolute windows", () => {
    expect(
      formatEventTime({
        mode: "exact",
        startAt: "2026-08-01T08:00:00+03:00",
        endAt: "2026-08-01T18:00:00+03:00",
      }),
    ).toBe("окно: с 1 августа, 08:00 до 1 августа, 18:00");
    expect(formatEventTime({ mode: "exact", startAt: "2026-08-01T08:00:00+03:00" })).toBe(
      "окно: с 1 августа, 08:00",
    );
    expect(formatEventTime({ mode: "exact", endAt: "2026-08-01T18:00:00+03:00" })).toBe(
      "окно: до 1 августа, 18:00",
    );
  });

  it("degrades unparseable absolute values to the neutral label", () => {
    expect(formatEventTime({ mode: "exact", peakAt: "junk" })).toBe("точное время события");
    expect(formatEventTime({ mode: "exact", peakAt: "2026-08" })).toBe("точное время события");
  });

  it("falls back to wire-local formatting for an unknown timezone", () => {
    expect(
      formatEventTime({ mode: "exact", peakAt: "2026-08-01T11:34:00+03:00" }, "Bogus/Zone"),
    ).toBe("пик 1 августа, 11:34");
  });

  it("labels part-of-day and date modes", () => {
    expect(formatEventTime({ mode: "partofday", partOfDay: "morning" })).toBe("утром");
    expect(formatEventTime({ mode: "partofday", partOfDay: "night" })).toBe("ночью");
    expect(formatEventTime({ mode: "date" })).toBe("в течение даты");
  });
});
// END_BLOCK: EVENT_TIME_ABSOLUTE

// START_BLOCK: EVENT_TIME_PARTS
describe("formatEventTimeParts", () => {
  it("keeps legacy clock-only peaks and windows", () => {
    expect(formatEventTimeParts({ mode: "exact", peak: "09:30" })).toMatchObject({
      peak: "Пик: 09:30",
      window: null,
      fallback: null,
    });
    expect(
      formatEventTimeParts({ mode: "exact", peak: "10:06", start: "22:42", end: "21:21" }),
    ).toMatchObject({ peak: "Пик: 10:06", window: "Окно: 22:42 → 21:21" });
    expect(formatEventTimeParts({ mode: "exact", start: "08:00" })).toMatchObject({
      window: "Окно: с 08:00",
    });
  });

  it("collapses same-day absolute windows to clocks", () => {
    expect(
      formatEventTimeParts({
        mode: "exact",
        startAt: "2026-08-01T08:00:00+03:00",
        endAt: "2026-08-01T18:00:00+03:00",
      }),
    ).toMatchObject({ window: "Окно: 08:00–18:00", fallback: null });
    expect(
      formatEventTimeParts(
        {
          mode: "exact",
          startAt: "2026-08-01T08:00:00+03:00",
          endAt: "2026-08-01T18:00:00+03:00",
        },
        "Bogus/Zone",
      ),
    ).toMatchObject({ window: "Окно: 08:00–18:00" });
  });

  it("collapses multi-day absolute windows to date ranges", () => {
    expect(
      formatEventTimeParts({
        mode: "exact",
        startAt: "2026-08-01T20:00:00+03:00",
        endAt: "2026-08-05T21:00:00+03:00",
      }),
    ).toMatchObject({ window: "Окно: 1 — 5 августа" });
    expect(
      formatEventTimeParts({
        mode: "exact",
        startAt: "2026-08-01T20:00:00+03:00",
        endAt: "2026-09-02T21:00:00+03:00",
      }),
    ).toMatchObject({ window: "Окно: 1 августа — 2 сентября" });
  });

  it("degrades incomplete absolute windows to one-sided lines or fallback", () => {
    expect(
      formatEventTimeParts({ mode: "exact", endAt: "2026-08-01T18:00:00+03:00" }),
    ).toMatchObject({ window: "Окно: до 1 августа, 18:00" });
    expect(
      formatEventTimeParts({
        mode: "exact",
        startAt: "junk",
        endAt: "2026-08-05T21:00:00+03:00",
      }),
    ).toMatchObject({ peak: null, window: null, fallback: "точное время события" });
    expect(
      formatEventTimeParts({ mode: "exact", startAt: "2026-08-01", endAt: "2026-08-02" }),
    ).toMatchObject({ peak: null, window: null, fallback: "точное время события" });
  });

  it("labels soft modes without inventing clocks", () => {
    expect(formatEventTimeParts({ mode: "partofday", partOfDay: "evening" })).toMatchObject({
      fallback: "вечером",
    });
    expect(formatEventTimeParts({ mode: "partofday", partOfDay: null })).toMatchObject({
      fallback: "в течение дня",
    });
    expect(formatEventTimeParts({ mode: "date" })).toMatchObject({
      fallback: "в течение даты",
    });
  });
});
// END_BLOCK: EVENT_TIME_PARTS
