"use client"

import { useState } from "react"
import { CalendarDays, Moon } from "lucide-react"

import type { CalendarDayReadModel } from "@/lib/contracts/calendar"
import { lunarPhaseGlyph, lunarPhaseLabel } from "@/lib/lunar-presentation"

type Props = {
  days: CalendarDayReadModel[]
}

function hasLunarFacts(day: CalendarDayReadModel): boolean {
  const lunar = day.lunar
  return lunar.phase != null
    || lunar.phaseIndex != null
    || lunar.phaseLabel != null
    || lunar.illumination != null
    || lunar.moonSign != null
    || lunar.moonSignLabel != null
    || lunar.lunarDay != null
    || lunar.voidOfCourse != null
}

export function LunarCalendarStrip({ days }: Props) {
  const lunarDays = days.filter((day) => day.isCurrentMonth && hasLunarFacts(day))
  const currentMonthDays = days.filter((day) => day.isCurrentMonth)
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const selected = selectedDate ? lunarDays.find((day) => day.date === selectedDate) ?? null : null
  const keyEvents = lunarDays.filter((day, index, source) => {
    const phaseIndex = day.lunar.phaseIndex
    if (phaseIndex == null || ![0, 2, 4, 6].includes(phaseIndex)) return false
    return source.findIndex((item) => item.lunar.phaseIndex === phaseIndex) === index
  })

  if (lunarDays.length === 0) {
    return (
      <section className="px-5 pt-4" aria-label="Лунный календарь" data-testid="lunar-calendar-unavailable">
        <div className="rounded-lg border border-border/50 bg-card/70 px-4 py-4 text-center">
          <Moon className="mx-auto h-4 w-4 text-muted-foreground" strokeWidth={1.75} />
          <p className="mt-2 text-sm font-medium text-foreground">Лунные данные недоступны</p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Для этого месяца backend пока не вернул лунные поля.
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="px-5 pt-4" aria-label="Лунный календарь" data-testid="lunar-calendar-strip">
      <div className="rounded-lg border border-border/50 bg-card/75 p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Moon className="h-3.5 w-3.5 text-primary" strokeWidth={1.75} />
            <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Лунный календарь
            </h3>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground/70">
            <CalendarDays className="h-3 w-3" strokeWidth={1.75} />
            <span>{currentMonthDays.length} дней</span>
          </div>
        </div>

        {keyEvents.length > 0 ? (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {keyEvents.map((day) => {
              const label = lunarPhaseLabel(day.lunar) ?? "Луна"
              return (
                <button
                  key={day.date}
                  type="button"
                  onClick={() => setSelectedDate(day.date)}
                  className="inline-flex items-center gap-1 rounded-full border border-primary/20 bg-primary/5 px-2 py-1 text-[10px] font-medium text-primary transition active:scale-95"
                  aria-label={`${label} ${day.dayNumber}`}
                >
                  <span aria-hidden>{lunarPhaseGlyph(day.lunar)}</span>
                  <span>{label}</span>
                  <span className="tabular-nums opacity-70">{day.dayNumber}</span>
                </button>
              )
            })}
          </div>
        ) : null}

        <div className="-mx-1 overflow-x-auto px-1 pb-1">
          <div className="flex min-w-max gap-1.5">
            {lunarDays.map((day) => {
              const lunar = day.lunar
              const isSelected = day.date === selected?.date
              const label = lunarPhaseLabel(lunar) ?? "Луна"
              return (
                <button
                  key={day.date}
                  type="button"
                  onClick={() => setSelectedDate(day.date)}
                  className="flex w-9 flex-col items-center gap-1 rounded-lg px-1 py-1.5 text-center transition active:scale-95"
                  style={{
                    outline: isSelected ? "1px solid var(--primary)" : "none",
                    background: isSelected ? "var(--secondary)" : "transparent",
                  }}
                  aria-label={[
                    day.dayNumber,
                    label,
                    typeof lunar.illumination === "number" ? `${Math.round(lunar.illumination)}%` : null,
                  ].filter(Boolean).join(", ")}
                >
                  <span className="text-[9px] tabular-nums text-muted-foreground">{day.dayNumber}</span>
                  <span className="text-[20px] leading-none" aria-hidden>{lunarPhaseGlyph(lunar)}</span>
                  {typeof lunar.illumination === "number" ? (
                    <span className="text-[8px] tabular-nums leading-none text-muted-foreground">{Math.round(lunar.illumination)}%</span>
                  ) : null}
                </button>
              )
            })}
          </div>
        </div>

        {selected ? (
          <div className="mt-3 rounded-md border border-border/50 bg-background/60 p-3" data-testid="lunar-calendar-selected-detail">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
              <span className="text-[18px] leading-none" aria-hidden>{lunarPhaseGlyph(selected.lunar)}</span>
              {lunarPhaseLabel(selected.lunar) ? (
                <span className="font-medium text-foreground">{lunarPhaseLabel(selected.lunar)}</span>
              ) : null}
              {typeof selected.lunar.illumination === "number" ? (
                <span className="text-muted-foreground">{Math.round(selected.lunar.illumination)}%</span>
              ) : null}
              {typeof selected.lunar.lunarDay === "number" ? (
                <span className="text-muted-foreground">{selected.lunar.lunarDay} лунный день</span>
              ) : null}
              {selected.lunar.moonSignLabel ?? selected.lunar.moonSign ? (
                <span className="text-muted-foreground">{selected.lunar.moonSignLabel ?? selected.lunar.moonSign}</span>
              ) : null}
              {selected.lunar.voidOfCourse === true ? (
                <span className="rounded-full bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400">
                  без курса
                </span>
              ) : null}
            </div>
          </div>
        ) : null}

        <div className="mt-2.5 flex items-center justify-center gap-3 text-[9px] text-muted-foreground/70">
          <span className="inline-flex items-center gap-1"><span aria-hidden>🌑</span> новолуние</span>
          <span className="inline-flex items-center gap-1"><span aria-hidden>🌕</span> полнолуние</span>
          <span className="inline-flex items-center gap-1"><span aria-hidden>🌓</span> четверть</span>
        </div>
      </div>
    </section>
  )
}
