"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { RotateCcw, ChevronDown } from "lucide-react"
import { getAllRetrogrades } from "@/lib/retrograde"

/**
 * RetrogradeTracker — shows which planets (Mercury, Venus, Mars) are
 * currently retrograde, with timing and interpretation.
 *
 * Retrograde periods are computed from simplified mean orbital elements.
 * Real dates would come from the SolarSage sidecar with full ephemeris.
 */

interface RetrogradeTrackerProps {
  date: Date
}

function formatDate(d: Date): string {
  const months = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
  return `${d.getDate()} ${months[d.getMonth()]}`
}

export function RetrogradeTracker({ date }: RetrogradeTrackerProps) {
  const [expanded, setExpanded] = useState<string | null>(null)

  const retrogrades = useMemo(() => getAllRetrogrades(date), [date])
  const anyRx = retrogrades.some((r) => r.isRetrograde)
  const rxCount = retrogrades.filter((r) => r.isRetrograde).length

  return (
    <section className="px-6" aria-label="Ретроградные планеты">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          <RotateCcw className="h-3 w-3" strokeWidth={1.8} />
          Ретрограды
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20">
        {/* Summary header */}
        <div
          className="flex items-center justify-between px-4 py-3"
          style={{
            background: anyRx
              ? "linear-gradient(90deg, oklch(0.65 0.12 27 / 0.06), transparent)"
              : "linear-gradient(90deg, oklch(0.65 0.13 145 / 0.04), transparent)",
          }}
        >
          <div className="flex items-center gap-2">
            <span
              className={`flex h-2 w-2 rounded-full ${anyRx ? "bg-amber-500" : "bg-emerald-500"}`}
            >
              {anyRx && (
                <motion.span
                  className="h-full w-full rounded-full bg-amber-500"
                  animate={{ scale: [1, 1.6, 1], opacity: [0.7, 0, 0.7] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              )}
            </span>
            <span className="text-[12px] font-medium text-foreground">
              {anyRx ? `${rxCount} ретроградн${rxCount === 1 ? "ая" : "ых"}` : "Все прямые"}
            </span>
          </div>
          <span className="text-[10px] text-muted-foreground">
            {anyRx ? "осторожно с начинаниями" : "можно действовать"}
          </span>
        </div>

        {/* Planet list */}
        <ol className="divide-y divide-border/40">
          {retrogrades.map((r) => {
            const isExpanded = expanded === r.planet
            return (
              <li key={r.planet}>
                <button
                  type="button"
                  onClick={() => setExpanded(isExpanded ? null : r.planet)}
                  className="group flex w-full items-center gap-3 px-4 py-2.5 text-left transition hover:bg-muted/20"
                >
                  {/* Planet symbol with Rx indicator */}
                  <div className="relative flex h-8 w-8 flex-none items-center justify-center">
                    <span
                      className="text-[16px] leading-none"
                      style={{ color: r.color, opacity: r.isRetrograde ? 1 : 0.5 }}
                    >
                      {r.symbol}
                    </span>
                    {r.isRetrograde && (
                      <motion.span
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="absolute -bottom-1 -right-1 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-amber-500 text-[7px] font-bold text-white"
                        title="Ретроградная"
                      >
                        R
                      </motion.span>
                    )}
                  </div>

                  {/* Planet name + status */}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[12.5px] font-medium text-foreground">{r.planetRu}</span>
                      <span
                        className={`rounded-full px-1.5 py-0.5 text-[9px] font-medium ${
                          r.isRetrograde
                            ? "bg-amber-500/15 text-amber-700 dark:text-amber-400"
                            : "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                        }`}
                      >
                        {r.isRetrograde ? "R" : "∅"}
                      </span>
                    </div>
                    <div className="mt-0.5 text-[10.5px] text-muted-foreground">
                      {r.isRetrograde
                        ? `До ${r.rxEndsAt ? formatDate(r.rxEndsAt) : "—"} · ${r.daysIntoRx}/${r.rxDurationDays} дн.`
                        : `След. R с ${r.nextRXStart ? formatDate(r.nextRXStart) : "—"}`}
                    </div>
                  </div>

                  <ChevronDown
                    className={`h-3.5 w-3.5 flex-none text-muted-foreground transition-transform ${isExpanded ? "rotate-180" : ""}`}
                    strokeWidth={1.8}
                  />
                </button>

                {/* Expandable detail */}
                <AnimatePresence initial={false}>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="px-4 pb-3 pt-1">
                        <div
                          className="rounded-lg px-3 py-2 text-[11.5px] leading-relaxed"
                          style={{
                            background: r.isRetrograde
                              ? "oklch(0.65 0.12 27 / 0.06)"
                              : "oklch(0.65 0.13 145 / 0.04)",
                          }}
                        >
                          {r.isRetrograde ? (
                            <>
                              <span className="font-medium" style={{ color: r.color }}>
                                {r.planetRu} ретроградна.
                              </span>{" "}
                              {r.interpretation}
                              <div className="mt-1.5 flex items-center gap-3 text-[10px] tabular-nums text-muted-foreground">
                                <span>Начало: {r.rxStartedAt ? formatDate(r.rxStartedAt) : "—"}</span>
                                <span>·</span>
                                <span>Конец: {r.rxEndsAt ? formatDate(r.rxEndsAt) : "—"}</span>
                              </div>
                            </>
                          ) : (
                            <>
                              <span className="font-medium" style={{ color: r.color }}>
                                {r.planetRu} в прямом движении.
                              </span>{" "}
                              Можно начинать новые дела, подписывать контракты, принимать решения
                              в сфере {r.planet === "Mercury" ? "коммуникаций" : r.planet === "Venus" ? "отношений и финансов" : "действий и энергии"}.
                            </>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </li>
            )
          })}
        </ol>
      </div>
    </section>
  )
}
