/**
 * API-фасад для «меты» профиля.
 */

import type { ProfileMeta } from "@/lib/profile-meta"

export async function getProfileMeta(): Promise<ProfileMeta> {
  let quotaRemaining = 0
  let resetAt = ""
  let referralCount = 0
  let referralUrl = ""

  try {
    const [quotaRes, referralRes] = await Promise.all([
      fetch("/api/chat/quota", {
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
      quotaRemaining = quota.remaining || 0
      resetAt = quota.resetAt || ""
    }

    if (referralRes.ok) {
      const referral = await referralRes.json()
      referralCount = referral.totalInvited || 0
      referralUrl = referral.inviteUrl || ""
    }
  } catch {
    // fallback to defaults
  }

  let nextInDays = 7
  if (resetAt) {
    const ms = new Date(resetAt).getTime() - Date.now()
    nextInDays = Math.max(1, Math.ceil(ms / 86400000))
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
