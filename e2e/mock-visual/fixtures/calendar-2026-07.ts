// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_FIXTURE_CALENDAR_2026_07
// ROLE: Contract-valid CalendarPayload fixture for mock visual e2e.
//       Provides v2 backend-shaped lunar data for July 2026.
// ############################################################################

import type { components } from "../../../packages/contracts/_generated";

type CalendarDay = components["schemas"]["CalendarDay"];
type CalendarLunarFields = components["schemas"]["CalendarLunarFields"];

export const accessPayload: components["schemas"]["AccessSummary"] = {
  user: "trial",
  referralDaysLeft: 8,
  subscriptionActive: false,
  accessStart: "2026-07-01",
  accessUntil: "2026-07-08",
};

const PHASE_KEYS = [
  "new_moon",
  "waxing_crescent",
  "first_quarter",
  "waxing_gibbous",
  "full_moon",
  "waning_gibbous",
  "last_quarter",
  "waning_crescent",
] as const;

const PHASE_LABELS = [
  "новолуние",
  "раст. серп",
  "перв. четв.",
  "раст. Луна",
  "полнолуние",
  "убыв. Луна",
  "посл. четв.",
  "убыв. серп",
] as const;

const SIGNS = [
  ["Aries", "Овен"],
  ["Taurus", "Телец"],
  ["Gemini", "Близнецы"],
  ["Cancer", "Рак"],
  ["Leo", "Лев"],
  ["Virgo", "Дева"],
  ["Libra", "Весы"],
  ["Scorpio", "Скорпион"],
  ["Sagittarius", "Стрелец"],
  ["Capricorn", "Козерог"],
  ["Aquarius", "Водолей"],
  ["Pisces", "Рыбы"],
] as const;

// Generated from apps/api/app/services/lunar_facts_service.py
// LunarFactsService.facts_for_date(date(2026, 7, day)) on 2026-07-08.
const julyLunar: Record<number, {
  phaseIndex: number;
  illumination: number;
  lunarDay: number;
  signIndex: number;
  voidOfCourse: boolean;
}> = {
  1: { phaseIndex: 4, illumination: 98, lunarDay: 17, signIndex: 9, voidOfCourse: false },
  2: { phaseIndex: 5, illumination: 93, lunarDay: 18, signIndex: 10, voidOfCourse: false },
  3: { phaseIndex: 5, illumination: 87, lunarDay: 19, signIndex: 10, voidOfCourse: false },
  4: { phaseIndex: 5, illumination: 79, lunarDay: 20, signIndex: 10, voidOfCourse: false },
  5: { phaseIndex: 5, illumination: 70, lunarDay: 21, signIndex: 11, voidOfCourse: false },
  6: { phaseIndex: 5, illumination: 60, lunarDay: 22, signIndex: 11, voidOfCourse: false },
  7: { phaseIndex: 6, illumination: 49, lunarDay: 23, signIndex: 0, voidOfCourse: false },
  8: { phaseIndex: 7, illumination: 39, lunarDay: 24, signIndex: 0, voidOfCourse: false },
  9: { phaseIndex: 7, illumination: 28, lunarDay: 25, signIndex: 0, voidOfCourse: false },
  10: { phaseIndex: 7, illumination: 19, lunarDay: 26, signIndex: 1, voidOfCourse: false },
  11: { phaseIndex: 7, illumination: 12, lunarDay: 27, signIndex: 1, voidOfCourse: false },
  12: { phaseIndex: 7, illumination: 6, lunarDay: 28, signIndex: 2, voidOfCourse: false },
  13: { phaseIndex: 7, illumination: 2, lunarDay: 29, signIndex: 2, voidOfCourse: false },
  14: { phaseIndex: 4, illumination: 0, lunarDay: 30, signIndex: 2, voidOfCourse: false },
  15: { phaseIndex: 0, illumination: 1, lunarDay: 1, signIndex: 3, voidOfCourse: false },
  16: { phaseIndex: 1, illumination: 3, lunarDay: 2, signIndex: 3, voidOfCourse: false },
  17: { phaseIndex: 1, illumination: 8, lunarDay: 3, signIndex: 4, voidOfCourse: false },
  18: { phaseIndex: 1, illumination: 15, lunarDay: 4, signIndex: 4, voidOfCourse: false },
  19: { phaseIndex: 1, illumination: 23, lunarDay: 5, signIndex: 4, voidOfCourse: false },
  20: { phaseIndex: 1, illumination: 33, lunarDay: 6, signIndex: 5, voidOfCourse: false },
  21: { phaseIndex: 1, illumination: 43, lunarDay: 7, signIndex: 5, voidOfCourse: false },
  22: { phaseIndex: 3, illumination: 53, lunarDay: 8, signIndex: 6, voidOfCourse: false },
  23: { phaseIndex: 3, illumination: 64, lunarDay: 9, signIndex: 6, voidOfCourse: false },
  24: { phaseIndex: 3, illumination: 74, lunarDay: 10, signIndex: 6, voidOfCourse: true },
  25: { phaseIndex: 3, illumination: 82, lunarDay: 11, signIndex: 7, voidOfCourse: false },
  26: { phaseIndex: 3, illumination: 90, lunarDay: 12, signIndex: 7, voidOfCourse: false },
  27: { phaseIndex: 3, illumination: 95, lunarDay: 13, signIndex: 8, voidOfCourse: false },
  28: { phaseIndex: 4, illumination: 99, lunarDay: 14, signIndex: 8, voidOfCourse: false },
  29: { phaseIndex: 4, illumination: 100, lunarDay: 15, signIndex: 8, voidOfCourse: true },
  30: { phaseIndex: 4, illumination: 99, lunarDay: 16, signIndex: 9, voidOfCourse: false },
  31: { phaseIndex: 5, illumination: 96, lunarDay: 17, signIndex: 9, voidOfCourse: false },
};

