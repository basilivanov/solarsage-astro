"use client"

import { useMemo, useState } from "react"
import { motion } from "framer-motion"
import { DEMO_NATAL_RESPONSE } from "@/lib/demo-data"

/**
 * PlanetaryStrengthRadar — SVG radar chart showing the relative strength
 * of each planet in the natal chart.
 *
 * Strength is computed from:
 *  - Essential dignity: sign rulership (+5), exaltation (+4), triplicity (+3),
 *    term (+2), face (+1) — using traditional essential dignity table.
 *  - House placement: angular houses 1/4/7/10 (+3), succedent 2/5/8/11 (+1.5).
 *  - Aspect harmony: number of soft aspects (trine/sextile) minus hard (square/opposition).
 *
 * The result is normalised to a 0-100 score per planet and rendered as a
 * radar polygon overlay on a 10-axis wheel (7 classical + 3 modern planets).
 */

const PLANET_META: { name: string; ru: string; symbol: string; color: string }[] = [
  { name: "Sun", ru: "Солнце", symbol: "☉", color: "oklch(0.72 0.15 60)" },
  { name: "Moon", ru: "Луна", symbol: "☽", color: "oklch(0.62 0.04 295)" },
  { name: "Mercury", ru: "Меркурий", symbol: "☿", color: "oklch(0.62 0.08 230)" },
  { name: "Venus", ru: "Венера", symbol: "♀", color: "oklch(0.70 0.12 15)" },
  { name: "Mars", ru: "Марс", symbol: "♂", color: "oklch(0.58 0.18 27)" },
  { name: "Jupiter", ru: "Юпитер", symbol: "♃", color: "oklch(0.70 0.13 85)" },
  { name: "Saturn", ru: "Сатурн", symbol: "♄", color: "oklch(0.55 0.05 260)" },
  { name: "Uranus", ru: "Уран", symbol: "♅", color: "oklch(0.68 0.10 200)" },
  { name: "Neptune", ru: "Нептун", symbol: "♆", color: "oklch(0.62 0.10 270)" },
  { name: "Pluto", ru: "Плутон", symbol: "♇", color: "oklch(0.45 0.08 300)" },
]

const SIGN_RU: Record<string, string> = {
  Aries: "Овен", Taurus: "Телец", Gemini: "Близнецы", Cancer: "Рак",
  Leo: "Лев", Virgo: "Дева", Libra: "Весы", Scorpio: "Скорпион",
  Sagittarius: "Стрелец", Capricorn: "Козерог", Aquarius: "Водолей", Pisces: "Рыбы",
}

// Sign rulership + exaltation (traditional)
const RULER: Record<string, string> = {
  Aries: "Mars", Taurus: "Venus", Gemini: "Mercury", Cancer: "Moon",
  Leo: "Sun", Virgo: "Mercury", Libra: "Venus", Scorpio: "Mars",
  Sagittarius: "Jupiter", Capricorn: "Saturn", Aquarius: "Saturn", Pisces: "Jupiter",
}
const EXALTED: Record<string, string> = {
  Aries: "Sun", Taurus: "Moon", Cancer: "Jupiter", Virgo: "Mercury",
  Libra: "Saturn", Capricorn: "Mars", Pisces: "Venus",
}
const DETRIMENT: Record<string, string> = {
  Aries: "Venus", Taurus: "Mars", Gemini: "Jupiter", Cancer: "Saturn",
  Leo: "Saturn", Virgo: "Jupiter", Libra: "Mars", Scorpio: "Venus",
  Sagittarius: "Mercury", Capricorn: "Moon", Aquarius: "Sun", Pisces: "Mercury",
}
const FALL: Record<string, string> = {
  Aries: "Saturn", Taurus: "Uranus", Cancer: "Mars", Leo: "Neptune",
  Virgo: "Venus", Libra: "Sun", Scorpio: "Moon", Capricorn: "Jupiter",
  Aquarius: "Pluto", Pisces: "Mercury",
}

