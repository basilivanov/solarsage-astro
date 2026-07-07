// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_FIXTURE_HORARY
// ROLE: Contract-valid API fixtures for mock visual horary e2e tests.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-FIXTURE-HORARY
// purpose: Provide contract-valid fixture payloads for horary mock visual e2e.
// owns:
//   - e2e/mock-visual/fixtures/horary.ts
// inputs: none (static fixtures)
// outputs: Named exports: horaryQuotaPayload, horaryQuestionsPayload, profilePayload
// dependencies: none (pure data)
// side_effects: none
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-FIXTURE-HORARY

import type { components } from "../../../packages/contracts/_generated";

export const horaryQuotaPayload: components["schemas"]["HoraryQuotaRead"] = {
  weeklyFreeAvailable: true,
  weeklyFreeExpiresAt: "2026-07-09T00:00:00Z",
  nextWeeklyFreeAt: null,
  bonusCredits: 2,
  paidCredits: 3,
  canPurchase: false,
};

export const horaryQuestionsPayload: components["schemas"]["HoraryQuestionRead"][] = [];

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
