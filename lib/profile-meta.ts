
// ############################################################################
// AI_HEADER: MODULE_LIB_PROFILE_META
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/profile-meta.ts
// owns:
//   - lib/profile-meta.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

/**
 * Контракт «мета»-данных профиля: всё, что НЕ хранится локально и
 * приедет с бэкенда (баланс хорарных вопросов, реферальная программа,
 * биллинговые подсказки и т.д.).
 *
 * Здесь только типы — без данных и без сетевых вызовов. Моки лежат в
 * `lib/mocks/profile-meta.ts`, а единая точка входа для UI —
 * `lib/api/profile-meta.ts` (`getProfileMeta`).
 *
 * Когда подключим бэк, эти же типы станут схемой ответа `/api/profile/meta`.
 */

export type HoraryMeta = {
  weeklyFreeAvailable: boolean
  weeklyFreeExpiresAt?: string | null
  nextWeeklyFreeAt?: string | null
  bonusCredits: number
  paidCredits: number
  canPurchase: boolean
}

export type ReferralMeta = {
  count: number
  bonusDays: number
  rewardDays: number
  inviteUrl: string
}

export type ProfileMeta = {
  horary: HoraryMeta
  referral: ReferralMeta
}