function computeStrength(planet: { name: string; sign: string; house: number; longitude: number }, allPlanets: { longitude: number }[]): {
  score: number
  details: string[]
} {
  let raw = 50
  const details: string[] = []

  // Essential dignity
  if (RULER[planet.sign] === planet.name) {
    raw += 22
    details.push("управитель знака (+22)")
  }
  if (EXALTED[planet.sign] === planet.name) {
    raw += 16
    details.push("экзальтация (+16)")
  }
  if (DETRIMENT[planet.sign] === planet.name) {
    raw -= 18
    details.push("изгнание (−18)")
  }
  if (FALL[planet.sign] === planet.name) {
    raw -= 12
    details.push("падение (−12)")
  }

  // Triplicity (element-based, simplified)
  const element = signElement(planet.sign)
  const triplicityRulers: Record<string, string> = {
    "Огонь": "Sun", "Земля": "Venus", "Воздух": "Saturn", "Вода": "Mars",
  }
  if (triplicityRulers[element] === planet.name) {
    raw += 8
    details.push("триплицитет (+8)")
  }

  // House strength
  if ([1, 4, 7, 10].includes(planet.house)) {
    raw += 14
    details.push(`угловой ${planet.house} дом (+14)`)
  } else if ([2, 5, 8, 11].includes(planet.house)) {
    raw += 6
    details.push(`суккедентный ${planet.house} дом (+6)`)
  } else {
    raw += 2
    details.push(`кадентный ${planet.house} дом (+2)`)
  }

  // Aspects to other planets
  let soft = 0, hard = 0
  for (const other of allPlanets) {
    if (other.longitude === planet.longitude) continue
    const diff = Math.abs(((other.longitude - planet.longitude) % 360 + 540) % 360 - 180)
    if (diff <= 8) { soft++; hard++ } // conjunction — neutral
    else if (Math.abs(diff - 60) <= 7 || Math.abs(diff - 120) <= 7) soft++
    else if (Math.abs(diff - 90) <= 7 || Math.abs(diff - 180) <= 7) hard++
  }
  raw += soft * 2 - hard * 2
  if (soft > hard) details.push(`гармоничные аспекты (+${(soft - hard) * 2})`)
  else if (hard > soft) details.push(`напряжённые аспекты (−${(hard - soft) * 2})`)

  return { score: Math.max(5, Math.min(100, Math.round(raw))), details }
}

function signElement(sign: string): string {
  const map: Record<string, string> = {
    Aries: "Огонь", Leo: "Огонь", Sagittarius: "Огонь",
    Taurus: "Земля", Virgo: "Земля", Capricorn: "Земля",
    Gemini: "Воздух", Libra: "Воздух", Aquarius: "Воздух",
    Cancer: "Вода", Scorpio: "Вода", Pisces: "Вода",
  }
  return map[sign] ?? "Огонь"
}

const SIZE = 320
const C = SIZE / 2
const R_MAX = 120
const RINGS = [0.25, 0.5, 0.75, 1.0]

