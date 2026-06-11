
// ############################################################################
// AI_HEADER: MODULE_API_PROFILE_META
// ROLE: UI — profile-meta
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ####// START_MODULE_CONTRACT
// purpose: API client for profile-meta
// owns:
//   - lib/api/profile-meta.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: Network calls to API
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT/**
 * API-фасад для «меты» профиля.
 */

import type { ProfileMeta } from "@/lib/profile-meta"

export async function getProfileMeta(): Promise<ProfileMeta> {
  let weeklyFreeAvailable = false
  let weeklyFreeExpiresAt: string | null = null
  let nextWeeklyFreeAt: string | null = null
  let bonusCredits = 0
  let paidCredits = 0
  let canPurchase = true

  let referralCount = 0
  let referralUrl = ""

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
      canPurchase = quota.canPurchase !== undefined ? quota.canPurchase : true
    }

    if (referralRes.ok) {
      const referral = await referralRes.json()
      referralCount = referral.totalInvited || 0
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
      bonusDays: referralCount * 14,
      inviteUrl: referralUrl,
      rewardDays: 14,
    },
  }
}

export const getProfileMetaAsync = getProfileMeta
