"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Clock, MapPin } from "lucide-react"

/**
 * HoraryChart — visualization of the horary moment (the astrological
 * chart for the instant the question was asked).
 *
 * In real horary astrology, the chart is cast for the time and place
 * the astrologer receives and understands the question. Here we derive
 * a deterministic chart from the question's `createdAt` timestamp so
 * each question gets a stable, unique chart.
 *
 * Houses are derived from the timestamp (sidereal time approximation),
 * and planets are positioned by a simplified ephemeris keyed to the
 * J2000 epoch.
 */

interface HoraryChartProps {
  /** ISO timestamp of the question moment */
  createdAt: string
  /** Optional: location name where the question was asked */
  locationName?: string | null
  /** Planets involved in the horary judgment (highlighted) */
  involvedPlanets?: string[]
}

const SIGN_SYMBOLS: Record<string, string> = {
  Aries: "♈", Taurus: "♉", Gemini: "♊", Cancer: "♋", Leo: "♌", Virgo: "♍",
  Libra: "♎", Scorpio: "♏", Sagittarius: "♐", Capricorn: "♑", Aquarius: "♒", Pisces: "♓",
}

const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
  Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
}

const PLANET_COLORS: Record<string, string> = {
  Sun: "oklch(0.72 0.15 60)",
  Moon: "oklch(0.62 0.04 295)",
  Mercury: "oklch(0.62 0.08 230)",
  Venus: "oklch(0.70 0.12 15)",
  Mars: "oklch(0.58 0.18 27)",
  Jupiter: "oklch(0.70 0.13 85)",
  Saturn: "oklch(0.55 0.05 260)",
  Uranus: "oklch(0.68 0.10 200)",
  Neptune: "oklch(0.62 0.10 270)",
  Pluto: "oklch(0.45 0.08 300)",
}

const PLANET_RU: Record<string, string> = {
  Sun: "Солнце", Moon: "Луна", Mercury: "Меркурий", Venus: "Венера",
  Mars: "Марс", Jupiter: "Юпитер", Saturn: "Сатурн",
  Uranus: "Уран", Neptune: "Нептун", Pluto: "Плутон",
}

const SIGN_RU: Record<string, string> = {
  Aries: "Овен", Taurus: "Телец", Gemini: "Близнецы", Cancer: "Рак",
  Leo: "Лев", Virgo: "Дева", Libra: "Весы", Scorpio: "Скорпион",
  Sagittarius: "Стрелец", Capricorn: "Козерог", Aquarius: "Водолей", Pisces: "Рыбы",
}

const ZODIAC_ORDER = [
  "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
  "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

// Module-level geometry constants
const SIZE = 300
const C = SIZE / 2
const R_OUTER = 142
const R_ZODIAC_INNER = 118
const R_HOUSE = 110
const R_HOUSE_INNER = 84
const R_PLANET = 68
const R_CENTER = 44

function longitudeToAngle(lon: number): number {
  return 180 - (lon % 360)
}

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = (angleDeg * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number): string {
  const start = polarToCartesian(cx, cy, r, endAngle)
  const end = polarToCartesian(cx, cy, r, startAngle)
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1"
  return ["M", start.x, start.y, "A", r, r, 0, largeArcFlag, 0, end.x, end.y].join(" ")
}

/**
 * Derive planet longitudes from a timestamp.
 * Uses simplified mean motions from J2000 epoch — visually plausible,
 * not ephemeris-accurate. Good enough for a demo horary chart.
 */
function derivePlanets(timestamp: number): { name: string; sign: string; longitude: number }[] {
  const J2000 = Date.UTC(2000, 0, 1, 12, 0, 0)
  const daysSinceJ2000 = (timestamp - J2000) / 86400000

  // Mean daily motion in degrees/day (simplified)
  const motions: Record<string, number> = {
    Sun: 0.9856,
    Moon: 13.1764,
    Mercury: 1.3833,
    Venus: 0.5240,
    Mars: 0.5240,
    Jupiter: 0.0831,
    Saturn: 0.0335,
    Uranus: 0.0117,
    Neptune: 0.0060,
    Pluto: 0.0040,
  }

  // Initial longitudes at J2000 (approximate, degrees)
  const initial: Record<string, number> = {
    Sun: 280,
    Moon: 218,
    Mercury: 252,
    Venus: 181,
    Mars: 355,
    Jupiter: 34,
    Saturn: 50,
    Uranus: 314,
    Neptune: 304,
    Pluto: 247,
  }

  return Object.entries(motions).map(([name, motion]) => {
    const lon = (initial[name] + daysSinceJ2000 * motion) % 360
    const signIdx = Math.floor(lon / 30)
    return {
      name,
      sign: ZODIAC_ORDER[signIdx],
      longitude: lon,
    }
  })
}

/**
 * Derive house cusps from a timestamp.
 * Uses a simplified Placidus approximation: the ASC is derived from
 * the sidereal time (which is a function of the timestamp), and the
 * other cusps are spaced at 30° intervals (equal house system for
 * simplicity in the demo).
 */
function deriveHouses(timestamp: number): { number: number; cusp: number; sign: string }[] {
  // Sidereal time approximation: GST = 18.697374558 + 24.06570982441908 * D
  // where D = days since J2000
  const J2000 = Date.UTC(2000, 0, 1, 12, 0, 0)
  const daysSinceJ2000 = (timestamp - J2000) / 86400000
  const gstHours = (18.697374558 + 24.06570982441908 * daysSinceJ2000) % 24
  const gstDegrees = gstHours * 15 // 1 hour = 15°

  // ASC ~ GST + 90° (simplified — real ASC depends on latitude)
  const ascLongitude = (gstDegrees + 90) % 360

  // Equal house: 12 cusps at 30° intervals from ASC
  return Array.from({ length: 12 }, (_, i) => {
    const cusp = (ascLongitude + i * 30) % 360
    const signIdx = Math.floor(cusp / 30)
    return {
      number: i + 1,
      cusp,
      sign: ZODIAC_ORDER[signIdx],
    }
  })
}

function formatTimeLabel(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleString("ru-RU", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    })
  } catch {
    return ""
  }
}