export function PlanetaryStrengthRadar() {
  const [hovered, setHovered] = useState<number | null>(null)

  const strengths = useMemo(() => {
    const planets = DEMO_NATAL_RESPONSE.planets as { name: string; sign: string; house: number; longitude: number }[]
    return PLANET_META.map((meta) => {
      const p = planets.find((x) => x.name === meta.name)
      if (!p) return { ...meta, score: 50, details: ["данные отсутствуют"], sign: "—", house: 0 }
      const s = computeStrength(p, planets)
      return { ...meta, score: s.score, details: s.details, sign: p.sign, house: p.house }
    })
  }, [])

  // Radar polygon points
  const points = useMemo(() => {
    return strengths.map((s, i) => {
      const angle = (i / strengths.length) * Math.PI * 2 - Math.PI / 2
      const r = (s.score / 100) * R_MAX
      return {
        x: C + r * Math.cos(angle),
        y: C + r * Math.sin(angle),
        angle,
        labelX: C + (R_MAX + 22) * Math.cos(angle),
        labelY: C + (R_MAX + 22) * Math.sin(angle),
      }
    })
  }, [strengths])

  const polygon = points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ")

  const strongest = useMemo(() => [...strengths].sort((a, b) => b.score - a.score)[0], [strengths])
  const weakest = useMemo(() => [...strengths].sort((a, b) => a.score - b.score)[0], [strengths])

  return (
    <section className="px-5" aria-label="Сила планет">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Сила планет
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="gradient-border-soft rounded-2xl p-4">
        {/* Radar chart */}
        <div className="flex justify-center">
          <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="h-[300px] w-[300px]">
            <defs>
              <radialGradient id="radar-fill" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="oklch(0.55 0.10 305 / 0.35)" />
                <stop offset="100%" stopColor="oklch(0.55 0.10 305 / 0.10)" />
              </radialGradient>
              <filter id="radar-glow">
                <feGaussianBlur stdDeviation="2" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* Concentric rings */}
            {RINGS.map((r, i) => (
              <circle
                key={i}
                cx={C}
                cy={C}
                r={R_MAX * r}
                fill="none"
                stroke="oklch(0.5 0.03 295 / 0.15)"
                strokeWidth={0.5}
                strokeDasharray={i === RINGS.length - 1 ? "0" : "2,3"}
              />
            ))}
            {/* Ring labels */}
            {RINGS.map((r, i) => (
              <text
                key={`rl-${i}`}
                x={C + 3}
                y={C - R_MAX * r + 3}
                fontSize={7}
                fill="oklch(0.5 0.03 295 / 0.5)"
                className="tabular-nums"
              >
                {Math.round(r * 100)}
              </text>
            ))}

            {/* Axis spokes */}
            {points.map((p, i) => (
              <line
                key={`spoke-${i}`}
                x1={C}
                y1={C}
                x2={C + R_MAX * Math.cos(p.angle)}
                y2={C + R_MAX * Math.sin(p.angle)}
                stroke="oklch(0.5 0.03 295 / 0.12)"
                strokeWidth={0.5}
              />
            ))}

            {/* Filled polygon */}
            <motion.polygon
              points={polygon}
              fill="url(#radar-fill)"
              stroke="oklch(0.55 0.10 305)"
              strokeWidth={1.5}
              strokeLinejoin="round"
              filter="url(#radar-glow)"
              initial={{ opacity: 0, scale: 0.6 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.7, ease: "easeOut" }}
              style={{ transformOrigin: `${C}px ${C}px` }}
            />

            {/* Data points */}
            {points.map((p, i) => (
              <g key={`pt-${i}`}>
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={hovered === i ? 6 : 4}
                  fill={strengths[i].color}
                  stroke="oklch(0.98 0.01 305)"
                  strokeWidth={1.5}
                  className="cursor-pointer transition-all"
                  onMouseEnter={() => setHovered(i)}
                  onMouseLeave={() => setHovered(null)}
                />
                {/* Planet label */}
                <text
                  x={p.labelX}
                  y={p.labelY}
                  fontSize={14}
                  fill={hovered === i ? strengths[i].color : "oklch(0.4 0.02 305 / 0.85)"}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="cursor-pointer transition-all"
                  onMouseEnter={() => setHovered(i)}
                  onMouseLeave={() => setHovered(null)}
                >
                  {strengths[i].symbol}
                </text>
                {/* Score under label */}
                <text
                  x={p.labelX}
                  y={p.labelY + 11}
                  fontSize={8}
                  fill="oklch(0.5 0.03 295 / 0.6)"
                  textAnchor="middle"
                  className="tabular-nums"
                >
                  {strengths[i].score}
                </text>
              </g>
            ))}
          </svg>
        </div>

        {/* Hovered planet detail */}
        {hovered !== null && (
          <motion.div
            key={hovered}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 rounded-xl border border-border/40 bg-secondary/30 px-3 py-2.5"
          >
            <div className="flex items-center gap-2">
              <span className="text-[16px]" style={{ color: strengths[hovered].color }}>
                {strengths[hovered].symbol}
              </span>
              <span className="font-serif text-[14px] text-foreground">{strengths[hovered].ru}</span>
              <span className="ml-auto text-[12px] font-medium tabular-nums" style={{ color: strengths[hovered].color }}>
                {strengths[hovered].score}/100
              </span>
            </div>
            <div className="mt-1 text-[11px] text-muted-foreground">
              Знак: {SIGN_RU[strengths[hovered].sign] ?? strengths[hovered].sign} · Дом: {strengths[hovered].house}
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1">
              {strengths[hovered].details.map((d, i) => (
                <span
                  key={i}
                  className="rounded-full bg-card px-2 py-0.5 text-[10px] text-foreground/70"
                >
                  {d}
                </span>
              ))}
            </div>
          </motion.div>
        )}

        {/* Summary footer */}
        <div className="mt-3 grid grid-cols-2 gap-2">
          <div className="rounded-xl bg-emerald-500/8 px-3 py-2">
            <div className="text-[9px] font-medium uppercase tracking-[0.1em] text-emerald-700 dark:text-emerald-400">
              Сильнейшая
            </div>
            <div className="mt-0.5 flex items-center gap-1.5">
              <span className="text-[14px]" style={{ color: strongest.color }}>{strongest.symbol}</span>
              <span className="text-[12px] font-medium text-foreground">{strongest.ru}</span>
              <span className="ml-auto text-[12px] tabular-nums text-foreground/70">{strongest.score}</span>
            </div>
          </div>
          <div className="rounded-xl bg-amber-500/8 px-3 py-2">
            <div className="text-[9px] font-medium uppercase tracking-[0.1em] text-amber-700 dark:text-amber-400">
              Слабейшая
            </div>
            <div className="mt-0.5 flex items-center gap-1.5">
              <span className="text-[14px]" style={{ color: weakest.color }}>{weakest.symbol}</span>
              <span className="text-[12px] font-medium text-foreground">{weakest.ru}</span>
              <span className="ml-auto text-[12px] tabular-nums text-foreground/70">{weakest.score}</span>
            </div>
          </div>
        </div>

        <p className="mt-2 text-center text-[10px] text-muted-foreground/60">
          Расчёт по эссенциальному достоинству, дому и аспектам. Наведи на планету для деталей.
        </p>
      </div>
    </section>
  )
}
