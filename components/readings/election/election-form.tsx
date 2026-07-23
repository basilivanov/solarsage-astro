// ############################################################################
// AI_HEADER: MODULE_ELECTION_FORM
// ROLE: Form component for creating an election date search
// ############################################################################

"use client"

import { useState } from "react"
import { Sparkles } from "lucide-react"
import { ELECTION_EVENTS, type ElectionEventKey } from "@/lib/contracts/election"

type Props = {
  onSubmit: (params: {
    eventType: ElectionEventKey
    windowFrom: string
    windowTo: string
  }) => void
  disabled?: boolean
  disabledReason?: string
}

function formatDateISO(d: Date): string {
  return d.toISOString().split("T")[0]
}

export function ElectionForm({ onSubmit, disabled = false, disabledReason }: Props) {
  const [selectedEvent, setSelectedEvent] = useState<ElectionEventKey | null>(null)
  const [preset, setPreset] = useState<"7d" | "14d" | "30d" | "custom">("14d")

  const today = new Date()
  const todayStr = formatDateISO(today)
  const defaultTo14 = formatDateISO(new Date(today.getTime() + 14 * 86400000))

  const [windowFrom, setWindowFrom] = useState(todayStr)
  const [windowTo, setWindowTo] = useState(defaultTo14)
  const [dateError, setDateError] = useState<string | null>(null)

  const handlePresetChange = (p: "7d" | "14d" | "30d" | "custom") => {
    setPreset(p)
    setDateError(null)
    const now = new Date()
    const fromStr = formatDateISO(now)
    setWindowFrom(fromStr)

    if (p === "7d") {
      setWindowTo(formatDateISO(new Date(now.getTime() + 7 * 86400000)))
    } else if (p === "14d") {
      setWindowTo(formatDateISO(new Date(now.getTime() + 14 * 86400000)))
    } else if (p === "30d") {
      setWindowTo(formatDateISO(new Date(now.getTime() + 30 * 86400000)))
    }
  }

  const validateDates = (from: string, to: string): boolean => {
    if (!from || !to) {
      setDateError("Укажите обе даты")
      return false
    }
    const dFrom = new Date(from)
    const dTo = new Date(to)
    if (dTo < dFrom) {
      setDateError("Дата окончания должна быть не раньше даты начала")
      return false
    }
    const diffDays = Math.round((dTo.getTime() - dFrom.getTime()) / 86400000)
    if (diffDays > 62) {
      setDateError("Максимальный интервал подбора — 62 дня")
      return false
    }
    setDateError(null)
    return true
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedEvent) return
    if (!validateDates(windowFrom, windowTo)) return
    onSubmit({
      eventType: selectedEvent,
      windowFrom,
      windowTo,
    })
  }

  const canSubmit = selectedEvent && !disabled && !dateError

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-6 rounded-2xl border border-border/70 bg-card p-6 shadow-sm"
      data-testid="election-form"
    >
      {/* Event type selection chips */}
      <div className="flex flex-col gap-3">
        <label className="text-[13px] font-medium uppercase tracking-wider text-muted-foreground">
          1. Выбери событие
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2" data-testid="election-events-grid">
          {ELECTION_EVENTS.map((event) => {
            const isSelected = selectedEvent === event.key
            return (
              <button
                key={event.key}
                type="button"
                onClick={() => setSelectedEvent(event.key)}
                data-testid={`election-event-chip-${event.key}`}
                data-state={isSelected ? "selected" : "unselected"}
                className={`flex items-center gap-2 rounded-xl border p-3 text-left transition text-[13px] font-medium active:scale-[0.98] ${
                  isSelected
                    ? "border-primary bg-primary/10 text-primary shadow-sm"
                    : "border-border/70 bg-card text-foreground hover:border-border"
                }`}
              >
                <span className="text-[16px]">{event.emoji}</span>
                <span className="truncate">{event.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Date window presets & custom inputs */}
      <div className="flex flex-col gap-3">
        <label className="text-[13px] font-medium uppercase tracking-wider text-muted-foreground">
          2. Интервал подбора
        </label>

        <div className="flex gap-2">
          {[
            { id: "7d", label: "Неделя" },
            { id: "14d", label: "2 недели" },
            { id: "30d", label: "Месяц" },
            { id: "custom", label: "Свои даты" },
          ].map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => handlePresetChange(p.id as any)}
              data-testid={`election-preset-${p.id}`}
              className={`flex-1 rounded-lg border py-2 text-[12.5px] font-medium transition active:scale-[0.98] ${
                preset === p.id
                  ? "border-primary bg-primary/10 text-primary font-semibold"
                  : "border-border/70 bg-card text-muted-foreground hover:text-foreground"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {preset === "custom" && (
          <div className="grid grid-cols-2 gap-3 mt-1" data-testid="election-custom-dates">
            <div>
              <label className="block text-[11px] text-muted-foreground mb-1">С даты</label>
              <input
                type="date"
                value={windowFrom}
                onChange={(e) => {
                  setWindowFrom(e.target.value)
                  validateDates(e.target.value, windowTo)
                }}
                className="w-full rounded-xl border border-border/70 bg-background px-3 py-2 text-[13px] text-foreground focus:border-primary focus:outline-none"
                data-testid="election-date-from"
              />
            </div>
            <div>
              <label className="block text-[11px] text-muted-foreground mb-1">По дату</label>
              <input
                type="date"
                value={windowTo}
                onChange={(e) => {
                  setWindowTo(e.target.value)
                  validateDates(windowFrom, e.target.value)
                }}
                className="w-full rounded-xl border border-border/70 bg-background px-3 py-2 text-[13px] text-foreground focus:border-primary focus:outline-none"
                data-testid="election-date-to"
              />
            </div>
          </div>
        )}

        {dateError && (
          <p className="text-[12px] text-destructive mt-1" role="alert" data-testid="election-date-error">
            {dateError}
          </p>
        )}
      </div>

      {disabledReason && (
        <p className="text-[12.5px] text-destructive text-center" role="alert">
          {disabledReason}
        </p>
      )}

      {/* Submit CTA */}
      <button
        type="submit"
        disabled={!canSubmit}
        aria-disabled={!canSubmit}
        data-testid="election-submit-btn"
        className="inline-flex h-12 items-center justify-center gap-2 rounded-full bg-primary px-6 text-[14px] font-semibold text-primary-foreground transition active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Sparkles className="h-4 w-4" />
         Подобрать лучшие даты
      </button>
    </form>
  )
}