function lunarFor(date: string): CalendarLunarFields {
  const day = Number(date.slice(8, 10));
  const month = Number(date.slice(5, 7));
  const fallback = {
    phaseIndex: (day + month) % 8,
    illumination: 20 + ((day * 7) % 70),
    lunarDay: ((day + 15) % 29) + 1,
    signIndex: (day + month) % SIGNS.length,
    voidOfCourse: false,
  };
  const source = month === 7 ? julyLunar[day] ?? fallback : fallback;
  const sign = SIGNS[source.signIndex];

  return {
    phase: PHASE_KEYS[source.phaseIndex],
    phaseIndex: source.phaseIndex,
    phaseLabel: PHASE_LABELS[source.phaseIndex],
    illumination: source.illumination,
    moonSign: sign[0],
    moonSignLabel: sign[1],
    lunarDay: source.lunarDay,
    voidOfCourse: source.voidOfCourse,
  };
}

function accessFor(date: string): CalendarDay["access"] {
  if (date === "2026-07-12") {
    return {
      state: "locked",
      reason: "outside_access_window",
      referralDaysLeft: 0,
      subscriptionActive: false,
      accessUntil: "2026-07-08",
    };
  }
  return {
    state: "full",
    reason: "active_referral_days",
    referralDaysLeft: 8,
    subscriptionActive: false,
    accessUntil: "2026-07-08",
  };
}

function statusFor(day: number): CalendarDay["dayStatus"] {
  if (day % 5 === 0) return "supportive";
  if (day % 4 === 0) return "tense";
  return "steady";
}

function day(date: string, isCurrentMonth: boolean, isToday = false): CalendarDay {
  const dayNumber = Number(date.slice(8, 10));
  return {
    date,
    dayNumber,
    isCurrentMonth,
    isToday,
    disabled: !isCurrentMonth,
    dayStatus: statusFor(dayNumber),
    access: accessFor(date),
    lunar: lunarFor(date),
  };
}

export const calendarPayload: components["schemas"]["CalendarPayload"] = {
  meta: {
    schemaVersion: "calendar/v1",
    contractVersion: 2,
    generatedAt: "2026-07-08T06:00:00Z",
  },
  month: "2026-07",
  title: "July 2026",
  allowedRange: {
    from: "2025-07-08",
    to: "2027-07-08",
  },
  days: [
    day("2026-06-29", false),
    day("2026-06-30", false),
    ...Array.from({ length: 31 }, (_, index) => {
      const dayNumber = String(index + 1).padStart(2, "0");
      return day(`2026-07-${dayNumber}`, true, dayNumber === "08");
    }),
    ...Array.from({ length: 9 }, (_, index) => {
      const dayNumber = String(index + 1).padStart(2, "0");
      return day(`2026-08-${dayNumber}`, false);
    }),
  ],
};

export const dayPayload = {
  date: "2026-07-10",
  dayStatus: "supportive",
  access: accessFor("2026-07-10"),
};
