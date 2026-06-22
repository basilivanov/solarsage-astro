"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Compass } from "lucide-react"
import { getLunarNodes } from "@/lib/lunar-nodes"

/**
 * LunarNodeWidget — shows the North (Rahu) and South (Ketu) lunar
 * node positions by sign and house, with interpretations.
 *
 * The nodes are destiny points in astrology — the North Node shows
 * the soul's growth direction, the South Node shows past karma.
 * They move retrograde through the zodiac in an 18.6-year cycle.
 */

interface LunarNodeWidgetProps {
  date?: Date
}

export function LunarNodeWidget({ date }: LunarNodeWidgetProps) {
  const [expanded, setExpanded] = useState(false)

  const nodes = useMemo(() => getLunarNodes(date ?? new Date()), [date])

  return (
    <section className="px-5 pt-6" aria-label="Лунные узлы">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          <Compass className="h-3 w-3" strokeWidth={1.8} />
          Лунные узлы
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="group relative w-full overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20 p-4 text-left transition-all hover:border-border active:scale-[0.99]"
        aria-expanded={expanded}
      >
        {/* Two-column: North (Rahu) + South (Ketu) */}
        <div className="grid grid-cols-2 gap-3">
          {/* North Node (Rahu) */}
          <div className="relative">
            <div
              aria-hidden
              className="pointer-events-none absolute -right-4 -top-4 h-16 w-16 rounded-full opacity-30"
              style={{ background: "radial-gradient(circle, oklch(0.55 0.10 305 / 0.15), transparent 70%)" }}
            />
            <div className="relative">
              <div className="text-[9px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                ☊ Северный (Раху)
              </div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="font-serif text-[24px] leading-none" style={{ color: "oklch(0.55 0.10 305)" }}>
                  {nodes.northNodeSymbol}
                </span>
                <div>
                  <div className="font-serif text-[16px] leading-tight text-foreground">
                    {nodes.northNodeSignRu}
                  </div>
                  <div className="text-[10px] text-muted-foreground">
                    {nodes.northNodeHouse} дом
                  </div>
                </div>
              </div>
              <p className="mt-1.5 text-[10.5px] leading-snug text-muted-foreground">
                {nodes.northNodeInterpretation}
              </p>
            </div>
          </div>

          {/* South Node (Ketu) */}
          <div className="relative border-l border-border/40 pl-3">
            <div
              aria-hidden
              className="pointer-events-none absolute -left-4 -top-4 h-16 w-16 rounded-full opacity-30"
              style={{ background: "radial-gradient(circle, oklch(0.55 0.08 260 / 0.12), transparent 70%)" }}
            />
            <div className="relative">
              <div className="text-[9px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                ☋ Южный (Кету)
              </div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="font-serif text-[24px] leading-none" style={{ color: "oklch(0.55 0.08 260)" }}>
                  {nodes.southNodeSymbol}
                </span>
                <div>
                  <div className="font-serif text-[16px] leading-tight text-foreground">
                    {nodes.southNodeSignRu}
                  </div>
                  <div className="text-[10px] text-muted-foreground">
                    {nodes.southNodeHouse} дом
                  </div>
                </div>
              </div>
              <p className="mt-1.5 text-[10.5px] leading-snug text-muted-foreground">
                {nodes.southNodeInterpretation}
              </p>
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
              <div className="mt-3 space-y-2 border-t border-border/50 pt-3">
                <div className="rounded-lg bg-secondary/30 px-3 py-2">
                  <div className="mb-0.5 text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                    ☊ Раху — направление роста
                  </div>
                  <p className="text-[11.5px] leading-relaxed text-foreground/80">
                    {nodes.northNodeInterpretation}
                  </p>
                  <div className="mt-1 text-[10px] text-muted-foreground">
                    Знак: {nodes.northNodeSignRu} · Дом: {nodes.northNodeHouse} (рост через сферу этого дома)
                  </div>
                </div>
                <div className="rounded-lg bg-secondary/30 px-3 py-2">
                  <div className="mb-0.5 text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                    ☋ Кету — карма прошлого
                  </div>
                  <p className="text-[11.5px] leading-relaxed text-foreground/80">
                    {nodes.southNodeInterpretation}
                  </p>
                  <div className="mt-1 text-[10px] text-muted-foreground">
                    Знак: {nodes.southNodeSignRu} · Дом: {nodes.southNodeHouse} (знакомая сфера)
                  </div>
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-primary/5 px-3 py-2 text-[11px]">
                  <span className="text-primary">⏳</span>
                  <span className="text-muted-foreground">
                    Узлы сменят знак через ~{nodes.yearsUntilSignChange} {nodes.yearsUntilSignChange === 1 ? "год" : "года"}
                  </span>
                </div>
                <p className="text-[10px] leading-relaxed text-muted-foreground/60">
                  Лунные узлы — точки пересечения орбиты Луны с эклиптикой. Движутся ретроградно, проходя весь зодиак за ~18.6 лет.
                </p>
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
