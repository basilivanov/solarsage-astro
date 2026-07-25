// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_HORARY_CHART
// ROLE: Horary chart wheel component displaying planetary positions and house cusps for horary questions.
// DEPENDENCIES: react, lucide-react, lib/contracts/horary
// GRACE_ANCHORS: [HORARY_CHART_COMPONENT]
// SLICE: SLICE-HORARY-READINGS
// ############################################################################

// START_MODULE_CONTRACT: M-COMPONENTS-HORARY-CHART
// purpose: Render astrological horary chart wheel with planetary symbols and house positions.
// owns:
//   - components/readings/horary/horary-chart.tsx
// inputs: chart (HoraryChartSnapshot), involvedPlanets
// outputs: HoraryChart React component
// dependencies: lib/contracts/horary
// side_effects: none (pure SVG rendering)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-COMPONENTS-HORARY-CHART

// START_MODULE_MAP: M-COMPONENTS-HORARY-CHART
// public_entrypoints:
//   - HoraryChart
// semantic_blocks:
//   - HORARY_CHART_COMPONENT: horary chart wheel component
// owned_tests:
//   - __tests__/horary/horary-answer-view.test.tsx
// END_MODULE_MAP: M-COMPONENTS-HORARY-CHART

"use client"

import { useMemo, useState } from "react"
import { Clock, MapPin } from "lucide-react"
import type { HoraryChartSnapshot } from "@/lib/contracts/horary"

type Props = {
  chart: HoraryChartSnapshot
  involvedPlanets?: string[]
}

const SIGN_SYMBOLS: Record<string, string> = {
  Aries: "♈", Taurus: "♉", Gemini: "♊", Cancer: "♋", Leo: "♌", Virgo: "♍",
  Libra: "♎", Scorpio: "♏", Sagittarius: "♐", Capricorn: "♑", Aquarius: "♒", Pisces: "♓",
}

const SIGN_RU: Record<string, string> = {
  Aries: "Овен", Taurus: "Телец", Gemini: "Близнецы", Cancer: "Рак",
  Leo: "Лев", Virgo: "Дева", Libra: "Весы", Scorpio: "Скорпион",
  Sagittarius: "Стрелец", Capricorn: "Козерог", Aquarius: "Водолей", Pisces: "Рыбы",
}

const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
  Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
}

const PLANET_RU: Record<string, string> = {
  Sun: "Солнце", Moon: "Луна", Mercury: "Меркурий", Venus: "Венера",
  Mars: "Марс", Jupiter: "Юпитер", Saturn: "Сатурн",
  Uranus: "Уран", Neptune: "Нептун", Pluto: "Плутон",
}

const ASPECT_RU: Record<string, string> = {
  conjunction: "соединение",
  sextile: "секстиль",
  square: "квадратура",
  trine: "тригон",
  opposition: "оппозиция",
}

const ASPECT_COLORS: Record<string, string> = {
  conjunction: "oklch(0.48 0.08 260)",
  sextile: "oklch(0.55 0.11 210)",
  square: "oklch(0.58 0.15 40)",
  trine: "oklch(0.56 0.12 150)",
  opposition: "oklch(0.54 0.16 20)",
}

const PLANET_COLORS: Record<string, string> = {
  Sun: "oklch(0.68 0.14 75)",
  Moon: "oklch(0.58 0.07 260)",
  Mercury: "oklch(0.50 0.10 220)",
  Venus: "oklch(0.62 0.13 345)",
  Mars: "oklch(0.55 0.17 30)",
  Jupiter: "oklch(0.58 0.12 120)",
  Saturn: "oklch(0.42 0.05 250)",
  Uranus: "oklch(0.58 0.10 190)",
  Neptune: "oklch(0.50 0.11 285)",
  Pluto: "oklch(0.42 0.08 320)",
}

