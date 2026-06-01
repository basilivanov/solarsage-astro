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
  /** Сколько хорарных вопросов доступно прямо сейчас. */
  left: number
  /** Через сколько дней начислится следующий вопрос. */
  nextInDays: number
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
