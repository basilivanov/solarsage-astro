/**
 * API-фасад для «меты» профиля.
 */

import type { ProfileMeta } from "@/lib/profile-meta"

export async function getProfileMeta(): Promise<ProfileMeta> {
  let quotaRemaining = 0
  let nextInDays = 7
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
      quotaRemaining = quota.left || 0
      nextInDays = quota.next_in_days || 7
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
      left: quotaRemaining,
      nextInDays,
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
