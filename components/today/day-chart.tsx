"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

/**
 * DayChart — circular SVG visualization of the 12-house astrological wheel
 * with planet positions for the current day.
 *
 * Data is derived from lib/demo-data.ts DEMO_NATAL_RESPONSE (planets + houses)
 * rotated to "today" for the demo. In production this would come from the
 * SolarSage sidecar's transit calculation.
 */

export interface ChartPlanet {
  name: string
  symbol: string
  sign: string
  signSymbol: string
  longitude: number // 0-360 absolute ecliptic longitude
  house: number
}

export interface ChartHouse {
  number: number
  cusp: number // 0-360
  sign: string
  signSymbol: string
}

const SIGN_SYMBOLS: Record<string, string> = {
  Aries: "♈",
  Taurus: "♉",
  Gemini: "♊",
  Cancer: "♋",
  Leo: "♌",
  Virgo: "♍",
  Libra: "♎",
  Scorpio: "♏",
  Sagittarius: "♐",
  Capricorn: "♑",
  Aquarius: "♒",
  Pisces: "♓",
}

const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉",
  Moon: "☽",
  Mercury: "☿",
  Venus: "♀",
  Mars: "♂",
  Jupiter: "♃",
  Saturn: "♄",
  Uranus: "♅",
  Neptune: "♆",
  Pluto: "♇",
}

const PLANET_COLORS: Record<string, string> = {
  Sun: "oklch(0.72 0.15 60)",
  Moon: "oklch(0.82 0.03 295)",
  Mercury: "oklch(0.62 0.08 230)",
  Venus: "oklch(0.70 0.12 15)",
  Mars: "oklch(0.58 0.18 27)",
  Jupiter: "oklch(0.70 0.13 85)",
  Saturn: "oklch(0.55 0.05 260)",
  Uranus: "oklch(0.68 0.10 200)",
  Neptune: "oklch(0.62 0.10 270)",
  Pluto: "oklch(0.45 0.08 300)",
}

