
// ############################################################################
// AI_HEADER: FRONTEND_API_PROFILE_META — fail-soft horary and referral metadata aggregation.
// ROLE: Fail-soft aggregator for horary quota and referral profile metadata.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-PROFILE-META
// purpose: Fetch quota and referral concurrently and assemble ProfileMeta defaults or partials.
// owns:
//   - lib/api/profile-meta.ts
// inputs: authenticated browser session.
// outputs: Promise<ProfileMeta> and compatibility alias.
// dependencies: lib/profile-meta type; Promise.all; fetch.
// side_effects: parallel credentialed GET /api/horary/quota and /api/referral.
// emitted_logs: none.
// invariants:
//   - Network and non-ok responses preserve existing defaults instead of throwing.
//   - When both fetch promises resolve, each response is applied only if its own response.ok is true; a rejected promise sends the whole Promise.all to the catch fallback.
//   - bonusDays remains referralCount multiplied by rewardDays; default rewardDays remains 14.
//   - The Async alias remains reference-equal.
// failure_policy: Catch transport failures silently and return defaults or partials.
// END_MODULE_CONTRACT: M-FRONTEND-API-PROFILE-META

// START_MODULE_MAP: M-FRONTEND-API-PROFILE-META
// public_entrypoints:
//   - getProfileMeta
//   - getProfileMetaAsync
// semantic_blocks:
//   - DEFAULTS: initialize safe horary and referral values.
//   - PARALLEL_FETCH: request quota and referral concurrently.
//   - QUOTA_MAPPING: apply quota fields only when the quota response is ok.
//   - REFERRAL_MAPPING: apply referral fields only when the referral response is ok.
//   - PROFILE_META_ASSEMBLY: return defaults or populated metadata.
//   - COMPATIBILITY_ALIAS: retain the reference-equal Async export.
// owned_tests:
//   - __tests__/api/profile-meta.test.ts
// END_MODULE_MAP: M-FRONTEND-API-PROFILE-META
/**
 * API-фасад для «меты» профиля.
 */

import type { ProfileMeta } from "@/lib/profile-meta"

export async function getProfileMeta(): Promise<ProfileMeta> {
  let weeklyFreeAvailable = false
  let weeklyFreeExpiresAt: string | null = null
  let nextWeeklyFreeAt: string | null = null
  let bonusCredits = 0
  let paidCredits = 0
  let canPurchase = false

  let referralCount = 0
  let referralUrl = ""
  let rewardDays = 14

  try {
    const [quotaRes, referralRes] = await Promise.all([
      fetch("/api/horary/quota", {
        credentials: "include",
        headers: { "Accept": "application/json" },
      }),
      fetch("/api/referral", {
        credentials: "include",
        headers: { "Accept": "application/json" },
      }),
    ])

    if (quotaRes.ok) {
      const quota = await quotaRes.json()
      weeklyFreeAvailable = quota.weeklyFreeAvailable || false
      weeklyFreeExpiresAt = quota.weeklyFreeExpiresAt || null
      nextWeeklyFreeAt = quota.nextWeeklyFreeAt || null
      bonusCredits = quota.bonusCredits || 0
      paidCredits = quota.paidCredits || 0
      canPurchase = quota.canPurchase === true
    }

    if (referralRes.ok) {
      const referral = await referralRes.json()
      referralCount = referral.totalInvited || 0
      if (typeof referral.daysPerInvite === "number") rewardDays = referral.daysPerInvite
      referralUrl = referral.inviteUrl || ""
    }
  } catch {
    // fallback to defaults
  }

  return {
    horary: {
      weeklyFreeAvailable,
      weeklyFreeExpiresAt,
      nextWeeklyFreeAt,
      bonusCredits,
      paidCredits,
      canPurchase,
    },
    referral: {
      count: referralCount,
      bonusDays: referralCount * rewardDays,
      inviteUrl: referralUrl,
      rewardDays,
    },
  }
}

export const getProfileMetaAsync = getProfileMeta
