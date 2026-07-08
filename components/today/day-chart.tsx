"use client"

import { useState, useCallback } from "react"
import type { DayChart as DayChartData, DayStatus } from "@/lib/contracts/today"
import { getPlanetLabel } from "@/lib/display/sphere-labels"

type Props = {
  chart: DayChartData | null
  dateLabel?: string
  dayStatus?: DayStatus
}

const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
  Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
}

const SIGN_SYMBOLS_LIST = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]

const SIGN_RU: Record<string, string> = {
  Aries: "Овен", Taurus: "Телец", Gemini: "Близнецы", Cancer: "Рак", Leo: "Лев", Virgo: "Дева",
  Libra: "Весы", Scorpio: "Скорпион", Sagittarius: "Стрелец", Capricorn: "Козерог", Aquarius: "Водолей", Pisces: "Рыбы",
}

const SIGN_PREPOSITIONAL: Record<string, string> = {
  Aries: "Овне", Taurus: "Тельце", Gemini: "Близнецах", Cancer: "Раке", Leo: "Льве", Virgo: "Деве",
  Libra: "Весах", Scorpio: "Скорпионе", Sagittarius: "Стрельце", Capricorn: "Козероге", Aquarius: "Водолее", Pisces: "Рыбах",
}

const SIGN_SYMBOLS: Record<string, string> = {
  Aries: "♈", Taurus: "♉", Gemini: "♊", Cancer: "♋", Leo: "♌", Virgo: "♍",
  Libra: "♎", Scorpio: "♏", Sagittarius: "♐", Capricorn: "♑", Aquarius: "♒", Pisces: "♓",
}

const STATUS_COLOR: Record<DayStatus, string> = {
  steady: "oklch(0.62 0.06 305)", supportive: "oklch(0.64 0.12 150)", tense: "oklch(0.58 0.14 27)",
}

const ASPECT_COLOR: Record<string, string> = {
  conjunction: "oklch(0.55 0.06 305)", opposition: "oklch(0.55 0.14 27)",
  trine: "oklch(0.60 0.10 150)", square: "oklch(0.60 0.12 60)", sextile: "oklch(0.60 0.08 230)",
}

const ASPECT_LABELS = [
  { name: "соединение", color: "oklch(0.55 0.06 305)" },
  { name: "оппозиция", color: "oklch(0.55 0.14 27)" },
  { name: "тригон", color: "oklch(0.60 0.10 150)" },
  { name: "квадратура", color: "oklch(0.60 0.12 60)" },
  { name: "секстиль", color: "oklch(0.60 0.08 230)" },
]

const PLANET_KEYWORDS: Record<string, string> = {
  Sun: "личность, самовыражение, витальность",
  Moon: "эмоции, подсознание, адаптация",
  Mercury: "мышление, коммуникация, интеллект",
  Venus: "любовь, ценности, гармония",
  Mars: "активность, воля, импульс",
  Jupiter: "расширение, возможности, мудрость",
  Saturn: "дисциплина, ответственность, ограничения",
  Uranus: "озарения, перемены, свобода",
  Neptune: "интуиция, иллюзии, вдохновение",
  Pluto: "трансформация, глубина, власть",
}

const HOUSE_THEMES: Record<number, string> = {
  1: "личность, внешность, инициатива",
  2: "ресурсы, финансы, ценности",
  3: "общение, контакты, поездки",
  4: "дом, семья, корни",
  5: "творчество, дети, самовыражение",
  6: "здоровье, рутина, служение",
  7: "партнёрство, отношения, договоры",
  8: "кризисы, общие финансы, перемены",
  9: "мировоззрение, учёба, путешествия",
  10: "карьера, статус, достижения",
  11: "планы, друзья, социум",
  12: "подсознание, уединение, тайны",
}

const SIZE = 320; const CENTER = SIZE / 2; const OUTER_RADIUS = 150; const HOUSE_RADIUS = 118; const PLANET_RADIUS = 82