const ZODIAC_ORDER = [
  "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
  "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

function signSymbol(sign: string): string {
  return SIGN_SYMBOLS[sign] ?? "?"
}

function planetSymbol(name: string): string {
  return PLANET_SYMBOLS[name] ?? "•"
}

function planetColor(name: string): string {
  return PLANET_COLORS[name] ?? "oklch(0.55 0.05 295)"
}

// Convert ecliptic longitude (0-360, Aries 0°) to SVG angle.
// Astrologically 0° Aries is at the 9 o'clock position (ASC = left = east).
// We rotate clockwise: 0° → left, 90° → top, 180° → right, 270° → bottom.
function longitudeToAngle(lon: number): number {
  // In an astrological chart, 0° Aries is at the 9 o'clock (left) and degrees
  // go counter-clockwise. For SVG (which is clockwise from 3 o'clock) we need
  // to flip: angle = 180 - lon.
  return 180 - (lon % 360)
}

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  // angle measured clockwise from 3 o'clock (SVG convention)
  const rad = (angleDeg * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function describeArc(
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number
): string {
  const start = polarToCartesian(cx, cy, r, endAngle)
  const end = polarToCartesian(cx, cy, r, startAngle)
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1"
  return [
    "M", start.x, start.y,
    "A", r, r, 0, largeArcFlag, 0, end.x, end.y,
  ].join(" ")
}

interface DayChartProps {
  planets: ChartPlanet[]
  houses: ChartHouse[]
  /** Optional: date label rendered in the center */
  dateLabel?: string
  /** Optional: day status for center accent color */
  dayStatus?: "steady" | "supportive" | "tense"
}

const STATUS_ACCENT: Record<string, string> = {
  steady: "oklch(0.62 0.06 305)",
  supportive: "oklch(0.68 0.12 150)",
  tense: "oklch(0.58 0.14 27)",
}

// Chart geometry constants (module-level so useMemo deps are stable)
const SIZE = 320
const C = SIZE / 2 // center
const R_OUTER = 152 // outer zodiac ring
const R_HOUSE = 124 // house ring outer
const R_HOUSE_INNER = 96 // house ring inner
const R_PLANET = 78 // planet ring radius
const R_CENTER = 52 // center disk

export function DayChart({
  planets,
  houses,
  dateLabel,
  dayStatus = "steady",
}: DayChartProps) {
  const [selected, setSelected] = useState<ChartPlanet | null>(null)

  // 12 zodiac slices (30° each, starting from 0° Aries at the left/9-o'clock)
  const zodiacSlices = useMemo(
    () =>
      ZODIAC_ORDER.map((sign, i) => {
        const startLon = i * 30
        const endLon = (i + 1) * 30
        const startAngle = longitudeToAngle(startLon)
        const endAngle = longitudeToAngle(endLon)
        return {
          sign,
          symbol: signSymbol(sign),
          startAngle,
          endAngle,
          // midpoint angle for the label
          midAngle: (startAngle + endAngle) / 2,
        }
      }),
    []
  )

  // House cusps: convert each house cusp longitude to an angle.
  // Houses are drawn as spokes from inner to outer ring.
  const houseSpokes = useMemo(() => {
    return houses.map((h) => {
      const angle = longitudeToAngle(h.cusp)
      const outer = polarToCartesian(C, C, R_HOUSE, angle)
      const inner = polarToCartesian(C, C, R_HOUSE_INNER, angle)
      return { ...h, angle, outer, inner }
    })
  }, [houses])

  // Planet positions on the planet ring, with collision-avoidance offset.
  const planetPoints = useMemo(() => {
    // Sort by longitude so neighbours are adjacent
    const sorted = [...planets].sort((a, b) => a.longitude - b.longitude)
    // If two planets are within 6° of each other, offset them radially.
    const points = sorted.map((p) => {
      const angle = longitudeToAngle(p.longitude)
      const pos = polarToCartesian(C, C, R_PLANET, angle)
      return { ...p, angle, x: pos.x, y: pos.y, offset: 0 }
    })
    for (let i = 0; i < points.length; i++) {
      const next = points[(i + 1) % points.length]
      const diff = Math.abs(((points[i].angle - next.angle + 540) % 360) - 180)
      if (diff < 8) {
        next.offset = 14 // push the second one slightly outward
        const pos = polarToCartesian(C, C, R_PLANET + next.offset, next.angle)
        next.x = pos.x
        next.y = pos.y
      }
    }
    return points
  }, [planets])

  return (
    <div className="relative flex flex-col items-center">
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="chart-svg-root h-auto w-full max-w-[340px]"
        role="img"
        aria-label="Карта дня — астрологическая карта с положениями планет"
      >
        {/* outer faint glow */}
        <defs>
          <radialGradient id="chart-bg-grad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="oklch(0.99 0.01 305)" />
            <stop offset="70%" stopColor="oklch(0.97 0.012 305)" />
            <stop offset="100%" stopColor="oklch(0.94 0.015 305)" />
          </radialGradient>
          <radialGradient id="chart-center-grad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={STATUS_ACCENT[dayStatus]} stopOpacity="0.12" />
            <stop offset="100%" stopColor={STATUS_ACCENT[dayStatus]} stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* background disk */}
        <circle cx={C} cy={C} r={R_OUTER + 4} fill="url(#chart-bg-grad)" stroke="oklch(0.88 0.01 295)" strokeWidth={0.5} />

        {/* zodiac ring slices (alternating tint) */}
        {zodiacSlices.map((s, i) => {
          const path = describeArc(C, C, R_OUTER, s.startAngle, s.endAngle)
          const innerPath = describeArc(C, C, R_HOUSE, s.startAngle, s.endAngle)
          const labelPos = polarToCartesian(C, C, (R_OUTER + R_HOUSE) / 2, s.midAngle)
          return (
            <g key={s.sign}>
              <path
                d={`${path} L ${polarToCartesian(C, C, R_HOUSE, s.endAngle).x} ${polarToCartesian(C, C, R_HOUSE, s.endAngle).y} ${innerPath.split("M")[1].replace("A", "A").replace(" 0 0 0 ", " 0 0 1 ")} Z`}
                fill={i % 2 === 0 ? "oklch(0.96 0.012 305)" : "oklch(0.98 0.008 305)"}
                stroke="oklch(0.88 0.01 295)"
                strokeWidth={0.4}
              />
              <text
                x={labelPos.x}
                y={labelPos.y}
                fontSize={13}
                fill="oklch(0.45 0.04 295)"
                textAnchor="middle"
                dominantBaseline="central"
                className="select-none"
              >
                {s.symbol}
              </text>
            </g>
          )
        })}

        {/* house ring (between R_HOUSE_INNER and R_HOUSE) */}
        <circle cx={C} cy={C} r={R_HOUSE} fill="none" stroke="oklch(0.82 0.01 295)" strokeWidth={0.5} />
        <circle cx={C} cy={C} r={R_HOUSE_INNER} fill="none" stroke="oklch(0.82 0.01 295)" strokeWidth={0.5} />

        {/* house spokes + numbers */}
        {houseSpokes.map((h) => (
          <g key={h.number}>
            <line
              x1={h.inner.x} y1={h.inner.y}
              x2={h.outer.x} y2={h.outer.y}
              stroke="oklch(0.78 0.015 295)"
              strokeWidth={0.5}
              strokeDasharray={h.number === 1 ? "none" : "2 2"}
            />
            {h.number === 1 && (
              <line
                x1={h.inner.x} y1={h.inner.y}
                x2={h.outer.x} y2={h.outer.y}
                stroke="oklch(0.55 0.06 305)"
                strokeWidth={1.2}
              />
            )}
          </g>
        ))}

        {/* house numbers (placed just inside the inner ring) */}
        {houseSpokes.map((h, i) => {
          const next = houseSpokes[(i + 1) % houseSpokes.length]
          const midLon = (h.cusp + next.cusp) / 2
          const midAngle = longitudeToAngle(midLon)
          const pos = polarToCartesian(C, C, (R_HOUSE + R_HOUSE_INNER) / 2, midAngle)
          return (
            <text
              key={`hn-${h.number}`}
              x={pos.x}
              y={pos.y}
              fontSize={10}
              fontWeight={600}
              fill={h.number === 1 ? "oklch(0.48 0.06 305)" : "oklch(0.58 0.02 295)"}
              textAnchor="middle"
              dominantBaseline="central"
              className="select-none"
            >
              {h.number}
            </text>
          )
        })}

        {/* center disk */}
        <circle cx={C} cy={C} r={R_CENTER} fill="url(#chart-center-grad)" stroke="oklch(0.78 0.015 295)" strokeWidth={0.5} data-chart-center />
        <circle cx={C} cy={C} r={R_CENTER - 6} fill="none" stroke="oklch(0.85 0.01 295)" strokeWidth={0.4} strokeDasharray="1 3" />

        {/* center label */}
        {dateLabel && (
          <text
            x={C}
            y={C - 4}
            fontSize={11}
            fontWeight={600}
            fill="oklch(0.42 0.04 295)"
            textAnchor="middle"
            dominantBaseline="central"
            className="select-none"
          >
            {dateLabel}
          </text>
        )}
        <text
          x={C}
          y={C + 10}
          fontSize={8}
          letterSpacing={1.5}
          fill="oklch(0.55 0.02 295)"
          textAnchor="middle"
          dominantBaseline="central"
          className="select-none uppercase"
        >
          карта дня
        </text>

        {/* aspect lines (simple: connect planets that are in close aspect) */}
        {planetPoints.map((p, i) =>
          planetPoints.slice(i + 1).map((q, j) => {
            const diff = Math.abs(p.longitude - q.longitude)
            const norm = Math.min(diff, 360 - diff)
            // major orbs: conjunction 8, opposition 8, trine 6, square 7, sextile 6
            let color: string | null = null
            if (norm <= 8) color = "oklch(0.55 0.06 305)" // conjunction - plum
            else if (Math.abs(norm - 180) <= 8) color = "oklch(0.55 0.14 27)" // opposition - red
            else if (Math.abs(norm - 120) <= 6) color = "oklch(0.60 0.10 150)" // trine - green
            else if (Math.abs(norm - 90) <= 7) color = "oklch(0.60 0.12 60)" // square - amber
            else if (Math.abs(norm - 60) <= 6) color = "oklch(0.60 0.08 230)" // sextile - blue
            if (!color) return null
            return (
              <line
                key={`asp-${i}-${j}`}
                x1={p.x} y1={p.y}
                x2={q.x} y2={q.y}
                stroke={color}
                strokeWidth={0.6}
                strokeOpacity={0.5}
              />
            )
          })
        )}

        {/* planets */}
        {planetPoints.map((p) => {
          const color = planetColor(p.name)
          const isSel = selected?.name === p.name
          return (
            <g
              key={p.name}
              className="cursor-pointer"
              onClick={() => setSelected(isSel ? null : p)}
            >
              {/* hit area */}
              <circle cx={p.x} cy={p.y} r={13} fill="transparent" />
              {/* planet disk */}
              <motion.circle
                cx={p.x} cy={p.y}
                r={isSel ? 11 : 9}
                fill="oklch(0.99 0.005 305)"
                stroke={color}
                strokeWidth={isSel ? 2 : 1.4}
                initial={false}
                animate={{ scale: isSel ? 1.1 : 1 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                style={{ transformOrigin: `${p.x}px ${p.y}px` }}
              />
              <text
                x={p.x}
                y={p.y}
                fontSize={12}
                fontWeight={600}
                fill={color}
                textAnchor="middle"
                dominantBaseline="central"
                className="select-none pointer-events-none"
              >
                {planetSymbol(p.name)}
              </text>
            </g>
          )
        })}
      </svg>

      {/* planet detail popover */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0, y: 8, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: 8, height: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-2 w-full max-w-[340px] overflow-hidden rounded-lg border border-border/70 bg-card/80 px-3.5 py-2.5 backdrop-blur"
          >
            <div className="flex items-center gap-2.5">
              <span
                className="flex h-8 w-8 items-center justify-center rounded-full text-base font-semibold"
                style={{
                  color: planetColor(selected.name),
                  background: `${planetColor(selected.name)}1a`,
                }}
              >
                {planetSymbol(selected.name)}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-medium text-foreground">{selected.name}</span>
                  <span className="text-[11px] text-muted-foreground">
                    {selected.signSymbol} {selected.sign} · {selected.house} дом
                  </span>
                </div>
                <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                  {planetDescription(selected.name, selected.house)}
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* legend */}
      <div className="mt-3 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-1.5 w-3 rounded-full" style={{ background: "oklch(0.55 0.06 305)" }} />
          соединение
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-1.5 w-3 rounded-full" style={{ background: "oklch(0.55 0.14 27)" }} />
          оппозиция
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-1.5 w-3 rounded-full" style={{ background: "oklch(0.60 0.10 150)" }} />
          тригон
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-1.5 w-3 rounded-full" style={{ background: "oklch(0.60 0.12 60)" }} />
          квадратура
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-1.5 w-3 rounded-full" style={{ background: "oklch(0.60 0.08 230)" }} />
          секстиль
        </span>
      </div>
    </div>
  )
}

function planetDescription(name: string, house: number): string {
  const houseThemes: Record<number, string> = {
    1: "личность и самовыражение",
    2: "ценности и ресурсы",
    3: "общение и ближние поездки",
    4: "дом и семья",
    5: "творчество и романтика",
    6: "работа и здоровье",
    7: "партнёрство",
    8: "трансформация и общие ресурсы",
    9: "мировоззрение и дальние поездки",
    10: "карьера и статус",
    11: "друзья и цели",
    12: "внутренний мир и уединение",
  }
  const planetThemes: Record<string, string> = {
    Sun: "Я-энергия, воля, сознание",
    Moon: "эмоции, инстинкты, подсознание",
    Mercury: "мышление, общение, обучение",
    Venus: "любовь, удовольствие, ценности",
    Mars: "действие, страсть, инициатива",
    Jupiter: "рост, удача, мудрость",
    Saturn: "дисциплина, ответственность, ограничения",
    Uranus: "перемены, озарения, свобода",
    Neptune: "мечты, иллюзии, духовность",
    Pluto: "трансформация, власть, глубина",
  }
  const pt = planetThemes[name] ?? ""
  const ht = houseThemes[house] ?? ""
  return `${pt}. Сегодня акцент через ${house} дом — ${ht}.`
}
