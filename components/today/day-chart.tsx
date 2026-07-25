// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_DAY_CHART
// ROLE: Interactive astronomical day chart wheel component for Today screen.
// DEPENDENCIES: react, framer-motion, lib/contracts/today
// GRACE_ANCHORS: [DAY_CHART_COMPONENT]
// SLICE: SLICE-TODAY-CALENDAR
// ############################################################################

// START_MODULE_CONTRACT: M-COMPONENTS-DAY-CHART
// purpose: Render interactive day astrological chart wheel with planetary positions and house cusps.
// owns:
//   - components/today/day-chart.tsx
// inputs: chart (DayChartData | null), dateLabel, dayStatus
// outputs: DayChart React component
// dependencies: lib/contracts/today
// side_effects: none (pure SVG/canvas calculation and rendering)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-COMPONENTS-DAY-CHART

// START_MODULE_MAP: M-COMPONENTS-DAY-CHART
// public_entrypoints:
//   - DayChart
// semantic_blocks:
//   - DAY_CHART_COMPONENT: main day chart wheel SVG component
// owned_tests:
//   - __tests__/components/TodayScreen.test.tsx
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP: M-COMPONENTS-DAY-CHART

"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import type { DayChart as DayChartData, DayStatus } from "@/lib/contracts/today"

type Props = {
  chart: DayChartData | null
  dateLabel?: string
  dayStatus?: DayStatus
}

interface ChartPlanet {
  name: string
  symbol: string
  sign: string
  signSymbol: string
  longitude: number
  house: number
  interpretation?: string | null
}

