import type { DayChart as DayChartData, DayStatus } from "@/lib/contracts/today"

type Props = {
  chart: DayChartData | null
  dateLabel?: string
  dayStatus?: DayStatus
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

const SIGN_SYMBOLS = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]

const STATUS_COLOR: Record<DayStatus, string> = {
  steady: "oklch(0.62 0.06 305)",
  supportive: "oklch(0.64 0.12 150)",
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
const CENTER = SIZE / 2
const OUTER_RADIUS = 150
const HOUSE_RADIUS = 118
const PLANET_RADIUS = 82

function pointAt(longitude: number, radius: number) {
  const angle = ((180 - longitude) * Math.PI) / 180
  return {
    x: CENTER + radius * Math.cos(angle),
    y: CENTER + radius * Math.sin(angle),
  }
}

export function DayChart({ chart, dateLabel, dayStatus = "steady" }: Props) {
  if (!chart || chart.transitPlanets.length === 0) {
    return (
      <section
        className="mx-5 rounded-lg border border-border/60 bg-card/60 px-4 py-6 text-center"
        data-testid="day-chart-unavailable"
      >
        <p className="text-sm font-medium text-foreground">Карта дня недоступна</p>
        <p className="mt-1 text-xs text-muted-foreground">Расчёт не пришёл от сервера.</p>
      </section>
    )
  }

  const planetPoints = new Map(
    chart.transitPlanets.map((planet) => [
      planet.name,
      { planet, ...pointAt(planet.longitude, PLANET_RADIUS) },
    ]),
  )

  return (
    <section className="px-5" aria-label="Карта дня" data-testid="day-chart">
      <div className="day-chart-surface">
        <div className="day-section-heading">
          <span>Карта дня</span>
          <span>{chart.source === "solarsage" ? "SolarSage" : chart.source}</span>
        </div>

        <svg
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          className="chart-svg-root h-auto w-full"
          role="img"
          aria-label="Астрологическая карта по данным сервера"
        >
          <circle
            cx={CENTER}
            cy={CENTER}
            r={OUTER_RADIUS}
            fill="var(--card)"
            stroke="var(--border)"
          />
          <circle
            cx={CENTER}
            cy={CENTER}
            r={HOUSE_RADIUS}
            fill="none"
            stroke="var(--border)"
          />
          <circle
            cx={CENTER}
            cy={CENTER}
            r={50}
            data-chart-center
            fill={STATUS_COLOR[dayStatus]}
            fillOpacity={0.08}
            stroke={STATUS_COLOR[dayStatus]}
            strokeOpacity={0.35}
          />

          {SIGN_SYMBOLS.map((symbol, index) => {
            const longitude = index * 30
            const spoke = pointAt(longitude, OUTER_RADIUS)
            const label = pointAt(longitude + 15, 134)
            return (
              <g key={symbol}>
                <line
                  x1={CENTER}
                  y1={CENTER}
                  x2={spoke.x}
                  y2={spoke.y}
                  stroke="var(--border)"
                  strokeWidth={0.6}
                  strokeOpacity={0.65}
                />
                <text
                  x={label.x}
                  y={label.y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={13}
                  fill="var(--muted-foreground)"
                >
                  {symbol}
                </text>
              </g>
            )
          })}

          {chart.houses.map((house) => {
            const outer = pointAt(house.cuspLongitude, HOUSE_RADIUS)
            const label = pointAt(house.cuspLongitude + 12, 106)
            return (
              <g key={`${house.number}-${house.cuspLongitude}`}>
                <line
                  x1={CENTER}
                  y1={CENTER}
                  x2={outer.x}
                  y2={outer.y}
                  stroke="var(--foreground)"
                  strokeWidth={house.number === 1 ? 1.2 : 0.5}
                  strokeOpacity={house.number === 1 ? 0.5 : 0.22}
                />
                <text
                  x={label.x}
                  y={label.y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={9}
                  fill="var(--muted-foreground)"
                >
                  {house.number}
                </text>
              </g>
            )
          })}

          {chart.aspects.map((aspect, index) => {
            const from = planetPoints.get(aspect.planet)
            const to = planetPoints.get(aspect.targetPlanet)
            if (!from || !to) return null
            return (
              <line
                key={`${aspect.planet}-${aspect.targetPlanet}-${aspect.aspectType}-${index}`}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke={ASPECT_COLOR[aspect.aspectType.toLowerCase()] ?? "var(--muted-foreground)"}
                strokeWidth={Math.max(0.7, (aspect.strength ?? 0.5) * 1.6)}
                strokeOpacity={0.58}
              />
            )
          })}

          {Array.from(planetPoints.values()).map(({ planet, x, y }) => (
            <g key={`${planet.name}-${planet.longitude}`}>
              <circle
                cx={x}
                cy={y}
                r={11}
                fill="var(--card)"
                stroke={planet.retrograde ? STATUS_COLOR.tense : "var(--primary)"}
                strokeWidth={1.4}
              />
              <text
                x={x}
                y={y}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={13}
                fontWeight={600}
                fill="var(--foreground)"
              >
                {PLANET_SYMBOLS[planet.name] ?? "•"}
              </text>
            </g>
          ))}

          {dateLabel ? (
            <text
              x={CENTER}
              y={CENTER - 3}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={12}
              fontWeight={600}
              fill="var(--foreground)"
            >
              {dateLabel}
            </text>
          ) : null}
          <text
            x={CENTER}
            y={CENTER + 12}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={8}
            fill="var(--muted-foreground)"
          >
            транзиты
          </text>
        </svg>

        <div className="mt-2 flex flex-wrap justify-center gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
          {chart.transitPlanets.map((planet) => (
            <span key={planet.name}>
              {PLANET_SYMBOLS[planet.name] ?? "•"} {planet.name}
              {planet.house ? ` · ${planet.house} дом` : ""}
              {planet.retrograde ? " · R" : ""}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
