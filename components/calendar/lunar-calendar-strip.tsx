"use client"

import { useState } from "react"
import { CalendarDays, Moon } from "lucide-react"

import type { CalendarDayReadModel } from "@/lib/contracts/calendar"

type Props = {
  days: CalendarDayReadModel[]
}

function hasLunarFacts(day: CalendarDayReadModel): boolean {
  const lunar = day.lunar
  return lunar.phase != null
    || lunar.illumination != null
    || lunar.moonSign != null
    || lunar.lunarDay != null
    || lunar.voidOfCourse != null
}

export function LunarCalendarStrip({ days }: Props) {
  const lunarDays = days.filter((day) => day.isCurrentMonth && hasLunarFacts(day))
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const selected = lunarDays.find((day) => day.date === selectedDate) ?? lunarDays[0] ?? null

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
            <span>{lunarDays.length} дней с данными</span>
          </div>
        </div>

        <div className="-mx-1 overflow-x-auto px-1 pb-1">
          <div className="flex min-w-max gap-1.5">
            {lunarDays.map((day) => {
              const lunar = day.lunar
              const isSelected = day.date === selected?.date
              return (
                <button
                  key={day.date}
                  type="button"
                  onClick={() => setSelectedDate(day.date)}
                  className="flex w-16 flex-col items-center gap-1 rounded-md border px-1.5 py-2 text-center transition active:scale-95"
                  style={{
                    borderColor: isSelected ? "var(--primary)" : "var(--border)",
                    background: isSelected ? "var(--secondary)" : "transparent",
                  }}
                  aria-label={[
                    day.dayNumber,
                    lunar.phase,
                    typeof lunar.illumination === "number" ? `${Math.round(lunar.illumination)}%` : null,
                  ].filter(Boolean).join(", ")}
                >
                  <span className="text-[9px] tabular-nums text-muted-foreground">{day.dayNumber}</span>
                  <Moon className="h-5 w-5 text-foreground" strokeWidth={1.75} aria-hidden />
                  <span className="max-w-full truncate text-[9px] leading-tight text-muted-foreground">
                    {lunar.phase ?? "Луна"}
                  </span>
                  {typeof lunar.illumination === "number" ? (
                    <span className="text-[9px] tabular-nums text-muted-foreground">{Math.round(lunar.illumination)}%</span>
                  ) : null}
                  {typeof lunar.lunarDay === "number" ? (
                    <span className="text-[9px] leading-tight text-muted-foreground">{lunar.lunarDay} лунный день</span>
                  ) : null}
                  {lunar.voidOfCourse === true ? (
                    <span className="text-[9px] leading-tight text-amber-700 dark:text-amber-400">без курса</span>
                  ) : null}
                </button>
              )
            })}
          </div>
        </div>

        {selected ? (
          <div className="mt-3 rounded-md border border-border/50 bg-background/60 p-3">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
              <Moon className="h-4 w-4 text-foreground" strokeWidth={1.75} aria-hidden />
              {selected.lunar.phase ? <span className="font-medium text-foreground">{selected.lunar.phase}</span> : null}
              {typeof selected.lunar.illumination === "number" ? (
                <span className="text-muted-foreground">{Math.round(selected.lunar.illumination)}%</span>
              ) : null}
              {typeof selected.lunar.lunarDay === "number" ? (
                <span className="text-muted-foreground">{selected.lunar.lunarDay} лунный день</span>
              ) : null}
              {selected.lunar.moonSign ? <span className="text-muted-foreground">{selected.lunar.moonSign}</span> : null}
              {selected.lunar.voidOfCourse === true ? (
                <span className="rounded-full bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400">
                  без курса
                </span>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  )
}
