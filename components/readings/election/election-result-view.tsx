// ############################################################################
// AI_HEADER: MODULE_ELECTION_RESULT_VIEW
// ROLE: Display election search results (Hero, Best days, Avoid days, Window Calendar)
// ############################################################################

// START_MODULE_CONTRACT: M-ELECTION-RESULT-VIEW
// purpose: Render election search results including hero recommendation, best days, days to avoid, and window calendar.
// owns:
//   - components/readings/election/election-result-view.tsx
// inputs: result (ElectionResult), onReset
// outputs: ElectionResultView React component
// dependencies: lib/contracts/election
// side_effects: none (pure rendering)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-ELECTION-RESULT-VIEW

// START_MODULE_MAP: M-ELECTION-RESULT-VIEW
// public_entrypoints:
//   - ElectionResultView
// semantic_blocks:
//   - ELECTION_RESULT_VIEW_COMPONENT: main election search result view component
// owned_tests:
//   - __tests__/readings/election-result-view.test.tsx
// END_MODULE_MAP: M-ELECTION-RESULT-VIEW

"use client"

import { useState } from "react"
import { CheckCircle2, XCircle, ArrowLeft, ChevronDown, ChevronUp, Sparkles, Clock, Calendar as CalendarIcon } from "lucide-react"
import { type ElectionResult, type ElectionDayFact } from "@/lib/contracts/election"

type Props = {
  result: ElectionResult
  onReset?: () => void
}

const RU_WEEKDAYS = ["вс", "пн", "вт", "ср", "чт", "пт", "сб"]
const RU_MONTHS = [
  "января", "февраля", "марта", "апреля", "мая", "июня",
  "июля", "августа", "сентября", "октября", "ноября", "декабря"
]

function formatDateFullRu(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    const dayName = RU_WEEKDAYS[d.getDay()]
    const dayNum = d.getDate()
    const monthName = RU_MONTHS[d.getMonth()]
    return `${dayName}, ${dayNum} ${monthName}`
  } catch {
    return dateStr
  }
}