const ZODIAC_ORDER = [
  "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
  "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

const SIZE = 300
const C = SIZE / 2
const R_OUTER = 142
const R_ZODIAC_INNER = 119
const R_HOUSE = 108
const R_HOUSE_INNER = 82
const R_PLANET = 66
const R_CENTER = 42

function longitudeToAngle(longitude: number): number {
  return 180 - (((longitude % 360) + 360) % 360)
}

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = (angleDeg * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number): string {
  const start = polarToCartesian(cx, cy, r, endAngle)
  const end = polarToCartesian(cx, cy, r, startAngle)
  const largeArcFlag = Math.abs(endAngle - startAngle) <= 180 ? "0" : "1"
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`
}

function formatMoment(value: string, timezone: string) {
  try {
    return new Date(value).toLocaleString("ru-RU", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: timezone,
    })
  } catch {
    return value
  }
}

function formatDegree(longitude: number) {
  const degree = ((longitude % 30) + 30) % 30
  return `${Math.floor(degree)}°${Math.floor((degree % 1) * 60)}′`
}

function planetLabel(name: string) {
  return PLANET_RU[name] ?? name
}

function aspectLabel(type: string) {
  return ASPECT_RU[type] ?? type
}

// START_BLOCK: HORARY_CHART_COMPONENT
export function HoraryChart({ chart, involvedPlanets = [] }: Props) {
  const [selected, setSelected] = useState<string | null>(null)
  const involved = useMemo(() => new Set(involvedPlanets), [involvedPlanets])

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

  const houses = useMemo(
    () =>
      chart.houses.map((house) => {
        const angle = longitudeToAngle(house.cusp)
        return {
          ...house,
          angle,
          inner: polarToCartesian(C, C, R_HOUSE_INNER, angle),
          outer: polarToCartesian(C, C, R_HOUSE, angle),
        }
      }),
    [chart.houses]
  )

  const planets = useMemo(() => {
    const sorted = [...chart.planets].sort((a, b) => a.longitude - b.longitude)
    const points = sorted.map((planet) => {
      const angle = longitudeToAngle(planet.longitude)
      const pos = polarToCartesian(C, C, R_PLANET, angle)
      return {
        ...planet,
        angle,
        x: pos.x,
        y: pos.y,
        isInvolved: involved.has(planet.name),
      }
    })

    for (let i = 0; i < points.length; i++) {
      const next = points[(i + 1) % points.length]
      const diff = Math.abs(((points[i].angle - next.angle + 540) % 360) - 180)
      if (diff < 7) {
        const pos = polarToCartesian(C, C, R_PLANET + 12, next.angle)
        next.x = pos.x
        next.y = pos.y
      }
    }
    return points
  }, [chart.planets, involved])

  const planetByName = useMemo(() => new Map(planets.map((planet) => [planet.name, planet])), [planets])
  const selectedPlanet = selected ? planetByName.get(selected) : null

  return (
    <section
      role="region"
      aria-label="Карта момента вопроса"
      className="rounded-lg border border-border/60 bg-card p-4 shadow-sm"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Clock className="h-3.5 w-3.5 text-primary" strokeWidth={1.75} />
          <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Карта момента
          </h3>
        </div>
        <span className="text-[10px] text-muted-foreground/75">
          {formatMoment(chart.castAt, chart.timezone)}
        </span>
      </div>

      {chart.locationName && (
        <div className="mb-2 flex items-center gap-1.5 text-[10.5px] text-muted-foreground">
          <MapPin className="h-3 w-3" strokeWidth={1.75} />
          <span>{chart.locationName}</span>
        </div>
      )}

      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="h-auto w-full"
        role="img"
        aria-label="Положение планет и домов в сохранённой хорарной карте"
      >
        <circle cx={C} cy={C} r={R_OUTER + 3} fill="oklch(0.985 0.004 105)" stroke="oklch(0.84 0.015 95)" strokeWidth={0.6} />

        {zodiacSlices.map((slice, i) => {
          const labelPos = polarToCartesian(C, C, (R_OUTER + R_ZODIAC_INNER) / 2, slice.midAngle)
          const innerEnd = polarToCartesian(C, C, R_ZODIAC_INNER, slice.endAngle)
          const innerArc = describeArc(C, C, R_ZODIAC_INNER, slice.endAngle, slice.startAngle).replace("M", "L")
          return (
            <g key={slice.sign}>
              <path
                d={`${describeArc(C, C, R_OUTER, slice.startAngle, slice.endAngle)} L ${innerEnd.x} ${innerEnd.y} ${innerArc} Z`}
                fill={i % 2 === 0 ? "oklch(0.955 0.010 98)" : "oklch(0.99 0.003 105)"}
                stroke="oklch(0.84 0.015 95)"
                strokeWidth={0.4}
              />
              <text x={labelPos.x} y={labelPos.y} fontSize={12} fill="oklch(0.39 0.045 95)" textAnchor="middle" dominantBaseline="central">
                {slice.symbol}
              </text>
            </g>
          )
        })}

        <circle cx={C} cy={C} r={R_HOUSE} fill="none" stroke="oklch(0.78 0.012 95)" strokeWidth={0.5} />
        <circle cx={C} cy={C} r={R_HOUSE_INNER} fill="none" stroke="oklch(0.78 0.012 95)" strokeWidth={0.5} />

        {houses.map((house) => (
          <line
            key={house.number}
            x1={house.inner.x}
            y1={house.inner.y}
            x2={house.outer.x}
            y2={house.outer.y}
            stroke={house.number === 1 ? "oklch(0.45 0.09 210)" : "oklch(0.72 0.015 95)"}
            strokeWidth={house.number === 1 ? 1.4 : 0.55}
            strokeDasharray={house.number === 1 ? "none" : "2 2"}
          />
        ))}

        {houses.map((house, i) => {
          const next = houses[(i + 1) % houses.length]
          const span = (((next?.cusp ?? house.cusp + 30) - house.cusp + 360) % 360) || 30
          const midAngle = longitudeToAngle(house.cusp + span / 2)
          const pos = polarToCartesian(C, C, (R_HOUSE + R_HOUSE_INNER) / 2, midAngle)
          return (
            <text
              key={`house-label-${house.number}`}
              x={pos.x}
              y={pos.y}
              fontSize={9}
              fontWeight={house.number === 1 ? 700 : 500}
              fill={house.number === 1 ? "oklch(0.45 0.09 210)" : "oklch(0.43 0.02 95)"}
              textAnchor="middle"
              dominantBaseline="central"
            >
              {house.number}
            </text>
          )
        })}

        {chart.aspects.map((aspect, index) => {
          const a = planetByName.get(aspect.planet)
          const b = planetByName.get(aspect.targetPlanet)
          if (!a || !b) return null
          return (
            <line
              key={`${aspect.planet}-${aspect.targetPlanet}-${index}`}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={ASPECT_COLORS[aspect.aspectType] ?? "oklch(0.5 0.04 250)"}
              strokeWidth={0.8}
              strokeOpacity={0.56}
            />
          )
        })}

        <circle cx={C} cy={C} r={R_CENTER} fill="oklch(0.97 0.006 105)" stroke="oklch(0.78 0.012 95)" strokeWidth={0.5} />
        <text x={C} y={C - 4} fontSize={8} letterSpacing={1} fill="oklch(0.42 0.025 95)" textAnchor="middle" dominantBaseline="central">
          ХОРАР
        </text>
        <text x={C} y={C + 7} fontSize={7} fill="oklch(0.48 0.02 95)" textAnchor="middle" dominantBaseline="central">
          момент
        </text>

        {planets.map((planet) => {
          const color = PLANET_COLORS[planet.name] ?? "oklch(0.42 0.04 250)"
          const selectedPlanet = selected === planet.name
          const isInvolved = planet.isInvolved
          return (
            <g key={planet.name} className="cursor-pointer" onClick={() => setSelected(selectedPlanet ? null : planet.name)}>
              <circle cx={planet.x} cy={planet.y} r={13} fill="transparent" />
              <circle
                cx={planet.x}
                cy={planet.y}
                r={selectedPlanet ? 11 : isInvolved ? 10 : 8}
                fill={isInvolved ? color : "oklch(0.995 0.002 105)"}
                stroke={color}
                strokeWidth={isInvolved ? 0 : selectedPlanet ? 2 : 1.2}
              />
              <text
                x={planet.x}
                y={planet.y}
                fontSize={11}
                fontWeight={600}
                fill={isInvolved ? "white" : color}
                textAnchor="middle"
                dominantBaseline="central"
                className="pointer-events-none select-none"
              >
                {PLANET_SYMBOLS[planet.name] ?? planet.name.slice(0, 1)}
              </text>
            </g>
          )
        })}
      </svg>

      {selectedPlanet && (
        <div className="mt-2 rounded-md border border-border/60 bg-muted/20 px-3 py-2 text-[12px]">
          <div className="flex items-center justify-between gap-3">
            <span className="font-medium text-foreground">{planetLabel(selectedPlanet.name)}</span>
            <span className="text-muted-foreground">
              {selectedPlanet.sign ? `${SIGN_SYMBOLS[selectedPlanet.sign] ?? ""} ${SIGN_RU[selectedPlanet.sign] ?? selectedPlanet.sign}` : ""}
            </span>
          </div>
          <div className="mt-1 text-muted-foreground">
            {formatDegree(selectedPlanet.longitude)} · {selectedPlanet.longitude.toFixed(1)}°
          </div>
        </div>
      )}

      <div className="mt-3 grid gap-2 text-[11px] text-muted-foreground">
        <div className="flex flex-wrap gap-1.5">
          {chart.planets.map((planet) => (
            <span key={planet.name} className="rounded-full border border-border/60 px-2 py-0.5">
              {planetLabel(planet.name)}
            </span>
          ))}
        </div>
        {chart.aspects.length > 0 && (
          <div className="space-y-1 border-t border-border/40 pt-2">
            {chart.aspects.slice(0, 4).map((aspect, index) => (
              <div key={`${aspect.planet}-${aspect.targetPlanet}-label-${index}`}>
                {planetLabel(aspect.planet)} - {planetLabel(aspect.targetPlanet)}: {aspectLabel(aspect.aspectType)} ({aspect.orb.toFixed(1)}°)
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
// END_BLOCK: HORARY_CHART_COMPONENT
