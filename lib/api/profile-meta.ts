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
