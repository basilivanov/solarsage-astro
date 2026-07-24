// ############################################################################
// AI_HEADER: FRONTEND_API_PROFILE_META — fail-soft horary and referral metadata aggregation.
// ROLE: Fail-soft aggregator for horary quota and referral profile metadata.
// DEPENDENCIES: lib/profile-meta type; lib/log/instrumented-fetch; lib/contracts/horary; Promise.all
// GRACE_ANCHORS: [FRONTEND_API_PROFILE_META]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-PROFILE-META
// purpose: Fetch quota and referral concurrently via instrumentedFetch and assemble ProfileMeta defaults or partials.
// owns:
//   - lib/api/profile-meta.ts
// inputs: authenticated browser session.
// outputs: Promise<ProfileMeta> and compatibility alias.
// dependencies: lib/profile-meta type; lib/log/instrumented-fetch; lib/contracts/horary; Promise.all.
// side_effects: parallel credentialed GET /api/horary/quota and /api/referral via instrumentedFetch.
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_request_failed, frontend.api_response_invalid.
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
//   - PARALLEL_FETCH: request quota and referral concurrently via instrumentedFetch.
//   - QUOTA_MAPPING: apply quota fields only when the quota response is ok.
//   - REFERRAL_MAPPING: apply referral fields only when the referral response is ok.
//   - PROFILE_META_ASSEMBLY: return defaults or populated metadata.
//   - COMPATIBILITY_ALIAS: retain the reference-equal Async export.
// owned_tests:
//   - __tests__/api/profile-meta.test.ts
// END_MODULE_MAP: M-FRONTEND-API-PROFILE-META

import type { ProfileMeta } from "@/lib/profile-meta"
import { instrumentedFetch } from "@/lib/log/instrumented-fetch"
import { HoraryQuotaSchema } from "@/lib/contracts/horary"

// START_BLOCK: PARALLEL_FETCH
export async function getProfileMeta(): Promise<ProfileMeta> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-PROFILE-META.getProfileMeta
  // purpose: Concurrently fetch horary quota and referral data using instrumentedFetch, returning populated metadata or partial/default fallbacks on transport failures.
  // inputs: none
  // returns: Promise<ProfileMeta>
  // side_effects: GET /api/horary/quota and GET /api/referral via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-PROFILE-META.getProfileMeta
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
      instrumentedFetch({
        operation: "profile_meta.horary_quota",
        routeTemplate: "GET /api/horary/quota",
        url: "/api/horary/quota",
        init: {
          credentials: "include",
          headers: { "Accept": "application/json" },
        },
        responseContract: {
          contractName: "HoraryQuota",
          contractVersion: "v1",
          validate: (json) => {
            const parsed = HoraryQuotaSchema.safeParse(json)
            if (parsed.success) return { valid: true }
            const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
            return { valid: false, missingFields: fields, invalidFieldTypes: fields }
          },
        },
      }),
      instrumentedFetch({
        operation: "profile_meta.referral",
        routeTemplate: "GET /api/referral",
        url: "/api/referral",
        init: {
          credentials: "include",
          headers: { "Accept": "application/json" },
        },
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
// END_BLOCK: PARALLEL_FETCH

// START_BLOCK: COMPATIBILITY_ALIAS
export const getProfileMetaAsync = getProfileMeta
// END_BLOCK: COMPATIBILITY_ALIAS
