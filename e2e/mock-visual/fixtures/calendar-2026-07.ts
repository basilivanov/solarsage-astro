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

const julyLunar: Record<number, { phaseIndex: number; illumination: number; lunarDay: number }> = {
  1: { phaseIndex: 5, illumination: 98, lunarDay: 16 },
  2: { phaseIndex: 5, illumination: 93, lunarDay: 17 },
  3: { phaseIndex: 5, illumination: 87, lunarDay: 18 },
  4: { phaseIndex: 5, illumination: 79, lunarDay: 19 },
  5: { phaseIndex: 5, illumination: 63, lunarDay: 20 },
  6: { phaseIndex: 6, illumination: 50, lunarDay: 21 },
  7: { phaseIndex: 7, illumination: 41, lunarDay: 22 },
  8: { phaseIndex: 7, illumination: 39, lunarDay: 24 },
  9: { phaseIndex: 7, illumination: 28, lunarDay: 25 },
  10: { phaseIndex: 7, illumination: 19, lunarDay: 26 },
  11: { phaseIndex: 0, illumination: 4, lunarDay: 27 },
  12: { phaseIndex: 0, illumination: 1, lunarDay: 28 },
  13: { phaseIndex: 1, illumination: 6, lunarDay: 29 },
  14: { phaseIndex: 1, illumination: 14, lunarDay: 1 },
  15: { phaseIndex: 1, illumination: 23, lunarDay: 2 },
  16: { phaseIndex: 1, illumination: 34, lunarDay: 3 },
  17: { phaseIndex: 2, illumination: 49, lunarDay: 4 },
  18: { phaseIndex: 3, illumination: 61, lunarDay: 5 },
  19: { phaseIndex: 3, illumination: 72, lunarDay: 6 },
  20: { phaseIndex: 3, illumination: 83, lunarDay: 7 },
  21: { phaseIndex: 3, illumination: 91, lunarDay: 8 },
  22: { phaseIndex: 4, illumination: 98, lunarDay: 9 },
  23: { phaseIndex: 4, illumination: 100, lunarDay: 10 },
  24: { phaseIndex: 5, illumination: 94, lunarDay: 11 },
  25: { phaseIndex: 5, illumination: 86, lunarDay: 12 },
  26: { phaseIndex: 5, illumination: 76, lunarDay: 13 },
  27: { phaseIndex: 5, illumination: 64, lunarDay: 14 },
  28: { phaseIndex: 6, illumination: 52, lunarDay: 15 },
  29: { phaseIndex: 6, illumination: 39, lunarDay: 16 },
  30: { phaseIndex: 7, illumination: 27, lunarDay: 17 },
  31: { phaseIndex: 7, illumination: 16, lunarDay: 18 },
};

function lunarFor(date: string): CalendarLunarFields {
  const day = Number(date.slice(8, 10));
  const month = Number(date.slice(5, 7));
  const source = month === 7
    ? julyLunar[day]
    : { phaseIndex: (day + month) % 8, illumination: 20 + ((day * 7) % 70), lunarDay: ((day + 15) % 29) + 1 };
  const sign = SIGNS[(day + month) % SIGNS.length];

  return {
    phase: PHASE_KEYS[source.phaseIndex],
    phaseIndex: source.phaseIndex,
    phaseLabel: PHASE_LABELS[source.phaseIndex],
    illumination: source.illumination,
    moonSign: sign[0],
    moonSignLabel: sign[1],
    lunarDay: source.lunarDay,
    voidOfCourse: date === "2026-07-12",
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
    generatedAt: "2026-07-05T06:00:00Z",
  },
  month: "2026-07",
  title: "July 2026",
  allowedRange: {
    from: "2025-07-05",
    to: "2027-07-05",
  },
  days: [
    day("2026-06-29", false),
    day("2026-06-30", false),
    ...Array.from({ length: 31 }, (_, index) => {
      const dayNumber = String(index + 1).padStart(2, "0");
      return day(`2026-07-${dayNumber}`, true, dayNumber === "05");
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
