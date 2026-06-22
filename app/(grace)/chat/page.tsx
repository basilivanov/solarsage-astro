"use client"

import { useEffect, useState } from "react"
import { ChatScreen } from "@/components/chat/chat-screen"
import { LockedFeatureCard } from "@/components/locked-feature-card"
import { DEFAULT_PROFILE, type Profile } from "@/lib/profile"
import { getProfile } from "@/lib/api/profile"
import { logger } from "@/lib/log"

/**
 * Chat page — "Спросить" tab.
 *
 * In demo mode we render the full ChatScreen with the default demo profile.
 * In production (no profile / not onboarded) we show the locked placeholder.
 */
export default function ChatPage() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    getProfile()
      .then((p) => {
        if (cancelled) return
        // Coerce the API profile shape into the local Profile contract.
        // The demo profile returns birthday as "YYYY-MM-DD" string; we
        // need the structured {day,month,year} form for ChatScreen.
        const prof: Profile = {
          ...DEFAULT_PROFILE,
          birthDate: parseBirthDate((p as any)?.birthday, DEFAULT_PROFILE.birthDate),
          birthTime: parseBirthTime((p as any)?.birthTime, DEFAULT_PROFILE.birthTime),
          birthPlace: (p as any)?.birthPlace || DEFAULT_PROFILE.birthPlace,
          currentCity: (p as any)?.currentCity || DEFAULT_PROFILE.currentCity,
          birthdayCity: (p as any)?.birthdayCity || DEFAULT_PROFILE.birthdayCity,
        }
        setProfile(prof)
      })
      .catch((e) => {
        logger.warn("[ChatPage] Failed to load profile, using default", { extra: { error: String(e) } })
        if (!cancelled) setProfile(DEFAULT_PROFILE)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  if (!profile) {
    return (
      <LockedFeatureCard
        title="Спросить"
        description="Скоро здесь появится личный астрологический ассистент. Он будет отвечать с учётом твоей натальной карты и текущих транзитов."
        badge="Скоро"
      />
    )
  }

  return <ChatScreen profile={profile} />
}

function parseBirthDate(s: string | undefined, fallback: Profile["birthDate"]): Profile["birthDate"] {
  if (!s) return fallback
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!m) return fallback
  return { year: m[1], month: m[2], day: m[3] }
}

function parseBirthTime(s: string | undefined, fallback: Profile["birthTime"]): Profile["birthTime"] {
  if (!s) return fallback
  const m = s.match(/^(\d{2}):(\d{2})$/)
  if (!m) return fallback
  return { hours: m[1], minutes: m[2], unknown: false }
}
