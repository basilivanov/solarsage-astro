"use client"

import { useMemo, useState } from "react"

import type { NatalPreviewChart, NatalPreviewChartPlanet } from "@/lib/contracts/natal"

type Props = {
  chart: NatalPreviewChart | null
  birthLabel?: string
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

const ZODIAC_ORDER = [
  "Aries",
  "Taurus",
  "Gemini",
  "Cancer",
  "Leo",
  "Virgo",
  "Libra",
  "Scorpio",
  "Sagittarius",
  "Capricorn",
  "Aquarius",
  "Pisces",
]

const ASPECT_COLOR: Record<string, string> = {
  conjunction: "oklch(0.55 0.06 305)",
  opposition: "oklch(0.55 0.14 27)",
  trine: "oklch(0.60 0.10 150)",
  square: "oklch(0.60 0.12 60)",
  sextile: "oklch(0.60 0.08 230)",
}

const SIZE = 360
const CENTER = SIZE / 2
const OUTER_RADIUS = 168
const ZODIAC_LABEL_RADIUS = 154
const HOUSE_RADIUS = 128
const HOUSE_LABEL_RADIUS = 114
const PLANET_RADIUS = 86
const ANGLE_MARKER_INNER_RADIUS = 134
const ANGLE_MARKER_OUTER_RADIUS = 168
const ANGLE_LABEL_RADIUS = 146

function pointAt(longitude: number, radius: number) {
  const angle = ((180 - longitude) * Math.PI) / 180
  return {
    x: CENTER + radius * Math.cos(angle),
    y: CENTER + radius * Math.sin(angle),
  }
}

function planetLabel(planet: NatalPreviewChartPlanet) {
  const symbol = PLANET_SYMBOLS[planet.name] ?? "•"
  const house = planet.house ? ` · ${planet.house} дом` : ""
  const retrograde = planet.retrograde ? " · R" : ""
  return `${symbol} ${planet.name} ${Math.round(planet.longitude * 10) / 10}°${house}${retrograde}`
}

export function NatalChartWheel({ chart, birthLabel }: Props) {
  const [selected, setSelected] = useState<string | null>(null)

  const planetPoints = useMemo(() => {
    if (!chart) return new Map<string, NatalPreviewChartPlanet & { x: number; y: number }>()
    return new Map(
      chart.planets.map((planet, index) => {
        const base = pointAt(planet.longitude, PLANET_RADIUS + (index % 2 === 0 ? 0 : 7))
        return [planet.name, { ...planet, ...base }]
      }),
    )
  }, [chart])

  if (!chart || chart.planets.length === 0 || chart.houses.length === 0) {
    return (
      <section
        className="mx-5 rounded-lg border border-border/60 bg-card/60 px-4 py-6 text-center"
        data-testid="natal-chart-unavailable"
      >
        <p className="text-sm font-medium text-foreground">Натальная карта недоступна</p>
        <p className="mt-1 text-xs text-muted-foreground">Расчёт не пришёл от сервера.</p>
      </section>
    )
  }

  return (
    <section className="px-5" aria-label="Натальная карта" data-testid="natal-chart">
      <div className="day-chart-surface">
        <div className="day-section-heading">
          <span>Натальная карта</span>
          <span>{chart.houseSystem}</span>
        </div>

        <svg
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          className="chart-svg-root h-auto w-full"
          role="img"
          aria-label="Натальная карта по данным сервера"
        >
          <circle cx={CENTER} cy={CENTER} r={OUTER_RADIUS} fill="var(--card)" stroke="var(--border)" />
          <circle cx={CENTER} cy={CENTER} r={HOUSE_RADIUS} fill="none" stroke="var(--border)" />
          <circle
            cx={CENTER}
            cy={CENTER}
            r={52}
            data-chart-center
            fill="oklch(0.48 0.06 305)"
            fillOpacity={0.08}
            stroke="oklch(0.48 0.06 305)"
            strokeOpacity={0.32}
          />

          {ZODIAC_ORDER.map((sign, index) => {
            const spoke = pointAt(index * 30, OUTER_RADIUS)
            const label = pointAt(index * 30 + 15, ZODIAC_LABEL_RADIUS)
            return (
              <g key={sign}>
                <line
                  x1={CENTER}
                  y1={CENTER}
                  x2={spoke.x}
                  y2={spoke.y}
                  stroke="var(--border)"
                  strokeWidth={0.55}
                  strokeOpacity={0.6}
                />
                <text
                  x={label.x}
                  y={label.y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={13}
                  fill="var(--muted-foreground)"
                >
                  {SIGN_SYMBOLS[sign]}
                </text>
              </g>
            )
          })}

          {chart.houses.map((house) => {
            const outer = pointAt(house.longitude, HOUSE_RADIUS)
            const label = pointAt(house.longitude + 12, HOUSE_LABEL_RADIUS)
            const isAngular = [1, 4, 7, 10].includes(house.number)
            return (
              <g key={`${house.number}-${house.longitude}`}>
                <line
                  x1={CENTER}
                  y1={CENTER}
                  x2={outer.x}
                  y2={outer.y}
                  stroke="var(--foreground)"
                  strokeWidth={isAngular ? 1.15 : 0.45}
                  strokeOpacity={isAngular ? 0.5 : 0.22}
                />
                <text
                  x={label.x}
                  y={label.y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={9}
                  fontWeight={isAngular ? 700 : 500}
                  fill="var(--muted-foreground)"
                >
                  {house.number}
                </text>
              </g>
            )
          })}

          {chart.angles.map((angle) => {
            const markerStart = pointAt(angle.longitude, ANGLE_MARKER_INNER_RADIUS)
            const markerEnd = pointAt(angle.longitude, ANGLE_MARKER_OUTER_RADIUS)
            const label = pointAt(angle.longitude, ANGLE_LABEL_RADIUS)
            const isPrimaryAngle = angle.name === "ASC" || angle.name === "MC"

            return (
              <g key={`${angle.name}-${angle.longitude}`} data-testid={`natal-angle-${angle.name}`}>
                <line
                  x1={markerStart.x}
                  y1={markerStart.y}
                  x2={markerEnd.x}
                  y2={markerEnd.y}
                  stroke={isPrimaryAngle ? "oklch(0.48 0.06 305)" : "var(--muted-foreground)"}
                  strokeWidth={isPrimaryAngle ? 1.6 : 0.9}
                  strokeOpacity={0.8}
                />
                <circle
                  cx={markerEnd.x}
                  cy={markerEnd.y}
                  r={isPrimaryAngle ? 3.5 : 2.5}
                  fill={isPrimaryAngle ? "oklch(0.48 0.06 305)" : "var(--muted-foreground)"}
                  fillOpacity={0.9}
                />
                <text
                  x={label.x}
                  y={label.y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={10}
                  fontWeight={700}
                  fill={isPrimaryAngle ? "var(--foreground)" : "var(--muted-foreground)"}
                >
                  {angle.name}
                </text>
              </g>
            )
          })}

          {chart.aspects.map((aspect, index) => {
            const from = planetPoints.get(aspect.planetA)
            const to = planetPoints.get(aspect.planetB)
            if (!from || !to) return null
            return (
              <line
                key={`${aspect.planetA}-${aspect.planetB}-${aspect.aspectType}-${index}`}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke={ASPECT_COLOR[aspect.aspectType.toLowerCase()] ?? "var(--muted-foreground)"}
                strokeWidth={0.9}
                strokeOpacity={0.52}
              />
            )
          })}

          {Array.from(planetPoints.values()).map((planet) => {
            const selectedPlanet = selected === planet.name
            const color = PLANET_COLORS[planet.name] ?? "var(--primary)"
            return (
              <g
                key={`${planet.name}-${planet.longitude}`}
                className="cursor-pointer"
                onClick={() => setSelected(selectedPlanet ? null : planet.name)}
              >
                <circle cx={planet.x} cy={planet.y} r={14} fill="transparent" />
                <circle
                  cx={planet.x}
                  cy={planet.y}
                  r={selectedPlanet ? 12 : 10}
                  fill="var(--card)"
                  stroke={planet.retrograde ? ASPECT_COLOR.opposition : color}
                  strokeWidth={selectedPlanet ? 2 : 1.35}
                />
                <text
                  x={planet.x}
                  y={planet.y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={13}
                  fontWeight={700}
                  fill={color}
                  className="pointer-events-none"
                >
                  {PLANET_SYMBOLS[planet.name] ?? "•"}
                </text>
              </g>
            )
          })}

          {birthLabel ? (
            <text
              x={CENTER}
              y={CENTER - 5}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={11}
              fontWeight={650}
              fill="var(--foreground)"
            >
              {birthLabel}
            </text>
          ) : null}
          <text
            x={CENTER}
            y={birthLabel ? CENTER + 11 : CENTER + 3}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={8}
            fill="var(--muted-foreground)"
          >
            {chart.houseSystem}
          </text>
        </svg>

        <div className="mt-2 flex flex-wrap justify-center gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
          {chart.planets.map((planet) => (
            <button
              key={`${planet.name}-${planet.longitude}`}
              type="button"
              className="rounded px-1 py-0.5 text-left transition hover:bg-secondary/70 hover:text-foreground"
              onClick={() => setSelected(selected === planet.name ? null : planet.name)}
            >
              {planetLabel(planet)}
            </button>
          ))}
        </div>

        {selected ? (
          <div className="mt-3 rounded-lg border border-border/70 bg-background/70 px-3 py-2 text-xs text-muted-foreground">
            {planetLabel(planetPoints.get(selected)!)}
          </div>
        ) : null}
      </div>
    </section>
  )
}
