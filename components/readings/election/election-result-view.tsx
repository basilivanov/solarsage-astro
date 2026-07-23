// ############################################################################
// AI_HEADER: MODULE_ELECTION_RESULT_VIEW
// ROLE: Display election search results (best & avoid days)
// ############################################################################

"use client"

import { CheckCircle2, XCircle, ArrowLeft } from "lucide-react"
import { ELECTION_EVENTS, type ElectionResult } from "@/lib/contracts/election"

type Props = {
  result: ElectionResult
  onReset?: () => void
}

const RU_DAYS = ["вс", "пн", "вт", "ср", "чт", "пт", "сб"]
const RU_MONTHS = [
  "янв", "фев", "мар", "апр", "май", "июн",
  "июл", "авг", "сен", "окт", "ноя", "дек"
]

function formatDateRu(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    const dayName = RU_DAYS[d.getDay()]
    const dayNum = d.getDate()
    const monthName = RU_MONTHS[d.getMonth()]
    return `${dayName}, ${dayNum} ${monthName}`
  } catch {
    return dateStr
  }
}

export function ElectionResultView({ result, onReset }: Props) {
  const eventInfo = ELECTION_EVENTS.find((e) => e.key === result.event)
  const eventLabel = eventInfo ? `${eventInfo.emoji} ${eventInfo.label}` : result.event

  const getLabelBadge = (label: string) => {
    switch (label) {
      case "great":
        return <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-medium text-emerald-500">Отличный день</span>
      case "good":
        return <span className="rounded-full bg-blue-500/10 px-2.5 py-0.5 text-[11px] font-medium text-blue-500">Хороший день</span>
      case "ok":
        return <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-[11px] font-medium text-amber-500">Нейтрально</span>
      default:
        return <span className="rounded-full bg-destructive/10 px-2.5 py-0.5 text-[11px] font-medium text-destructive">Не рекомендуется</span>
    }
  }

  return (
    <div className="flex flex-col gap-6" data-testid="election-result-view">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-[20px] font-semibold text-foreground">
          {eventLabel}
        </h2>
        {onReset && (
          <button
            type="button"
            onClick={onReset}
            className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-card px-3 py-1.5 text-[12px] font-medium text-foreground transition active:scale-95"
            data-testid="election-reset-btn"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Новый подбор
          </button>
        )}
      </div>

      {/* Top Best Days */}
      <div className="flex flex-col gap-3">
        <h3 className="text-[13px] font-medium uppercase tracking-wider text-muted-foreground">
          Лучшие даты
        </h3>
        {result.best_days.length === 0 ? (
          <p className="text-[13px] text-muted-foreground">Подходящих дат в выбранном окне не найдено</p>
        ) : (
          result.best_days.map((day) => (
            <div
              key={day.date}
              className="rounded-2xl border border-border/70 bg-card p-4 flex flex-col gap-2 shadow-sm"
              data-testid={`election-best-day-${day.date}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-emerald-500 flex-none" />
                  <span className="font-semibold text-[15px] text-foreground">
                    {formatDateRu(day.date)}
                  </span>
                </div>
                {getLabelBadge(day.label)}
              </div>
              <ul className="flex flex-col gap-1 mt-1 pl-7 text-[13px] text-muted-foreground list-disc">
                {day.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          ))
        )}
      </div>

      {/* Avoid Days */}
      {result.avoid_days.length > 0 && (
        <div className="flex flex-col gap-3 mt-2">
          <h3 className="text-[13px] font-medium uppercase tracking-wider text-muted-foreground">
            Лучше не начинать
          </h3>
          {result.avoid_days.map((day) => (
            <div
              key={day.date}
              className="rounded-2xl border border-destructive/20 bg-destructive/[0.02] p-4 flex flex-col gap-2"
              data-testid={`election-avoid-day-${day.date}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <XCircle className="h-5 w-5 text-destructive flex-none" />
                  <span className="font-semibold text-[15px] text-foreground">
                    {formatDateRu(day.date)}
                  </span>
                </div>
                {getLabelBadge(day.label)}
              </div>
              <ul className="flex flex-col gap-1 mt-1 pl-7 text-[13px] text-muted-foreground list-disc">
                {day.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
