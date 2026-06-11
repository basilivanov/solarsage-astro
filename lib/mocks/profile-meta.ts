
// ############################################################################
// AI_HEADER: MODULE_MOCKS_PROFILE_META
// ROLE: Lib — profile-meta.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: Library: profile-meta
// owns:
//   - lib/mocks/profile-meta.ts
// inputs: Function arguments
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
/**
 * Mock-данные «меты» профиля.
 *
 * Импортируется ТОЛЬКО из `lib/api/profile-meta.ts` — компоненты не должны
 * знать об этом файле. Когда появится бэкенд, удаляем этот модуль и
 * переписываем `lib/api/profile-meta.ts` на fetch + Zod-валидацию.
 */

import type { ProfileMeta } from "@/lib/profile-meta"

const MOCK: ProfileMeta = {
  horary: {
    weeklyFreeAvailable: true,
    weeklyFreeExpiresAt: "2026-06-15T12:00:00Z",
    nextWeeklyFreeAt: "2026-06-22T12:00:00Z",
    bonusCredits: 2,
    paidCredits: 0,
    canPurchase: true,
  },
  referral: {
    count: 0,
    bonusDays: 0,
    rewardDays: 14,
    inviteUrl: "",
  },
}

export function buildMockProfileMeta(): ProfileMeta {
  // Возвращаем копию, чтобы случайная мутация в UI не утекла обратно в мок.
  return {
    horary: { ...MOCK.horary },
    referral: { ...MOCK.referral },
  }
}