interface ChartHouse {
  number: number
  cusp: number
  sign: string
  signSymbol: string
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

const SIGN_PREPOSITIONAL: Record<string, string> = {
  Aries: "Овне", Taurus: "Тельце", Gemini: "Близнецах", Cancer: "Раке", Leo: "Льве", Virgo: "Деве",
  Libra: "Весах", Scorpio: "Скорпионе", Sagittarius: "Стрельце", Capricorn: "Козероге", Aquarius: "Водолее", Pisces: "Рыбах",
}

const STATUS_ACCENT: Record<string, string> = {
  steady: "oklch(0.62 0.06 305)",
  supportive: "oklch(0.68 0.12 150)",
  tense: "oklch(0.58 0.14 27)",
}

const ASPECT_COLOR: Record<string, string> = {
  conjunction: "oklch(0.55 0.06 305)",
  opposition: "oklch(0.55 0.14 27)",
  trine: "oklch(0.60 0.10 150)",
  square: "oklch(0.60 0.12 60)",
  sextile: "oklch(0.60 0.08 230)",
}

const SIZE = 320
const C = SIZE / 2
const R_OUTER = 152
const R_HOUSE = 124
const R_HOUSE_INNER = 96
const R_PLANET = 78
const R_CENTER = 52

function longitudeToAngle(lon: number): number {
  return 180 - (lon % 360)
}

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
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

// START_BLOCK: DAY_CHART_COMPONENT
export function DayChart({ chart, dateLabel, dayStatus = "steady" }: Props) {
  const [selectedPlanet, setSelectedPlanet] = useState<string | null>(null)

  const planetsConverted = useMemo((): ChartPlanet[] => {
    if (!chart) return []
    return chart.transitPlanets.map((p) => ({
      name: p.name,
      symbol: PLANET_SYMBOLS[p.name] ?? "•",
      sign: p.sign || "",
      signSymbol: p.sign ? (SIGN_SYMBOLS[p.sign] || "") : "",
      longitude: p.longitude,
      house: p.house || 1,
      interpretation: p.interpretation,
    }))
  }, [chart])

  const housesConverted = useMemo((): ChartHouse[] => {
    if (!chart) return []
    return chart.houses.map((h) => ({
      number: h.number,
      cusp: h.cuspLongitude,
      sign: h.sign || "",
      signSymbol: h.sign ? (SIGN_SYMBOLS[h.sign] || "") : "",
    }))
  }, [chart])

  const zodiacSlices = useMemo(
    () =>
      ZODIAC_ORDER.map((sign, i) => {
        const startLon = i * 30
        const endLon = (i + 1) * 30
        const startAngle = longitudeToAngle(startLon)
        const endAngle = longitudeToAngle(endLon)
        return {
          sign,
          symbol: SIGN_SYMBOLS[sign] ?? "?",
          startAngle,
          endAngle,
          midAngle: (startAngle + endAngle) / 2,
        }
      }),
    []
  )

  const houseSpokes = useMemo(() => {
    return housesConverted.map((h) => {
      const angle = longitudeToAngle(h.cusp)
      const outer = polarToCartesian(C, C, R_HOUSE, angle)
      const inner = polarToCartesian(C, C, R_HOUSE_INNER, angle)
      return { ...h, angle, outer, inner }
    })
  }, [housesConverted])

  const planetPoints = useMemo(() => {
    const sorted = [...planetsConverted].sort((a, b) => a.longitude - b.longitude)
    const points = sorted.map((p) => {
      const angle = longitudeToAngle(p.longitude)
      const pos = polarToCartesian(C, C, R_PLANET, angle)
      return { ...p, angle, x: pos.x, y: pos.y, offset: 0 }
    })
    for (let i = 0; i < points.length; i++) {
      const next = points[(i + 1) % points.length]
      const diff = Math.abs(((points[i].angle - next.angle + 540) % 360) - 180)
      if (diff < 8) {
        next.offset = 14
        const pos = polarToCartesian(C, C, R_PLANET + next.offset, next.angle)
        next.x = pos.x
        next.y = pos.y
      }
    }
    return points
  }, [planetsConverted])

  const selected = selectedPlanet ? planetsConverted.find((p) => p.name === selectedPlanet) ?? null : null

  if (!chart || chart.transitPlanets.length === 0) {
    return (
      <section className="mx-5 rounded-lg border border-border/60 bg-card/60 px-4 py-6 text-center" data-testid="day-chart-unavailable">
        <p className="text-sm font-medium text-foreground">Карта дня недоступна</p>
        <p className="mt-1 text-xs text-muted-foreground">Расчёт не пришёл от сервера.</p>
      </section>
    )
  }

  return (
    <div className="relative flex flex-col items-center" data-testid="day-chart">
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="chart-svg-root h-auto w-full max-w-[340px]"
        role="img"
        aria-label="Карта дня — астрологическая карта с положениями планет"
      >
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

        {/* house ring */}
        <circle cx={C} cy={C} r={R_HOUSE} fill="none" stroke="oklch(0.82 0.01 295)" strokeWidth={0.5} />
        <circle cx={C} cy={C} r={R_HOUSE_INNER} fill="none" stroke="oklch(0.82 0.01 295)" strokeWidth={0.5} />

        {/* house spokes */}
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

        {/* house numbers */}
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

        {/* center labels */}
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

        {/* aspect lines using real backend aspects data */}
        {chart.aspects.map((a, i) => {
          const from = planetPoints.find(p => p.name === a.planet)
          const to = planetPoints.find(p => p.name === a.targetPlanet)
          if (!from || !to) return null
          const color = ASPECT_COLOR[a.aspectType.toLowerCase()] ?? "oklch(0.55 0.06 295)"
          return (
            <line
              key={`asp-${a.planet}-${a.targetPlanet}-${i}`}
              x1={from.x} y1={from.y}
              x2={to.x} y2={to.y}
              stroke={color}
              strokeWidth={0.6}
              strokeOpacity={0.5}
            />
          )
        })}

        {/* planets */}
        {planetPoints.map((p) => {
          const color = PLANET_COLORS[p.name] ?? "oklch(0.55 0.05 295)"
          const isSel = selected?.name === p.name
          return (
            <g
              key={p.name}
              className="cursor-pointer focus:outline-none"
              style={{ outline: "none", WebkitTapHighlightColor: "transparent" }}
              onClick={() => setSelectedPlanet(isSel ? null : p.name)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault()
                  setSelectedPlanet(isSel ? null : p.name)
                }
              }}
              role="button"
              tabIndex={0}
              aria-label={`${PLANET_RU[p.name] ?? p.name} в ${p.sign ? (SIGN_PREPOSITIONAL[p.sign] || p.sign) : ""}${p.house ? `, ${p.house} дом` : ""}`}
              data-testid="day-chart-planet"
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
                {PLANET_SYMBOLS[p.name] ?? "•"}
              </text>
            </g>
          )
        })}
      </svg>

      {/* planet detail popover matching 3001 */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0, y: 8, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: 8, height: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-2 w-full max-w-[340px] overflow-hidden rounded-lg border border-border/70 bg-card/80 px-3.5 py-2.5 backdrop-blur"
            data-testid="day-chart-planet-popover"
          >
            <div className="flex items-center gap-2.5">
              <span
                className="flex h-8 w-8 items-center justify-center rounded-full text-base font-semibold"
                style={{
                  color: PLANET_COLORS[selected.name] ?? "var(--foreground)",
                  background: `${PLANET_COLORS[selected.name] || "#000000"}1a`,
                }}
              >
                {PLANET_SYMBOLS[selected.name] ?? "•"}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-medium text-foreground">{PLANET_RU[selected.name] ?? selected.name}</span>
                  <span className="text-[11px] text-muted-foreground">
                    {selected.signSymbol} {SIGN_RU[selected.sign] ?? selected.sign} · {selected.house} дом
                  </span>
                </div>
                <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                  {selected.interpretation || "Интерпретация временно недоступна."}
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* static aspect legend matching 3001 */}
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
// END_BLOCK: DAY_CHART_COMPONENT
