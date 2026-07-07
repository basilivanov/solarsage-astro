// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_FIXTURE_PROFILE
// ROLE: Contract-valid API fixtures for mock visual e2e profile tests.
//       Matches backend shapes: ProfileRead, AccessSummary, HoraryQuotaRead,
//       referral, CheckinMetrics.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-FIXTURE-PROFILE
// purpose: Provide contract-valid fixture payloads for profile mock visual e2e.
// owns:
//   - e2e/mock-visual/fixtures/profile.ts
// inputs: none (static fixtures)
// outputs: Named exports: profilePayload, accessPayload, horaryQuotaPayload,
//          referralPayload, checkinMetricsPayload
// dependencies: none (pure data)
// side_effects: none
// invariants: Shapes match _generated.ts contract types
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-FIXTURE-PROFILE

// START_MODULE_MAP: M-E2E-MOCK-VISUAL-FIXTURE-PROFILE
// public_entrypoints:
//   - profilePayload
//   - accessPayload
//   - horaryQuotaPayload
//   - referralPayload
//   - checkinMetricsPayload
// owned_tests:
//   - e2e/mock-visual/profile.spec.ts
// END_MODULE_MAP: M-E2E-MOCK-VISUAL-FIXTURE-PROFILE

import type { components } from "../../../packages/contracts/_generated";

export const profilePayload: components["schemas"]["ProfileRead"] = {
  userId: "11111111-1111-4111-8111-111111111111",
  firstName: "Ada",
  gender: "female",
  isOnboarded: true,
  birth: {
    birthday: "1985-12-10",
    birthTime: "12:05:00",
    birthCity: "Lisbon, Portugal",
    birthLat: 38.7223,
    birthLon: -9.1393,
    birthTz: "Europe/Lisbon",
  },
  currentLocation: {
    city: "Lisbon, Portugal",
    lat: 38.7223,
    lon: -9.1393,
    tz: "Europe/Lisbon",
  },
  birthdayLocation: {
    city: "Tokyo, Japan",
    lat: 35.6762,
    lon: 139.6503,
    tz: "Asia/Tokyo",
  },
};

export const accessPayload: components["schemas"]["AccessSummary"] = {
  user: "trial",
  referralDaysLeft: 14,
  subscriptionActive: false,
  accessStart: "2026-07-01",
  accessUntil: "2026-07-21",
};

export const horaryQuotaPayload: components["schemas"]["HoraryQuotaRead"] = {
  weeklyFreeAvailable: true,
  weeklyFreeExpiresAt: "2026-07-09T00:00:00Z",
  nextWeeklyFreeAt: null,
  bonusCredits: 2,
  paidCredits: 3,
  canPurchase: false,
};

export const referralPayload = {
  inviteCode: "3333",
  inviteUrl: "https://t.me/vi_astro_bot/app?startapp=3333",
  totalInvited: 1,
  daysPerInvite: 14,
};

export const checkinMetricsPayload: components["schemas"]["CheckinMetrics"] = {
  totalCheckins: 9,
  currentStreak: 3,
  longestStreak: 5,
  averageMood: 4.1,
  averageEnergy: 3.7,
  averageAccuracy: 2.4,
  moodDistribution: { "1": 0, "2": 1, "3": 2, "4": 4, "5": 2 },
  accuracyDistribution: { "1": 1, "2": 3, "3": 5 },
  tagFrequency: { focused: 4, social: 3, calm: 2 },
};