// START_BLOCK: ELECTION_RESULT_VIEW_COMPONENT
export function ElectionResultView({ result, onReset }: Props) {
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [selectedCalDate, setSelectedCalDate] = useState<string | null>(null)

  const bestDays = result.best_days || []
  const avoidDays = result.avoid_days || []
  const allDays = result.days || []
  const heroDay = bestDays[0] || null
  const narrative = result.narrative

  // Map day notes by date
  const dayNotesMap = new Map<string, string>()
  if (narrative?.day_notes) {
    for (const item of narrative.day_notes) {
      dayNotesMap.set(item.date, item.note)
    }
  }
  const avoidNotesMap = new Map<string, string>()
  if (narrative?.avoid_notes) {
    for (const item of narrative.avoid_notes) {
      avoidNotesMap.set(item.date, item.note)
    }
  }

  // Calendar grid preparation
  const calendarAnchorDate = heroDay ? new Date(heroDay.date) : new Date()
  const year = calendarAnchorDate.getFullYear()
  const month = calendarAnchorDate.getMonth()

  const firstDayOfMonth = new Date(year, month, 1)
  const lastDayOfMonth = new Date(year, month + 1, 0)

  // Monday-based starting day (0=Mon, 6=Sun)
  let startDayOfWeek = firstDayOfMonth.getDay() - 1
  if (startDayOfWeek < 0) startDayOfWeek = 6

  const daysInMonth = lastDayOfMonth.getDate()

  const dayStatusMap = new Map<string, ElectionDayFact>()
  for (const d of allDays) {
    dayStatusMap.set(d.date, d)
  }

  const selectedDayFact = selectedCalDate ? dayStatusMap.get(selectedCalDate) : null
  const selectedDayNote = selectedCalDate
    ? dayNotesMap.get(selectedCalDate) || avoidNotesMap.get(selectedCalDate) || selectedDayFact?.reasons.join(". ")
    : null

  const getLabelBadge = (label: string) => {
    switch (label) {
      case "great":
        return <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-[12px] font-semibold text-emerald-500">Отличный день</span>
      case "good":
        return <span className="rounded-full bg-blue-500/10 px-3 py-1 text-[12px] font-semibold text-blue-500">Хороший день</span>
      case "ok":
        return <span className="rounded-full bg-amber-500/10 px-3 py-1 text-[12px] font-semibold text-amber-500">Нейтрально</span>
      default:
        return <span className="rounded-full bg-destructive/10 px-3 py-1 text-[12px] font-semibold text-destructive">Не рекомендуется</span>
    }
  }

  return (
    <div className="flex flex-col gap-6" data-testid="election-result-view">
      <div className="flex items-center justify-between">
        <span className="text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
          Результат подбора
        </span>
        {onReset && (
          <button
            type="button"
            onClick={onReset}
            className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-card px-3.5 py-1.5 text-[12.5px] font-medium text-foreground transition active:scale-95"
            data-testid="election-reset-btn"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Новый подбор
          </button>
        )}
      </div>

      {/* Hero Day Card */}
      {heroDay && (
        <div
          className="rounded-2xl border border-primary/30 bg-card p-6 flex flex-col gap-4 shadow-sm relative overflow-hidden"
          data-testid="election-hero"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-[12px] font-medium text-primary uppercase tracking-wider mb-1">
                Главная рекомендация
              </div>
              <h2 className="font-serif text-[26px] font-bold text-foreground">
                {formatDateFullRu(heroDay.date)}
              </h2>
            </div>
            {getLabelBadge(heroDay.label)}
          </div>

          {narrative?.hero_reason && (
            <p className="text-[14.5px] leading-relaxed text-foreground/90 font-medium">
              {narrative.hero_reason}
            </p>
          )}

          {/* Moon Info Bar */}
          <div className="flex items-center gap-2 text-[12.5px] text-muted-foreground bg-secondary/50 rounded-xl p-3">
            <Sparkles className="h-4 w-4 text-primary flex-none" />
            <span>
              {heroDay.waxing ? "Растущая Луна" : "Убывающая Луна"}
              {heroDay.phase_pct != null && `, ${heroDay.phase_pct}%`}
              {heroDay.moon_sign_ru && ` · знак: ${heroDay.moon_sign_ru}`}
            </span>
          </div>

          {/* Best Hours Gold Box */}
          {narrative?.hero_hours && (
            <div className="flex items-start gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/5 p-3.5 text-[13px] text-amber-600 dark:text-amber-400">
              <Clock className="h-4 w-4 flex-none mt-0.5" />
              <span>{narrative.hero_hours}</span>
            </div>
          )}

          {/* Expandable Why This Day? Section */}
          <div className="border-t border-border/60 pt-3">
            <button
              type="button"
              onClick={() => setDetailsOpen(!detailsOpen)}
              className="flex w-full items-center justify-between py-1 text-[13px] font-medium text-primary hover:underline"
            >
              <span>Почему этот день?</span>
              {detailsOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>

            {detailsOpen && (
              <div className="flex flex-col gap-3 mt-3 text-[13px] text-muted-foreground animate-in fade-in">
                {narrative?.hero_personal && (
                  <div>
                    <strong className="text-foreground block mb-0.5">Астрологически:</strong>
                    {narrative.hero_personal}
                  </div>
                )}
                {narrative?.hero_plain && (
                  <div>
                    <strong className="text-foreground block mb-0.5">Простыми словами:</strong>
                    {narrative.hero_plain}
                  </div>
                )}
                {heroDay.reasons.length > 0 && (
                  <ul className="list-disc pl-5 space-y-1 pt-1 border-t border-border/40 text-[12px]">
                    {heroDay.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Remaining Best Days */}
      {bestDays.length > 1 && (
        <div className="flex flex-col gap-3">
          <h3 className="text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
            Ещё хорошие дни
          </h3>
          {bestDays.slice(1).map((day) => {
            const note = dayNotesMap.get(day.date)
            return (
              <div
                key={day.date}
                className="rounded-2xl border border-border/70 bg-card p-4 flex flex-col gap-2 shadow-sm"
                data-testid={`election-best-day-${day.date}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-emerald-500 flex-none" />
                    <span className="font-semibold text-[15px] text-foreground">
                      {formatDateFullRu(day.date)}
                    </span>
                  </div>
                  {getLabelBadge(day.label)}
                </div>
                {note ? (
                  <p className="text-[13px] text-foreground/80 mt-1 pl-7">{note}</p>
                ) : (
                  <ul className="flex flex-col gap-1 mt-1 pl-7 text-[12.5px] text-muted-foreground list-disc">
                    {day.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Avoid Days */}
      {avoidDays.length > 0 && (
        <div className="flex flex-col gap-3 mt-2">
          <h3 className="text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
            Лучше не начинать
          </h3>
          {avoidDays.map((day) => {
            const note = avoidNotesMap.get(day.date)
            return (
              <div
                key={day.date}
                className="rounded-2xl border border-destructive/20 bg-destructive/[0.02] p-4 flex flex-col gap-2"
                data-testid={`election-avoid-day-${day.date}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <XCircle className="h-5 w-5 text-destructive flex-none" />
                    <span className="font-semibold text-[15px] text-foreground">
                      {formatDateFullRu(day.date)}
                    </span>
                  </div>
                  {getLabelBadge(day.label)}
                </div>
                {note ? (
                  <p className="text-[13px] text-foreground/80 mt-1 pl-7">{note}</p>
                ) : (
                  <ul className="flex flex-col gap-1 mt-1 pl-7 text-[12.5px] text-muted-foreground list-disc">
                    {day.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Month Calendar Grid */}
      {allDays.length > 0 && (
        <div
          className="rounded-2xl border border-border/70 bg-card p-5 flex flex-col gap-4 shadow-sm mt-2"
          data-testid="election-calendar"
        >
          <div className="flex items-center gap-2 text-foreground font-serif text-[16px] font-semibold">
            <CalendarIcon className="h-4 w-4 text-primary" />
            Календарь окна подбора
          </div>

          <div className="grid grid-cols-7 gap-1 text-center text-[11px] font-medium text-muted-foreground mb-1">
            <span>пн</span><span>вт</span><span>ср</span><span>чт</span><span>пт</span><span>сб</span><span>вс</span>
          </div>

          <div className="grid grid-cols-7 gap-1.5 text-center">
            {/* Empty padding cells */}
            {Array.from({ length: startDayOfWeek }).map((_, i) => (
              <div key={`empty-${i}`} className="h-9 w-full" />
            ))}

            {/* Month days */}
            {Array.from({ length: daysInMonth }).map((_, i) => {
              const dNum = i + 1
              const monthStr = String(month + 1).padStart(2, "0")
              const dayStr = String(dNum).padStart(2, "0")
              const fullDateStr = `${year}-${monthStr}-${dayStr}`

              const fact = dayStatusMap.get(fullDateStr)
              const isSelected = selectedCalDate === fullDateStr
              const isToday = fullDateStr === new Date().toISOString().split("T")[0]

              let bgStyle = "bg-background text-foreground/60 border-border/40"
              if (fact?.label === "great") {
                bgStyle = "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 font-semibold"
              } else if (fact?.label === "good") {
                bgStyle = "bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30 font-semibold"
              } else if (fact?.label === "avoid") {
                bgStyle = "bg-destructive/15 text-destructive border-destructive/30"
              }

              return (
                <button
                  key={fullDateStr}
                  type="button"
                  onClick={() => fact && setSelectedCalDate(fullDateStr)}
                  disabled={!fact}
                  data-testid={`election-calendar-day-${fullDateStr}`}
                  className={`h-9 w-full rounded-xl border flex items-center justify-center text-[13px] transition ${bgStyle} ${
                    isSelected ? "ring-2 ring-primary ring-offset-1" : ""
                  } ${isToday ? "ring-1 ring-foreground" : ""}`}
                >
                  {dNum}
                </button>
              )
            })}
          </div>

          {/* Selected day explanation under calendar */}
          {selectedCalDate && selectedDayNote && (
            <div className="rounded-xl bg-secondary/60 p-3.5 text-[13px] text-foreground animate-in fade-in mt-1">
              <div className="font-semibold mb-1">{formatDateFullRu(selectedCalDate)}:</div>
              <p className="text-muted-foreground">{selectedDayNote}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
// END_BLOCK: ELECTION_RESULT_VIEW_COMPONENT
