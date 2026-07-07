"use client"

import { useMemo } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { ArrowLeft } from "lucide-react"

import { CheckinScreen } from "@/components/checkin/checkin-screen"
import { useProfile } from "@/hooks/use-profile"
import { resolveCheckinTargetDate } from "@/lib/api/checkin"

export default function CheckinPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { profile } = useProfile()
  const timeZone =
    profile.currentLocation?.timezone || profile.birthLocation?.timezone || null
  const target = searchParams.get("target") || searchParams.get("date")
  const targetDate = useMemo(
    () => resolveCheckinTargetDate(new Date(), timeZone, target),
    [timeZone, target],
  )

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-md">
        <div className="flex items-center gap-3 px-5 pt-6">
          <button
            type="button"
            aria-label="Назад"
            onClick={() => router.back()}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-border/70 text-foreground"
          >
            <ArrowLeft className="h-4 w-4" strokeWidth={1.75} />
          </button>
          <h1 className="font-serif text-[20px] leading-tight text-foreground">
            Оценка дня
          </h1>
        </div>
        <CheckinScreen
          targetDate={targetDate}
          onComplete={() => router.push(`/day/${targetDate}`)}
        />
      </div>
    </main>
  )
}