function pointAt(longitude: number, radius: number) {
  const angle = ((180 - longitude) * Math.PI) / 180
  return { x: CENTER + radius * Math.cos(angle), y: CENTER + radius * Math.sin(angle) }
}

export function DayChart({ chart, dateLabel, dayStatus = "steady" }: Props) {
  const [selectedPlanet, setSelectedPlanet] = useState<string | null>(null)

  const selectPlanet = useCallback((name: string) => {
    setSelectedPlanet((prev) => (prev === name ? null : name))
  }, [])

  const handleKeyDown = useCallback((name: string, e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectPlanet(name) }
  }, [selectPlanet])

  if (!chart || chart.transitPlanets.length === 0) {
    return (
      <section className="mx-5 rounded-lg border border-border/60 bg-card/60 px-4 py-6 text-center" data-testid="day-chart-unavailable">
        <p className="text-sm font-medium text-foreground">Карта дня недоступна</p>
        <p className="mt-1 text-xs text-muted-foreground">Расчёт не пришёл от сервера.</p>
      </section>
    )
  }

  const planetPoints = new Map(chart.transitPlanets.map((p) => [p.name, { planet: p, ...pointAt(p.longitude, PLANET_RADIUS) }]))
  const selected = selectedPlanet ? chart.transitPlanets.find((p) => p.name === selectedPlanet) ?? null : null

  // Popover description builder
  const getPopoverDesc = () => {
    if (!selected) return ""
    const kw = PLANET_KEYWORDS[selected.name] || ""
    const houseTheme = selected.house ? HOUSE_THEMES[selected.house] : null
    return `${kw}.${houseTheme ? ` Сегодня акцент через ${selected.house} дом — ${houseTheme}.` : ""}`
  }

  return (
    <section className="px-5 space-y-3" aria-label="Карта дня" data-testid="day-chart">
      {/* 3001 visual shell: nobordered card, directly follows concrete advice */}
      <div className="flex flex-col items-center">
        <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="chart-svg-root h-auto w-full max-w-[340px]" role="img" aria-label="Астрологическая карта">
          <circle cx={CENTER} cy={CENTER} r={OUTER_RADIUS} fill="var(--card)" stroke="var(--border)" />
          <circle cx={CENTER} cy={CENTER} r={HOUSE_RADIUS} fill="none" stroke="var(--border)" />
          <circle cx={CENTER} cy={CENTER} r={50} data-chart-center fill={STATUS_COLOR[dayStatus]} fillOpacity={0.08} stroke={STATUS_COLOR[dayStatus]} strokeOpacity={0.35} />

          {/* Sign spokes */}
          {SIGN_SYMBOLS_LIST.map((symbol, i) => {
            const sp = pointAt(i * 30, OUTER_RADIUS)
            const lb = pointAt(i * 30 + 15, 134)
            return (
              <g key={symbol}>
                <line x1={CENTER} y1={CENTER} x2={sp.x} y2={sp.y} stroke="var(--border)" strokeWidth={0.6} strokeOpacity={0.65} />
                <text x={lb.x} y={lb.y} textAnchor="middle" dominantBaseline="central" fontSize={13} fill="var(--muted-foreground)">{symbol}</text>
              </g>
            )
          })}

          {/* Houses */}
          {chart.houses.map((h) => {
            const outer = pointAt(h.cuspLongitude, HOUSE_RADIUS)
            const lb = pointAt(h.cuspLongitude + 12, 106)
            return (
              <g key={`${h.number}-${h.cuspLongitude}`}>
                <line x1={CENTER} y1={CENTER} x2={outer.x} y2={outer.y} stroke="var(--foreground)" strokeWidth={h.number === 1 ? 1.2 : 0.5} strokeOpacity={h.number === 1 ? 0.5 : 0.22} />
                <text x={lb.x} y={lb.y} textAnchor="middle" dominantBaseline="central" fontSize={9} fill="var(--muted-foreground)">{h.number}</text>
              </g>
            )
          })}

          {/* Aspects */}
          {chart.aspects.map((a, i) => {
            const from = planetPoints.get(a.planet)
            const to = planetPoints.get(a.targetPlanet)
            if (!from || !to) return null
            return <line key={`${a.planet}-${a.targetPlanet}-${a.aspectType}-${i}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke={ASPECT_COLOR[a.aspectType.toLowerCase()] ?? "var(--muted-foreground)"} strokeWidth={Math.max(0.7, (a.strength ?? 0.5) * 1.6)} strokeOpacity={0.58} />
          })}

          {/* Planets — clickable */}
          {Array.from(planetPoints.values()).map(({ planet, x, y }) => {
            const isSelected = selectedPlanet === planet.name
            return (
              <g key={`${planet.name}-${planet.longitude}`} className="cursor-pointer">
                {/* Visual glyph */}
                <circle cx={x} cy={y} r={11} fill="var(--card)" stroke={isSelected ? "var(--primary)" : planet.retrograde ? STATUS_COLOR.tense : "var(--primary)"} strokeWidth={isSelected ? 2.5 : 1.4} />
                <text x={x} y={y} textAnchor="middle" dominantBaseline="central" fontSize={13} fontWeight={isSelected ? 700 : 600} fill="var(--foreground)" className="pointer-events-none">
                  {PLANET_SYMBOLS[planet.name] ?? "•"}
                </text>
                {/* Hit area (larger transparent circle, rendered last to sit on top of glyph/text) */}
                <circle cx={x} cy={y} r={18} fill="transparent" style={{ cursor: "pointer" }}
                  onClick={() => selectPlanet(planet.name)}
                  onKeyDown={(e) => handleKeyDown(planet.name, e)}
                  role="button" tabIndex={0}
                  aria-label={`${getPlanetLabel(planet.name)}${planet.sign ? ` в ${SIGN_PREPOSITIONAL[planet.sign] || planet.sign}` : ""}${planet.house ? `, ${planet.house} дом` : ""}`}
                  data-testid="day-chart-planet"
                />
              </g>
            )
          })}

          {/* Center labels matching 3001 */}
          {dateLabel ? <text x={CENTER} y={CENTER - 5} textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600} fill="var(--foreground)">{dateLabel}</text> : null}
          <text x={CENTER} y={CENTER + 9} textAnchor="middle" dominantBaseline="central" fontSize={8} fill="var(--muted-foreground)" letterSpacing={1.5} className="uppercase">карта дня</text>
        </svg>

        {/* 3001 Aspect Legend */}
        <div className="mt-4 flex flex-wrap justify-center gap-x-4 gap-y-1.5 text-[11px] text-muted-foreground/80">
          {ASPECT_LABELS.map((aspect) => (
            <div key={aspect.name} className="flex items-center gap-1.5">
              <span className="h-1.5 w-3 rounded-full flex-none" style={{ background: aspect.color }} />
              <span>{aspect.name}</span>
            </div>
          ))}
        </div>

        {/* Planet detail popover matching 3001 style */}
        {selected ? (
          <div className="mt-3 w-full max-w-[340px] rounded-lg border border-border/70 bg-card/80 px-3.5 py-2.5 backdrop-blur" data-testid="day-chart-planet-popover">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-full text-base font-semibold" style={{ background: "var(--muted)/15", color: "var(--foreground)" }}>
                {PLANET_SYMBOLS[selected.name]}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-medium text-foreground">{getPlanetLabel(selected.name)}</span>
                  <span className="text-[11px] text-muted-foreground">
                    {selected.sign ? (SIGN_SYMBOLS[selected.sign] || "") : ""} {selected.sign ? (SIGN_RU[selected.sign] || selected.sign) : ""} · {selected.house || 1} дом
                  </span>
                </div>
                <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground">
                  {getPopoverDesc()}
                </p>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  )
}
