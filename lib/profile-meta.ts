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
