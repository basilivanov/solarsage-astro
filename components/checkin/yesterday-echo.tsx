// ############################################################################
// AI_HEADER: MODULE_CHECKIN_YESTERDAY_ECHO
// ROLE: UI component — yesterday echo block in day screen
// DEPENDENCIES: react
// GRACE_ANCHORS: []
// SLICE: SLICE-CHECKIN
// WAVE: W-8.1
// ############################################################################

"use client"

import { useRouter } from "next/navigation"
import type { YesterdayEcho } from "@/lib/contracts/checkin"

const MOOD_EMOJI: Record<number, string> = { 1: "😫", 2: "😕", 3: "😐", 4: "🙂", 5: "🤩" }
const ACCURACY_EMOJI: Record<string, string> = { miss: "❌", partial: "🤷", hit: "✅" }

type Props = {
  echo: YesterdayEcho | null
}

export function YesterdayEchoBlock({ echo }: Props) {
  const router = useRouter()

  if (!echo || !echo.hadCheckin) {
    // No checkin → show CTA
    return (
      <div
        className="rounded-2xl border border-border/60 bg-card p-4"
        data-testid="yesterday-echo-cta"
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[13px] font-medium text-foreground">
              📊 Вчерашний прогноз без оценки
            </div>
            <div className="text-[12px] text-muted-foreground">
              Оцени за 5 секунд
            </div>
          </div>
          <button
            type="button"
            onClick={() => router.push("/checkin")}
            className="rounded-full bg-foreground px-4 py-2 text-[12px] font-medium text-background"
          >
            Оценить
          </button>
        </div>
      </div>
    )
  }

  // Has checkin → show echo
  const moodEmoji = echo.mood ? MOOD_EMOJI[echo.mood] || "😐" : "📊"
  const accuracyText = echo.accuracy
    ? `Прогноз: ${ACCURACY_EMOJI[echo.accuracy] || ""} ${echo.accuracy === "hit" ? "попал" : echo.accuracy === "partial" ? "частично" : "мимо"}`
    : null

  return (
    <div
      className="rounded-2xl border border-border/60 bg-card p-4"
      data-testid="yesterday-echo-block"
    >
      <div className="flex items-start gap-3">
        <div className="text-2xl">{moodEmoji}</div>
        <div className="flex-1">
          <div className="text-[13px] font-medium text-foreground">
            Вчера ты отметил: {moodEmoji}
          </div>
          {echo.closureText && (
            <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
              {echo.closureText}
            </p>
          )}
          {accuracyText && (
            <div className="mt-2 text-[12px] text-muted-foreground">
              {accuracyText}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
