// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_FIXTURE_CALENDAR_2026_07
// ROLE: Contract-valid CalendarPayload fixture for mock visual e2e.
//       Provides lunar data for July 2026 so the day overview card renders
//       real lunar info instead of "Лунные данные загружаются".
// ############################################################################

import type { components } from "../../../packages/contracts/_generated";

export const calendarPayload: components["schemas"]["CalendarPayload"] = {
  meta: {
    schemaVersion: "calendar/v1",
    contractVersion: 1,
    generatedAt: "2026-07-05T06:00:00Z",
  },
  month: "2026-07",
  title: "Июль 2026",
  allowedRange: {
    from: "2025-07-05",
    to: "2027-07-05",
  },
  days: [
    { date: "2026-06-29", dayNumber: 180, isCurrentMonth: false, isToday: false, disabled: false, dayStatus: "steady", lunar: {} },
    { date: "2026-06-30", dayNumber: 181, isCurrentMonth: false, isToday: false, disabled: false, dayStatus: "tense", lunar: {} },
    { date: "2026-07-01", dayNumber: 182, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "supportive", lunar: { phase: "Убывающая", illumination: 98, moonSign: "Козерог", lunarDay: 16, voidOfCourse: false } },
    { date: "2026-07-02", dayNumber: 183, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "steady", lunar: { phase: "Убывающая", illumination: 93, moonSign: "Водолей", lunarDay: 17, voidOfCourse: false } },
    { date: "2026-07-03", dayNumber: 184, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "tense", lunar: { phase: "Убывающая", illumination: 85, moonSign: "Водолей", lunarDay: 18, voidOfCourse: false } },
    { date: "2026-07-04", dayNumber: 185, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "steady", lunar: { phase: "Убывающая", illumination: 75, moonSign: "Рыбы", lunarDay: 19, voidOfCourse: false } },
    { date: "2026-07-05", dayNumber: 186, isCurrentMonth: true, isToday: true, disabled: false, dayStatus: "supportive", lunar: { phase: "Убывающая Луна", illumination: 63, moonSign: "Рыбы", lunarDay: 20, voidOfCourse: false } },
    { date: "2026-07-06", dayNumber: 187, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "steady", lunar: { phase: "Убывающая", illumination: 50, moonSign: "Овен", lunarDay: 21, voidOfCourse: false } },
    { date: "2026-07-07", dayNumber: 188, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "supportive", lunar: { phase: "Убывающая", illumination: 37, moonSign: "Овен", lunarDay: 22, voidOfCourse: false } },
    { date: "2026-07-08", dayNumber: 189, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "tense", lunar: {} },
    { date: "2026-07-09", dayNumber: 190, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "steady", lunar: {} },
    { date: "2026-07-10", dayNumber: 191, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "supportive", lunar: {} },
    { date: "2026-07-11", dayNumber: 192, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "steady", lunar: {} },
    { date: "2026-07-12", dayNumber: 193, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "tense", lunar: {} },
    { date: "2026-07-13", dayNumber: 194, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "supportive", lunar: {} },
    { date: "2026-07-14", dayNumber: 195, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "steady", lunar: {} },
    { date: "2026-07-15", dayNumber: 196, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "tense", lunar: {} },
    { date: "2026-07-16", dayNumber: 197, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "supportive", lunar: {} },
    { date: "2026-07-17", dayNumber: 198, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "steady", lunar: {} },
    { date: "2026-07-18", dayNumber: 199, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "tense", lunar: {} },
    { date: "2026-07-19", dayNumber: 200, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "steady", lunar: {} },
    { date: "2026-07-20", dayNumber: 201, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "supportive", lunar: {} },
    { date: "2026-07-21", dayNumber: 202, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "steady", lunar: {} },
    { date: "2026-07-22", dayNumber: 203, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "tense", lunar: {} },
    { date: "2026-07-23", dayNumber: 204, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "supportive", lunar: {} },
    { date: "2026-07-24", dayNumber: 205, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "steady", lunar: {} },
    { date: "2026-07-25", dayNumber: 206, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "tense", lunar: {} },
    { date: "2026-07-26", dayNumber: 207, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "steady", lunar: {} },
    { date: "2026-07-27", dayNumber: 208, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "supportive", lunar: {} },
    { date: "2026-07-28", dayNumber: 209, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "supportive", lunar: {} },
    { date: "2026-07-29", dayNumber: 210, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "steady", lunar: {} },
    { date: "2026-07-30", dayNumber: 211, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "tense", lunar: {} },
    { date: "2026-07-31", dayNumber: 212, isCurrentMonth: true, isToday: false, disabled: false, dayStatus: "steady", lunar: {} },
    { date: "2026-08-01", dayNumber: 213, isCurrentMonth: false, isToday: false, disabled: false, dayStatus: "supportive", lunar: {} },
  ],
};
