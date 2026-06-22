"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Clock, ChevronDown } from "lucide-react"
import { getPlanetaryHourTimeline, type PlanetaryHourEntry } from "@/lib/planetary-day"

/**
 * PlanetaryHourTimeline — shows the 12 hours of the current planetary
 * period (day or night) with their ruling planets, highlighting the
 * current hour.
 *
 * In traditional Western astrology, each hour is ruled by one of the
 * 7 classical planets following the Chaldean order. The first hour
 * of each period is ruled by the day ruler.
 */

interface PlanetaryHourTimelineProps {
  date: Date
}

function formatHour(d: Date): string {
  return d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
}

const HOUR_INTERPRETATIONS: Record<string, string> = {
  Sun: "Активность, самовыражение, лидерство. Хорошо для публичных дел.",
  Moon: "Эмоции, интуиция, дом. Хорошо для заботы и отдыха.",
  Mars: "Действие, смелость, скорость. Хорошо для спорта и решений.",
  Mercury: "Общение, торговля, документы. Хорошо для переговоров и учёбы.",
  Jupiter: "Расширение, удача, мудрость. Хорошо для крупных дел.",
  Venus: "Красота, любовь, партнёрство. Хорошо для отношений и искусства.",
  Saturn: "Структура, дисциплина, итоги. Хорошо для рутины и планирования.",
}

export function PlanetaryHourTimeline({ date }: PlanetaryHourTimelineProps) {
  const [expanded, setExpanded] = useState(false)
  const [hovered, setHovered] = useState<number | null>(null)

  const hours = useMemo(() => getPlanetaryHourTimeline(date), [date])
  const current = useMemo(() => hours.find((h) => h.isCurrent) ?? null, [hours])
  const periodLabel = hours[0]?.type === "day" ? "Дневные часы" : "Ночные часы"

  return (
    <section className="px-6" aria-label="Планетарные часы">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="group relative w-full overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20 p-4 text-left transition-all hover:border-border active:scale-[0.99]"
        aria-expanded={expanded}
      >
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-primary/10">
            <Clock className="h-4 w-4 text-primary" strokeWidth={1.8} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              {periodLabel}
            </div>
            <div className="mt-0.5 flex items-center gap-2">
              {current && (
                <>
                  <span className="text-[16px] leading-none" style={{ color: current.rulerColor }}>
                    {current.rulerSymbol}
                  </span>
                  <span className="font-serif text-[15px] leading-tight text-foreground">
                    Час {current.rulerRu}
                  </span>
                </>
              )}
            </div>
          </div>
          <div className="flex-none text-right">
            {current && (
              <>
                <div className="text-[10px] text-muted-foreground">сейчас</div>
                <div className="text-[11px] tabular-nums text-foreground">
                  {formatHour(current.startsAt)}–{formatHour(current.endsAt)}
                </div>
              </>
            )}
          </div>
          <ChevronDown
            className={`h-4 w-4 flex-none text-muted-foreground transition-transform ${expanded ? "rotate-180" : ""}`}
            strokeWidth={1.8}
          />
        </div>

        {/* Hour strip — always visible */}
        <div className="mt-3 flex gap-0.5">
          {hours.map((h, i) => (
            <div
              key={i}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
              className="group/hr relative flex-1"
              title={`${formatHour(h.startsAt)} ${h.rulerSymbol} ${h.rulerRu}`}
            >
              <div
                className="h-6 rounded transition-all"
                style={{
                  background: h.isCurrent
                    ? h.rulerColor
                    : `${h.rulerColor}25`,
                  opacity: h.isCurrent ? 1 : hovered === i ? 0.9 : 0.5,
                }}
              />
              <div
                className={`mt-0.5 text-center text-[8px] tabular-nums transition-opacity ${
                  h.isCurrent || hovered === i ? "opacity-100" : "opacity-40"
                }`}
                style={{ color: h.isCurrent ? h.rulerColor : undefined }}
              >
                {h.startsAt.getHours()}
              </div>
            </div>
          ))}
        </div>

        {/* Hovered hour detail */}
        <AnimatePresence initial={false}>
          {hovered !== null && (
            <motion.div
              key={hovered}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="mt-2 rounded-lg bg-secondary/30 px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <span className="text-[14px]" style={{ color: hours[hovered].rulerColor }}>
                  {hours[hovered].rulerSymbol}
                </span>
                <span className="text-[12px] font-medium text-foreground">
                  {hours[hovered].rulerRu}
                </span>
                <span className="ml-auto text-[10px] tabular-nums text-muted-foreground">
                  {formatHour(hours[hovered].startsAt)}–{formatHour(hours[hovered].endsAt)}
                </span>
                {hours[hovered].isCurrent && (
                  <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[9px] font-medium text-primary">
                    сейчас
                  </span>
                )}
              </div>
              <p className="mt-1 text-[11px] leading-snug text-muted-foreground">
                {HOUR_INTERPRETATIONS[hours[hovered].ruler] ?? ""}
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Expanded full list */}
        <AnimatePresence initial={false}>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              <div className="mt-3 space-y-1 border-t border-border/50 pt-3">
                {hours.map((h) => (
                  <HourRow key={h.index} hour={h} />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-2 text-center text-[10px] text-muted-foreground/70">
          {expanded ? "↑ свернуть" : "↓ все часы"}
        </div>
      </button>
    </section>
  )
}

function HourRow({ hour }: { hour: PlanetaryHourEntry }) {
  return (
    <div
      className={`flex items-center gap-3 rounded-lg px-2 py-1.5 transition-colors ${
        hour.isCurrent ? "bg-primary/8" : "hover:bg-muted/30"
      }`}
    >
      <span className="text-[14px] leading-none" style={{ color: hour.rulerColor }}>
        {hour.rulerSymbol}
      </span>
      <span className={`text-[12px] ${hour.isCurrent ? "font-medium text-foreground" : "text-foreground/80"}`}>
        {hour.rulerRu}
      </span>
      <span className="ml-auto text-[11px] tabular-nums text-muted-foreground">
        {formatHour(hour.startsAt)}–{formatHour(hour.endsAt)}
      </span>
      {hour.isCurrent && (
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="rounded-full bg-primary px-1.5 py-0.5 text-[9px] font-medium text-primary-foreground"
        >
          сейчас
        </motion.span>
      )}
    </div>
  )
}
