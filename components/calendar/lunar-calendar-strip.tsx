"use client"

import { useState } from "react"
import { CalendarDays, Moon, Info } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

import { PhaseGlyph, phaseColor } from "@/components/calendar/phase-glyph"
import type { CalendarDayReadModel } from "@/lib/contracts/calendar"
import { lunarPhaseLabel } from "@/lib/lunar-presentation"

type Props = {
  days: CalendarDayReadModel[]
}

const PHASE_COLORS: Record<number, string> = {
  0: "oklch(0.30 0.02 295)", // new moon — deep
  1: "oklch(0.60 0.04 295)", // waxing crescent
  2: "oklch(0.55 0.06 305)", // first quarter — plum
  3: "oklch(0.65 0.05 305)", // waxing gibbous
  4: "oklch(0.72 0.08 85)",  // full moon — gold
  5: "oklch(0.65 0.05 305)", // waning gibbous
  6: "oklch(0.55 0.06 305)", // last quarter — plum
  7: "oklch(0.60 0.04 295)", // waning crescent
}

const PHASE_DESCRIPTIONS: Record<number, string> = {
  0: "Время начинаний и намерений",
  1: "Рост, первые шаги к цели",
  2: "Решительность и действие",
  3: "Усиление и приближение к пиковой энергии",
  4: "Пик эмоций, кульминация, ясность",
  5: "Подведение итогов, благодарность",
  6: "Освобождение, пересмотр",
  7: "Отдых, рефлексия, закрытие цикла",
}

const ZODIAC_INFO: Record<string, { symbol: string; element: string }> = {
  "Овен": { symbol: "♈", element: "Огонь" },
  "Телец": { symbol: "♉", element: "Земля" },
  "Близнецы": { symbol: "♊", element: "Воздух" },
  "Рак": { symbol: "♋", element: "Вода" },
  "Лев": { symbol: "♌", element: "Огонь" },
  "Дева": { symbol: "♍", element: "Земля" },
  "Весы": { symbol: "♎", element: "Воздух" },
  "Скорпион": { symbol: "♏", element: "Вода" },
  "Стрелец": { symbol: "♐", element: "Огонь" },
  "Козерог": { symbol: "♑", element: "Земля" },
  "Водолей": { symbol: "♒", element: "Воздух" },
  "Рыбы": { symbol: "♓", element: "Вода" },
}

const ZODIAC_BY_ABBR: Record<string, { name: string; symbol: string; element: string }> = {
  ari: { name: "Овен", symbol: "♈", element: "Огонь" },
  tau: { name: "Телец", symbol: "♉", element: "Земля" },
  gem: { name: "Близнецы", symbol: "♊", element: "Воздух" },
  can: { name: "Рак", symbol: "♋", element: "Вода" },
  cnc: { name: "Рак", symbol: "♋", element: "Вода" },
  leo: { name: "Лев", symbol: "♌", element: "Огонь" },
  vir: { name: "Дева", symbol: "♍", element: "Земля" },
  lib: { name: "Весы", symbol: "♎", element: "Воздух" },
  sco: { name: "Скорпион", symbol: "♏", element: "Вода" },
  sgr: { name: "Стрелец", symbol: "♐", element: "Огонь" },
  sag: { name: "Стрелец", symbol: "♐", element: "Огонь" },
  cap: { name: "Козерог", symbol: "♑", element: "Земля" },
  aqr: { name: "Водолей", symbol: "♒", element: "Воздух" },
  psc: { name: "Рыбы", symbol: "♓", element: "Вода" },
  pis: { name: "Рыбы", symbol: "♓", element: "Вода" },
}

function getZodiacDetails(label: string | null | undefined, sign: string | null | undefined) {
  const cleanLabel = label?.trim()
  if (cleanLabel && ZODIAC_INFO[cleanLabel]) {
    return {
      name: cleanLabel,
      symbol: ZODIAC_INFO[cleanLabel].symbol,
      element: ZODIAC_INFO[cleanLabel].element,
    }
  }
  const cleanSign = sign?.trim().toLowerCase()
  if (cleanSign && ZODIAC_BY_ABBR[cleanSign]) {
    return ZODIAC_BY_ABBR[cleanSign]
  }
  return {
    name: cleanLabel || sign || "Неизвестно",
    symbol: "🌙",
    element: "",
  }
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
        <div className="rounded-lg border border-border/50 bg-card/77 px-4 py-4 text-center">
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
      <div className="rounded-2xl border border-border/50 bg-gradient-to-br from-card via-card to-secondary/20 p-4">
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

        <AnimatePresence>
          {selected && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
              data-testid="lunar-calendar-selected-detail"
            >
              {(() => {
                const dateParts = selected.date.split("-").map(Number)
                const month = dateParts[1]
                const phaseIdx = selected.lunar.phaseIndex ?? 7
                const phaseColorVal = PHASE_COLORS[phaseIdx] ?? "oklch(0.60 0.04 295)"
                const phaseDesc = PHASE_DESCRIPTIONS[phaseIdx] ?? ""
                const zodiac = getZodiacDetails(selected.lunar.moonSignLabel, selected.lunar.moonSign)
                const phaseName = lunarPhaseLabel(selected.lunar) ?? "Луна"

                return (
                  <div className="mt-3 rounded-lg border border-border/50 bg-background/60 p-3">
                    <div className="flex items-center gap-3">
                      <PhaseGlyph phaseIndex={phaseIdx} size={36} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-baseline justify-between gap-2">
                          <span className="text-sm font-medium text-foreground">
                            {phaseName}
                          </span>
                          <span className="text-[11px] tabular-nums text-muted-foreground">
                            {selected.dayNumber}.{month} · {selected.lunar.illumination}%
                          </span>
                        </div>
                        {phaseDesc ? (
                          <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                            {phaseDesc}
                          </p>
                        ) : null}
                        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                          <span
                            className="inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[9px] font-medium"
                            style={{
                              color: phaseColorVal,
                              background: `${phaseColorVal}14`,
                            }}
                          >
                            {zodiac.symbol} {zodiac.name}
                          </span>
                          {zodiac.element ? (
                            <span className="text-[9px] text-muted-foreground">
                              {zodiac.element}
                            </span>
                          ) : null}
                          {selected.lunar.lunarDay != null ? (
                            <>
                              <span className="text-[9px] text-muted-foreground/60" aria-hidden>·</span>
                              <span className="text-[9px] text-muted-foreground font-medium">
                                {selected.lunar.lunarDay} лунный день
                              </span>
                            </>
                          ) : null}
                          {selected.lunar.voidOfCourse === true ? (
                            <>
                              <span className="text-[9px] text-muted-foreground/60" aria-hidden>·</span>
                              <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-1.5 py-0.5 text-[9px] font-medium text-amber-700 dark:text-amber-400">
                                <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                                без курса
                              </span>
                            </>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })()}
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-2.5 flex items-center justify-center gap-3 text-[9px] text-muted-foreground/70">
          <span className="inline-flex items-center gap-1">
            <PhaseGlyph phaseIndex={0} size={9} />
            новолуние
          </span>
          <span className="inline-flex items-center gap-1">
            <PhaseGlyph phaseIndex={4} size={9} />
            полнолуние
          </span>
          <span className="inline-flex items-center gap-1">
            <PhaseGlyph phaseIndex={2} size={9} />
            четверть
          </span>
          <span className="inline-flex items-center gap-1">
            <Info className="h-2.5 w-2.5" strokeWidth={1.75} />
            ±1 день
          </span>
        </div>
      </div>
    </section>
  )
}
