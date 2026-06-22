"use client"

import { motion } from "framer-motion"

/**
 * DayEnergyMeter — horizontal stacked visualization of the day's
 * planetary "strength" / influence weights. Bars are derived from
 * the demo topFlags strengths (0-1), grouped by planet.
 *
 * Purely presentational — drives engagement and gives the user a
 * sense of which planetary energies dominate the day.
 */

export interface EnergyItem {
  name: string
  symbol: string
  strength: number // 0..1
  color: string
}

interface DayEnergyMeterProps {
  items: EnergyItem[]
  dayStatus: "steady" | "supportive" | "tense"
}

const STATUS_LABEL: Record<string, string> = {
  steady: "Ровный день",
  supportive: "Поддерживающий день",
  tense: "Напряжённый день",
}

const STATUS_COLOR: Record<string, string> = {
  steady: "oklch(0.62 0.06 305)",
  supportive: "oklch(0.68 0.12 150)",
  tense: "oklch(0.58 0.14 27)",
}

const STATUS_HINT: Record<string, string> = {
  steady: "Энергии сбалансированы — опирайся на рутину и внимательно относись к деталям.",
  supportive: "Планеты дают мягкую поддержку — хороший день для начинаний и контактов.",
  tense: "Несколько напряжённых аспектов — будь осмотрителен в решениях и общении.",
}

const PLANET_RU: Record<string, string> = {
  Sun: "Солнце",
  Moon: "Луна",
  Mercury: "Меркурий",
  Venus: "Венера",
  Mars: "Марс",
  Jupiter: "Юпитер",
  Saturn: "Сатурн",
  Uranus: "Уран",
  Neptune: "Нептун",
  Pluto: "Плутон",
}

function planetRu(name: string): string {
  return PLANET_RU[name] ?? name
}

export function DayEnergyMeter({ items, dayStatus }: DayEnergyMeterProps) {
  const total = items.reduce((s, i) => s + i.strength, 0) || 1
  const accent = STATUS_COLOR[dayStatus]
  const sorted = [...items].sort((a, b) => b.strength - a.strength)
  const topPlanet = sorted[0]

  return (
    <section className="px-6" aria-label="Энергия дня">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Энергия дня
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      {/* status pill */}
      <div
        className="mb-4 flex items-center justify-between rounded-xl border px-4 py-3"
        style={{
          borderColor: `${accent}40`,
          background: `${accent}0d`,
        }}
      >
        <div className="flex items-center gap-2.5">
          <span
            className="h-2.5 w-2.5 animate-pulse rounded-full"
            style={{ background: accent, boxShadow: `0 0 8px ${accent}` }}
            aria-hidden
          />
          <span className="text-sm font-medium text-foreground">
            {STATUS_LABEL[dayStatus]}
          </span>
        </div>
        {topPlanet && (
          <span className="text-[11px] text-muted-foreground">
            доминирует{" "}
            <span className="font-semibold" style={{ color: topPlanet.color }}>
              {topPlanet.symbol} {planetRu(topPlanet.name)}
            </span>
          </span>
        )}
      </div>

      {/* stacked bar */}
      <div className="energy-stacked-bar mb-2 flex h-2.5 w-full overflow-hidden rounded-full bg-muted">
        {sorted.map((item, i) => (
          <motion.div
            key={item.name}
            initial={{ width: 0, opacity: 0 }}
            animate={{
              width: `${(item.strength / total) * 100}%`,
              opacity: 1,
            }}
            transition={{
              duration: 0.6,
              delay: 0.1 + i * 0.08,
              ease: "easeOut",
            }}
            style={{
              background: item.color,
              minWidth: item.strength > 0.05 ? "4px" : "0",
            }}
            title={`${planetRu(item.name)}: ${Math.round(item.strength * 100)}%`}
          />
        ))}
      </div>

      {/* individual rows */}
      <div className="mt-3 space-y-1.5">
        {sorted.map((item, i) => (
          <motion.div
            key={item.name}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.35, delay: 0.15 + i * 0.05 }}
            className="planet-chip flex items-center gap-3 rounded-md py-0.5"
          >
            <span
              className="flex h-6 w-6 flex-none items-center justify-center rounded-md text-xs font-semibold"
              style={{
                color: item.color,
                background: `${item.color}14`,
              }}
            >
              {item.symbol}
            </span>
            <span className="w-20 flex-none text-xs font-medium text-foreground">
              {planetRu(item.name)}
            </span>
            <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${item.strength * 100}%` }}
                transition={{ duration: 0.7, delay: 0.2 + i * 0.05, ease: "easeOut" }}
                className="absolute inset-y-0 left-0 rounded-full"
                style={{ background: item.color }}
              />
            </div>
            <span className="w-9 flex-none text-right text-[11px] tabular-nums text-muted-foreground">
              {Math.round(item.strength * 100)}
            </span>
          </motion.div>
        ))}
      </div>

      <p className="mt-3.5 text-[12px] leading-relaxed text-muted-foreground">
        {STATUS_HINT[dayStatus]}
      </p>
    </section>
  )
}
