
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_SHARE_INVITE
// ROLE: UI — use-share-invite
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: API client for use-share-invite
// owns:
//   - lib/hooks/use-share-invite.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: Network calls to API; React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { useCallback, useEffect, useState } from "react"

const SHARE_TEXT = "Привет! Попробуй астрологический навигатор — персонализированные разборы дня по твоей натальной карте. 14 дней бесплатно по ссылке:"
const DEFAULT_URL = "https://t.me/vi_astro_bot?start=invite"

export function useShareInvite() {
  const [inviteUrl, setInviteUrl] = useState("")

  useEffect(() => {
    fetch("/api/referral", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => setInviteUrl(d.inviteUrl || DEFAULT_URL))
      .catch(() => setInviteUrl(DEFAULT_URL))
  }, [])

  const share = useCallback(() => {
    const url = inviteUrl || DEFAULT_URL
    const text = encodeURIComponent(SHARE_TEXT)
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${text}`

    try {
      const tg = window?.Telegram?.WebApp
      if (tg?.openTelegramLink) {
        tg.openTelegramLink(shareUrl)
      } else if (tg?.openLink) {
        tg.openLink(shareUrl)
      } else if (navigator.share) {
        navigator.share({ title: "Астрологический навигатор", text: "Попробуй персональный астрологический навигатор дня", url })
      } else {
        window.open(shareUrl, "_blank")
      }
    } catch {
      window.open(shareUrl, "_blank")
    }
  }, [inviteUrl])

  return share
}