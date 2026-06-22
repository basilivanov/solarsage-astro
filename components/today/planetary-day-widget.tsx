"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Clock } from "lucide-react"
import { getPlanetaryDay } from "@/lib/planetary-day"

/**
 * PlanetaryDayWidget — shows the day ruler and current hour ruler
 * based on traditional Western planetary day/hour system.
 *
 * Each day of the week is ruled by one of the 7 classical planets,
 * setting the "flavor" of the day. Planetary hours cycle through
 * the Chaldean order within each day.
 */

interface PlanetaryDayWidgetProps {
  date: Date
}

export function PlanetaryDayWidget({ date }: PlanetaryDayWidgetProps) {
  const [expanded, setExpanded] = useState(false)

  const info = useMemo(() => getPlanetaryDay(date), [date])

  return (
    <section className="px-6" aria-label="Планетарный день">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="group relative w-full overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20 p-4 text-left transition-all hover:border-border active:scale-[0.99]"
        aria-expanded={expanded}
      >
        {/* Decorative glow keyed to day ruler color */}
        <div
          aria-hidden
          className="pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full opacity-40"
          style={{
            background: `radial-gradient(circle, ${info.dayRulerColor}22, transparent 70%)`,
          }}
        />

        <div className="relative flex items-center gap-4">
          {/* Day ruler symbol */}
          <div
            className="flex h-14 w-14 flex-none items-center justify-center rounded-full border-2"
            style={{
              borderColor: info.dayRulerColor,
              background: `${info.dayRulerColor}10`,
            }}
          >
            <span className="text-[22px] leading-none" style={{ color: info.dayRulerColor }}>
              {info.dayRulerSymbol}
            </span>
          </div>

          {/* Info */}
          <div className="min-w-0 flex-1">
            <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              {info.dayOfWeekRu}
            </div>
            <div className="mt-0.5 flex items-baseline gap-2">
              <span className="font-serif text-[17px] leading-tight text-foreground">
                День {info.dayRulerRu}
              </span>
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <Clock className="h-3 w-3" strokeWidth={1.8} />
              <span>Час {info.hourRulerSymbol} {info.hourRulerRu}</span>
              <span aria-hidden>·</span>
              <span className={info.hourType === "day" ? "text-amber-600 dark:text-amber-400" : "text-indigo-600 dark:text-indigo-400"}>
                {info.hourType === "day" ? "дневной" : "ночной"}
              </span>
            </div>
          </div>
        </div>

        {/* Expandable detail */}
        <AnimatePresence initial={false}>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              <div className="mt-3 space-y-2.5 border-t border-border/50 pt-3">
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <span className="text-[14px] leading-none" style={{ color: info.dayRulerColor }}>
                      {info.dayRulerSymbol}
                    </span>
                    <span className="text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                      Управитель дня
                    </span>
                  </div>
                  <p className="text-[11.5px] leading-relaxed text-foreground/80">
                    {info.dayInterpretation}
                  </p>
                </div>
                <div className="rounded-lg bg-secondary/30 px-3 py-2">
                  <div className="mb-0.5 flex items-center gap-1.5">
                    <span className="text-[14px] leading-none" style={{ color: PLANET_COLORS[info.hourRuler] ?? info.dayRulerColor }}>
                      {info.hourRulerSymbol}
                    </span>
                    <span className="text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                      Управитель часа
                    </span>
                  </div>
                  <p className="text-[11.5px] leading-relaxed text-muted-foreground">
                    {info.hourInterpretation}
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-2 text-center text-[10px] text-muted-foreground/70">
          {expanded ? "↑ свернуть" : "↓ подробнее"}
        </div>
      </button>
    </section>
  )
}

const PLANET_COLORS: Record<string, string> = {
  Sun: "oklch(0.72 0.15 60)",
  Moon: "oklch(0.62 0.04 295)",
  Mars: "oklch(0.58 0.18 27)",
  Mercury: "oklch(0.62 0.08 230)",
  Jupiter: "oklch(0.70 0.13 85)",
  Venus: "oklch(0.70 0.12 15)",
  Saturn: "oklch(0.55 0.05 260)",
}
