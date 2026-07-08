"use client"

import { useState } from "react"
import { CalendarDays, Moon } from "lucide-react"

import { PhaseGlyph, phaseColor } from "@/components/calendar/phase-glyph"
import type { CalendarDayReadModel } from "@/lib/contracts/calendar"
import { lunarPhaseLabel } from "@/lib/lunar-presentation"

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
              const color = phaseColor(day.lunar.phaseIndex)
              return (
                <button
                  key={day.date}
                  type="button"
                  onClick={() => setSelectedDate(day.date)}
                  className="inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[10px] font-medium transition active:scale-95"
                  style={{
                    borderColor: `${color}30`,
                    background: `${color}0d`,
                    color,
                  }}
                  aria-label={`${label} ${day.dayNumber}`}
                >
                  <PhaseGlyph phaseIndex={day.lunar.phaseIndex} size={10} />
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
              const color = phaseColor(lunar.phaseIndex)
              const isEvent = [0, 2, 4, 6].includes(lunar.phaseIndex ?? -1)
              return (
                <button
                  key={day.date}
                  type="button"
                  onClick={() => setSelectedDate(day.date)}
                  className="flex w-9 flex-col items-center gap-1 rounded-lg px-1 py-1.5 text-center transition active:scale-95"
                  style={{
                    outline: isSelected || isEvent ? `1px solid ${color}30` : "none",
                    background: isSelected ? `${color}14` : "transparent",
                  }}
                  aria-label={[
                    day.dayNumber,
                    label,
                    typeof lunar.illumination === "number" ? `${Math.round(lunar.illumination)}%` : null,
                  ].filter(Boolean).join(", ")}
                >
                  <span className="text-[9px] tabular-nums text-muted-foreground">{day.dayNumber}</span>
                  <PhaseGlyph phaseIndex={lunar.phaseIndex} size={20} />
                  {typeof lunar.illumination === "number" ? (
                    <span
                      className="text-[8px] tabular-nums leading-none"
                      style={{ color: isEvent ? color : "oklch(0.55 0.02 295)" }}
                    >
                      {Math.round(lunar.illumination)}%
                    </span>
                  ) : null}
                </button>
              )
            })}
          </div>
        </div>

        {selected ? (
          <div className="mt-3 rounded-md border border-border/50 bg-background/60 p-3" data-testid="lunar-calendar-selected-detail">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
              <PhaseGlyph phaseIndex={selected.lunar.phaseIndex} size={24} />
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
          <span className="inline-flex items-center gap-1"><PhaseGlyph phaseIndex={0} size={9} /> новолуние</span>
          <span className="inline-flex items-center gap-1"><PhaseGlyph phaseIndex={4} size={9} /> полнолуние</span>
          <span className="inline-flex items-center gap-1"><PhaseGlyph phaseIndex={2} size={9} /> четверть</span>
        </div>
      </div>
    </section>
  )
}
