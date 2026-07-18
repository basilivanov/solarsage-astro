// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_SHARE_INVITE
// ROLE: UI — use-share-invite
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Share invite hook — builds the default referral share text/link.
// owns:
//   - lib/hooks/use-share-invite.ts
// inputs: none (fetches /api/referral for the user invite URL)
// outputs: share() callback opening the Telegram share URL
// dependencies: /api/referral inviteUrl, Telegram WebApp initDataUnsafe/openTelegramLink/openLink
// side_effects: one GET /api/referral on mount; opens share UI on demand
// emitted_logs: n/a
// invariants:
//   - Default share text is the accepted variant-1 copy plus the honest
//     motivator "мы оба получим по 14 дней полного доступа" (referral.py
//     grants 14 days to BOTH users).
//   - The bonus motivator is shared ONLY together with an attributed invite
//     URL (API inviteUrl or the canonical startapp fallback built from
//     Telegram initDataUnsafe user.id, both t.me/vi_astro_bot/app?startapp={id}
//     — the frontend auto-claim reads start_param).
//   - Without any user id, the shared link degrades to generic
//     https://t.me/vi_astro_bot/app and the text to SHARE_TEXT_GENERIC
//     WITHOUT the bonus promise (an unattributed link cannot grant a bonus).
//   - Tone: расчёт по натальной карте, на ты, без эзотерического пафоса;
//     слово «гороскоп» только с отрицанием (здесь — не используется).
// failure_policy: on referral fetch failure, fall back to the canonical
//   startapp URL from initDataUnsafe; without a user id, share the generic
//   app link with the promise-free generic text.
// END_MODULE_CONTRACT
"use client"

import { useCallback, useEffect, useState } from "react"

export const SHARE_TEXT = "Слушай, жутко точно: тут считают день по моей натальной карте — сфера за сферой всё про меня. Глянь свой, это 30 секунд:\n\nПо моей ссылке мы оба получим по 14 дней полного доступа."
export const SHARE_TEXT_GENERIC = "Слушай, жутко точно: тут считают день по моей натальной карте — сфера за сферой всё про меня. Глянь свой, это 30 секунд:"
const APP_URL = "https://t.me/vi_astro_bot/app"

// START_BLOCK: FALLBACK_URL
// Canonical attributed fallback: same inviteUrl form the API returns,
// built from the Telegram initDataUnsafe user id. Returns null when no
// id is available — then the caller must not promise a referral bonus.
export function buildFallbackInviteUrl(): string | null {
  try {
    const id = window?.Telegram?.WebApp?.initDataUnsafe?.user?.id
    return typeof id === "number" && Number.isFinite(id) && id > 0
      ? `${APP_URL}?startapp=${id}`
      : null
  } catch {
    return null
  }
}
// END_BLOCK: FALLBACK_URL

export function useShareInvite() {
  const [inviteUrl, setInviteUrl] = useState<string | null>(null)

  useEffect(() => {
    fetch("/api/referral", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => setInviteUrl(d.inviteUrl || null))
      .catch(() => setInviteUrl(null))
  }, [])

  const share = useCallback(() => {
    const attributedUrl = inviteUrl ?? buildFallbackInviteUrl()
    const url = attributedUrl ?? APP_URL
    // Honest text selection: the 14-days-both promise is only made when the
    // link actually carries referral attribution (startapp={tg_user_id}).
    const shareText = attributedUrl ? SHARE_TEXT : SHARE_TEXT_GENERIC
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(shareText)}`

    try {
      const tg = window?.Telegram?.WebApp
      if (tg?.openTelegramLink) {
        tg.openTelegramLink(shareUrl)
      } else if (tg?.openLink) {
        tg.openLink(shareUrl)
      } else if (navigator.share) {
        navigator.share({ title: "Разбор дня по натальной карте", text: shareText, url })
      } else {
        window.open(shareUrl, "_blank")
      }
    } catch {
      window.open(shareUrl, "_blank")
    }
  }, [inviteUrl])

  return share
}
