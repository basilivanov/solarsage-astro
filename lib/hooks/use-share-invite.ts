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