export function HoraryChart({ createdAt, locationName, involvedPlanets = [] }: HoraryChartProps) {
  const [selected, setSelected] = useState<string | null>(null)
  const ts = new Date(createdAt).getTime()

  const planets = useMemo(() => derivePlanets(ts), [ts])
  const houses = useMemo(() => deriveHouses(ts), [ts])

  const zodiacSlices = useMemo(
    () =>
      ZODIAC_ORDER.map((sign, i) => {
        const startLon = i * 30
        const endLon = (i + 1) * 30
        return {
          sign,
          symbol: SIGN_SYMBOLS[sign],
          startAngle: longitudeToAngle(startLon),
          endAngle: longitudeToAngle(endLon),
          midAngle: longitudeToAngle(startLon + 15),
        }
      }),
    []
  )

  const houseSpokes = useMemo(
    () =>
      houses.map((h) => {
        const angle = longitudeToAngle(h.cusp)
        return {
          ...h,
          angle,
          outer: polarToCartesian(C, C, R_HOUSE, angle),
          inner: polarToCartesian(C, C, R_HOUSE_INNER, angle),
        }
      }),
    [houses]
  )

  const planetPoints = useMemo(() => {
    const involved = new Set(involvedPlanets)
    const sorted = [...planets].sort((a, b) => a.longitude - b.longitude)
    const points = sorted.map((p) => {
      const angle = longitudeToAngle(p.longitude)
      const pos = polarToCartesian(C, C, R_PLANET, angle)
      return { ...p, angle, x: pos.x, y: pos.y, offset: 0, isInvolved: involved.has(p.name) }
    })
    for (let i = 0; i < points.length; i++) {
      const next = points[(i + 1) % points.length]
      const diff = Math.abs(((points[i].angle - next.angle + 540) % 360) - 180)
      if (diff < 7) {
        next.offset = 14
        const pos = polarToCartesian(C, C, R_PLANET + next.offset, next.angle)
        next.x = pos.x
        next.y = pos.y
      }
    }
    return points
  }, [planets, involvedPlanets])

  const selectedPlanet = selected ? planetPoints.find((p) => p.name === selected) : null

  return (
    <section className="px-5" aria-label="Карта момента вопроса">
      <div className="rounded-2xl border border-border/50 bg-gradient-to-br from-card via-card to-secondary/20 p-4">
        {/* Header */}
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="h-3.5 w-3.5 text-primary" strokeWidth={1.75} />
            <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Карта момента
            </h3>
          </div>
          <span className="text-[10px] text-muted-foreground/70">
            {formatTimeLabel(createdAt)}
          </span>
        </div>

        {locationName && (
          <div className="mb-2 flex items-center gap-1 text-[10px] text-muted-foreground">
            <MapPin className="h-2.5 w-2.5" strokeWidth={1.75} />
            <span>{locationName}</span>
          </div>
        )}

        <svg
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          className="chart-svg-root h-auto w-full"
          role="img"
          aria-label="Хорарная карта — положение планет на момент вопроса"
        >
          <defs>
            <radialGradient id="horary-bg-grad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="oklch(0.99 0.008 305)" />
              <stop offset="100%" stopColor="oklch(0.94 0.015 305)" />
            </radialGradient>
            <radialGradient id="horary-center-grad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="oklch(0.48 0.06 305 / 0.16)" />
              <stop offset="100%" stopColor="oklch(0.48 0.06 305 / 0)" />
            </radialGradient>
          </defs>

          <circle cx={C} cy={C} r={R_OUTER + 4} fill="url(#horary-bg-grad)" stroke="oklch(0.88 0.01 295)" strokeWidth={0.5} />

          {/* Zodiac ring */}
          {zodiacSlices.map((s, i) => {
            const labelPos = polarToCartesian(C, C, (R_OUTER + R_ZODIAC_INNER) / 2, s.midAngle)
            return (
              <g key={s.sign}>
                <path
                  d={`${describeArc(C, C, R_OUTER, s.startAngle, s.endAngle)} L ${polarToCartesian(C, C, R_ZODIAC_INNER, s.endAngle).x} ${polarToCartesian(C, C, R_ZODIAC_INNER, s.endAngle).y} ${describeArc(C, C, R_ZODIAC_INNER, s.endAngle, s.startAngle).replace("M", "L")} Z`}
                  fill={i % 2 === 0 ? "oklch(0.96 0.012 305)" : "oklch(0.98 0.008 305)"}
                  stroke="oklch(0.88 0.01 295)"
                  strokeWidth={0.4}
                />
                <text x={labelPos.x} y={labelPos.y} fontSize={12} fill="oklch(0.45 0.04 295)" textAnchor="middle" dominantBaseline="central" className="select-none">
                  {s.symbol}
                </text>
              </g>
            )
          })}

          {/* House ring */}
          <circle cx={C} cy={C} r={R_HOUSE} fill="none" stroke="oklch(0.82 0.01 295)" strokeWidth={0.5} />
          <circle cx={C} cy={C} r={R_HOUSE_INNER} fill="none" stroke="oklch(0.82 0.01 295)" strokeWidth={0.5} />

          {/* House spokes — 1st house (ASC) highlighted */}
          {houseSpokes.map((h) => (
            <line
              key={h.number}
              x1={h.inner.x} y1={h.inner.y}
              x2={h.outer.x} y2={h.outer.y}
              stroke={h.number === 1 ? "oklch(0.55 0.06 305)" : "oklch(0.78 0.015 295)"}
              strokeWidth={h.number === 1 ? 1.4 : 0.5}
              strokeDasharray={h.number === 1 ? "none" : "2 2"}
            />
          ))}

          {/* House numbers */}
          {houseSpokes.map((h, i) => {
            const next = houseSpokes[(i + 1) % houseSpokes.length]
            const midLon = (h.cusp + next.cusp) / 2
            const midAngle = longitudeToAngle(midLon)
            const pos = polarToCartesian(C, C, (R_HOUSE + R_HOUSE_INNER) / 2, midAngle)
            return (
              <text key={`hn-${h.number}`} x={pos.x} y={pos.y} fontSize={9} fontWeight={h.number === 1 ? 700 : 500} fill={h.number === 1 ? "oklch(0.48 0.06 305)" : "oklch(0.58 0.02 295)"} textAnchor="middle" dominantBaseline="central" className="select-none">
                {h.number}
              </text>
            )
          })}

          {/* Center disk */}
          <circle cx={C} cy={C} r={R_CENTER} fill="url(#horary-center-grad)" stroke="oklch(0.78 0.015 295)" strokeWidth={0.5} data-chart-center />
          <text x={C} y={C - 4} fontSize={8} letterSpacing={1} fill="oklch(0.55 0.02 295)" textAnchor="middle" dominantBaseline="central" className="select-none uppercase">
            хорар
          </text>
          <text x={C} y={C + 7} fontSize={7} fill="oklch(0.6 0.02 295)" textAnchor="middle" dominantBaseline="central" className="select-none">
            момент
          </text>

          {/* Aspect lines between involved planets only */}
          {planetPoints.filter((p) => p.isInvolved).map((p, i, arr) =>
            arr.slice(i + 1).map((q, j) => {
              const diff = Math.abs(p.longitude - q.longitude)
              const norm = Math.min(diff, 360 - diff)
              let color: string | null = null
              if (norm <= 8) color = "oklch(0.55 0.06 305)"
              else if (Math.abs(norm - 180) <= 8) color = "oklch(0.55 0.14 27)"
              else if (Math.abs(norm - 120) <= 7) color = "oklch(0.60 0.10 150)"
              else if (Math.abs(norm - 90) <= 7) color = "oklch(0.60 0.12 60)"
              else if (Math.abs(norm - 60) <= 6) color = "oklch(0.60 0.08 230)"
              if (!color) return null
              return (
                <line key={`asp-${i}-${j}`} x1={p.x} y1={p.y} x2={q.x} y2={q.y} stroke={color} strokeWidth={0.7} strokeOpacity={0.5} />
              )
            })
          )}

          {/* Planets — involved ones highlighted */}
          {planetPoints.map((p) => {
            const color = PLANET_COLORS[p.name]
            const isSel = selected === p.name
            const isInvolved = p.isInvolved
            return (
              <g key={p.name} className="cursor-pointer" onClick={() => setSelected(isSel ? null : p.name)}>
                <circle cx={p.x} cy={p.y} r={12} fill="transparent" />
                <motion.circle
                  cx={p.x} cy={p.y}
                  r={isSel ? 11 : isInvolved ? 10 : 8}
                  fill={isInvolved ? color : "oklch(0.99 0.005 305)"}
                  stroke={color}
                  strokeWidth={isInvolved ? 0 : isSel ? 2 : 1.2}
                  initial={false}
                  animate={{ scale: isSel ? 1.1 : 1 }}
                  transition={{ type: "spring", stiffness: 300, damping: 20 }}
                  style={{ transformOrigin: `${p.x}px ${p.y}px` }}
                />
                <text
                  x={p.x} y={p.y}
                  fontSize={11}
                  fontWeight={600}
                  fill={isInvolved ? "oklch(0.99 0.005 305)" : color}
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="select-none pointer-events-none"
                >
                  {PLANET_SYMBOLS[p.name]}
                </text>
                {/* Involved planet ring */}
                {isInvolved && !isSel && (
                  <circle cx={p.x} cy={p.y} r={13} fill="none" stroke={color} strokeWidth={0.8} strokeOpacity={0.4} strokeDasharray="2 2" />
                )}
              </g>
            )
          })}
        </svg>

        {/* Planet detail popover */}
        <AnimatePresence>
          {selectedPlanet && (
            <motion.div
              initial={{ opacity: 0, y: 8, height: 0 }}
              animate={{ opacity: 1, y: 0, height: "auto" }}
              exit={{ opacity: 0, y: 8, height: 0 }}
              transition={{ duration: 0.2 }}
              className="mt-2 overflow-hidden rounded-lg border border-border/70 bg-card/80 px-3.5 py-2.5 backdrop-blur"
            >
              <div className="flex items-center gap-2.5">
                <span
                  className="flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold"
                  style={{ color: PLANET_COLORS[selectedPlanet.name], background: `${PLANET_COLORS[selectedPlanet.name]}1a` }}
                >
                  {PLANET_SYMBOLS[selectedPlanet.name]}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-sm font-medium text-foreground">
                      {PLANET_RU[selectedPlanet.name] ?? selectedPlanet.name}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      {SIGN_SYMBOLS[selectedPlanet.sign]} {SIGN_RU[selectedPlanet.sign]}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[11px] tabular-nums text-muted-foreground">
                    {Math.floor(selectedPlanet.longitude % 30)}°{Math.floor((selectedPlanet.longitude % 1) * 60)}′ · {selectedPlanet.longitude.toFixed(1)}°
                    {selectedPlanet.isInvolved && (
                      <span className="ml-1.5 text-primary">· задействован в ответе</span>
                    )}
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Legend */}
        <div className="mt-2.5 flex items-center justify-center gap-3 text-[9px] text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-primary" />
            задействован
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full border border-primary" />
            фон
          </span>
          <span>ASC — 1 дом</span>
        </div>
      </div>
    </section>
  )
}
