"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

/**
 * NatalChartWheel — full natal chart visualization with all 10 planets,
 * 12 houses, zodiac ring, and aspect lines. Larger and more detailed
 * than the DayChart (which uses only 7 planets and day-shifted positions).
 *
 * Uses the natal data from DEMO_NATAL_RESPONSE (lib/demo-data.ts).
 */

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

const ZODIAC_ORDER = [
  "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
  "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

// Russian names for the planet detail popover
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

// Chart geometry constants (module-level so useMemo deps are stable)
const SIZE = 360
const C = SIZE / 2
const R_OUTER = 168
const R_ZODIAC_INNER = 140
const R_HOUSE = 132
const R_HOUSE_INNER = 104
const R_PLANET = 86
const R_CENTER = 56

export interface NatalPlanet {
  name: string
  sign: string
  longitude: number
  house: number
}

export interface NatalHouse {
  number: number
  cusp: number
  sign: string
}

interface NatalChartWheelProps {
  planets: NatalPlanet[]
  houses: NatalHouse[]
  houseSystem?: string
  birthLabel?: string
}

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

export function NatalChartWheel({
  planets,
  houses,
  houseSystem = "PLACIDUS",
  birthLabel,
}: NatalChartWheelProps) {
  const [selected, setSelected] = useState<NatalPlanet | null>(null)
  const [showAspects, setShowAspects] = useState(true)

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
          midAngle: longitudeToAngle(h.cusp + 15),
        }
      }),
    [houses]
  )

  const planetPoints = useMemo(() => {
    const sorted = [...planets].sort((a, b) => a.longitude - b.longitude)
    const points = sorted.map((p) => {
      const angle = longitudeToAngle(p.longitude)
      const pos = polarToCartesian(C, C, R_PLANET, angle)
      return { ...p, angle, x: pos.x, y: pos.y, offset: 0 }
    })
    // Collision avoidance: spread close planets radially
    for (let i = 0; i < points.length; i++) {
      const next = points[(i + 1) % points.length]
      const diff = Math.abs(((points[i].angle - next.angle + 540) % 360) - 180)
      if (diff < 7) {
        next.offset = 16
        const pos = polarToCartesian(C, C, R_PLANET + next.offset, next.angle)
        next.x = pos.x
        next.y = pos.y
      }
    }
    return points
  }, [planets])

  const aspects = useMemo(() => {
    const result: { p1: typeof planetPoints[0]; p2: typeof planetPoints[0]; color: string; type: string }[] = []
    for (let i = 0; i < planetPoints.length; i++) {
      for (let j = i + 1; j < planetPoints.length; j++) {
        const diff = Math.abs(planetPoints[i].longitude - planetPoints[j].longitude)
        const norm = Math.min(diff, 360 - diff)
        let color: string | null = null
        let type = ""
        if (norm <= 8) { color = "oklch(0.55 0.06 305)"; type = "соединение" }
        else if (Math.abs(norm - 180) <= 8) { color = "oklch(0.55 0.14 27)"; type = "оппозиция" }
        else if (Math.abs(norm - 120) <= 7) { color = "oklch(0.60 0.10 150)"; type = "тригон" }
        else if (Math.abs(norm - 90) <= 7) { color = "oklch(0.60 0.12 60)"; type = "квадратура" }
        else if (Math.abs(norm - 60) <= 6) { color = "oklch(0.60 0.08 230)"; type = "секстиль" }
        if (color) result.push({ p1: planetPoints[i], p2: planetPoints[j], color, type })
      }
    }
    return result
  }, [planetPoints])

  return (
    <section className="px-5" aria-label="Натальная карта">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Натальная карта
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="relative rounded-2xl border border-border/50 bg-gradient-to-br from-card via-card to-secondary/20 p-3">
        {/* Toggle aspects */}
        <button
          type="button"
          onClick={() => setShowAspects((v) => !v)}
          className="absolute right-3 top-3 z-10 rounded-full border border-border/60 bg-card/80 px-2.5 py-1 text-[10px] font-medium text-muted-foreground backdrop-blur transition hover:text-foreground active:scale-95"
        >
          {showAspects ? "✓ аспекты" : "○ аспекты"}
        </button>

        <svg
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          className="chart-svg-root h-auto w-full"
          role="img"
          aria-label="Натальная карта — круговая диаграмма с положениями планет"
        >
          <defs>
            <radialGradient id="natal-bg-grad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="oklch(0.99 0.008 305)" />
              <stop offset="70%" stopColor="oklch(0.97 0.012 305)" />
              <stop offset="100%" stopColor="oklch(0.94 0.015 305)" />
            </radialGradient>
            <radialGradient id="natal-center-grad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="oklch(0.48 0.06 305 / 0.14)" />
              <stop offset="100%" stopColor="oklch(0.48 0.06 305 / 0)" />
            </radialGradient>
          </defs>

          <circle cx={C} cy={C} r={R_OUTER + 4} fill="url(#natal-bg-grad)" stroke="oklch(0.88 0.01 295)" strokeWidth={0.5} />

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

          {/* House ring */}
          <circle cx={C} cy={C} r={R_HOUSE} fill="none" stroke="oklch(0.82 0.01 295)" strokeWidth={0.5} />
          <circle cx={C} cy={C} r={R_HOUSE_INNER} fill="none" stroke="oklch(0.82 0.01 295)" strokeWidth={0.5} />

          {/* House cusps */}
          {houseSpokes.map((h) => (
            <g key={h.number}>
              <line
                x1={h.inner.x} y1={h.inner.y}
                x2={h.outer.x} y2={h.outer.y}
                stroke={h.number === 1 ? "oklch(0.55 0.06 305)" : "oklch(0.78 0.015 295)"}
                strokeWidth={h.number === 1 ? 1.4 : 0.5}
                strokeDasharray={h.number === 1 ? "none" : "2 2"}
              />
              {h.number === 4 && (
                <line
                  x1={h.inner.x} y1={h.inner.y}
                  x2={h.outer.x} y2={h.outer.y}
                  stroke="oklch(0.55 0.06 305)"
                  strokeWidth={1}
                />
              )}
              {h.number === 7 && (
                <line
                  x1={h.inner.x} y1={h.inner.y}
                  x2={h.outer.x} y2={h.outer.y}
                  stroke="oklch(0.55 0.06 305)"
                  strokeWidth={1}
                />
              )}
              {h.number === 10 && (
                <line
                  x1={h.inner.x} y1={h.inner.y}
                  x2={h.outer.x} y2={h.outer.y}
                  stroke="oklch(0.55 0.06 305)"
                  strokeWidth={1}
                />
              )}
            </g>
          ))}

          {/* House numbers */}
          {houseSpokes.map((h, i) => {
            const next = houseSpokes[(i + 1) % houseSpokes.length]
            const midLon = (h.cusp + next.cusp) / 2
            const midAngle = longitudeToAngle(midLon)
            const pos = polarToCartesian(C, C, (R_HOUSE + R_HOUSE_INNER) / 2, midAngle)
            const isAngular = [1, 4, 7, 10].includes(h.number)
            return (
              <text
                key={`hn-${h.number}`}
                x={pos.x}
                y={pos.y}
                fontSize={10}
                fontWeight={isAngular ? 700 : 500}
                fill={isAngular ? "oklch(0.48 0.06 305)" : "oklch(0.58 0.02 295)"}
                textAnchor="middle"
                dominantBaseline="central"
                className="select-none"
              >
                {h.number}
              </text>
            )
          })}

          {/* Center disk */}
          <circle cx={C} cy={C} r={R_CENTER} fill="url(#natal-center-grad)" stroke="oklch(0.78 0.015 295)" strokeWidth={0.5} data-chart-center />
          <circle cx={C} cy={C} r={R_CENTER - 6} fill="none" stroke="oklch(0.85 0.01 295)" strokeWidth={0.4} strokeDasharray="1 3" />

          {/* Center label */}
          {birthLabel && (
            <text
              x={C}
              y={C - 8}
              fontSize={10}
              fontWeight={600}
              fill="oklch(0.42 0.04 295)"
              textAnchor="middle"
              dominantBaseline="central"
              className="select-none"
            >
              {birthLabel}
            </text>
          )}
          <text
            x={C}
            y={C + 4}
            fontSize={8}
            letterSpacing={1}
            fill="oklch(0.55 0.02 295)"
            textAnchor="middle"
            dominantBaseline="central"
            className="select-none uppercase"
          >
            {houseSystem}
          </text>
          <text
            x={C}
            y={C + 16}
            fontSize={7}
            fill="oklch(0.6 0.02 295)"
            textAnchor="middle"
            dominantBaseline="central"
            className="select-none"
          >
            {planets.length} планет
          </text>

          {/* Aspect lines */}
          {showAspects && aspects.map((a, i) => (
            <line
              key={`asp-${i}`}
              x1={a.p1.x} y1={a.p1.y}
              x2={a.p2.x} y2={a.p2.y}
              stroke={a.color}
              strokeWidth={0.6}
              strokeOpacity={0.45}
            />
          ))}

          {/* Planets */}
          {planetPoints.map((p) => {
            const color = PLANET_COLORS[p.name]
            const isSel = selected?.name === p.name
            return (
              <g
                key={p.name}
                className="cursor-pointer"
                onClick={() => setSelected(isSel ? null : p)}
              >
                <circle cx={p.x} cy={p.y} r={14} fill="transparent" />
                <motion.circle
                  cx={p.x} cy={p.y}
                  r={isSel ? 12 : 10}
                  fill="oklch(0.99 0.005 305)"
                  stroke={color}
                  strokeWidth={isSel ? 2.2 : 1.4}
                  initial={false}
                  animate={{ scale: isSel ? 1.1 : 1 }}
                  transition={{ type: "spring", stiffness: 300, damping: 20 }}
                  style={{ transformOrigin: `${p.x}px ${p.y}px` }}
                />
                <text
                  x={p.x}
                  y={p.y}
                  fontSize={13}
                  fontWeight={600}
                  fill={color}
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="select-none pointer-events-none"
                >
                  {PLANET_SYMBOLS[p.name]}
                </text>
              </g>
            )
          })}
        </svg>

        {/* Planet detail popover */}
        <AnimatePresence>
          {selected && (
            <motion.div
              initial={{ opacity: 0, y: 8, height: 0 }}
              animate={{ opacity: 1, y: 0, height: "auto" }}
              exit={{ opacity: 0, y: 8, height: 0 }}
              transition={{ duration: 0.2 }}
              className="mt-2 overflow-hidden rounded-lg border border-border/70 bg-card/80 px-3.5 py-2.5 backdrop-blur"
            >
              <div className="flex items-center gap-2.5">
                <span
                  className="flex h-9 w-9 items-center justify-center rounded-full text-base font-semibold"
                  style={{
                    color: PLANET_COLORS[selected.name],
                    background: `${PLANET_COLORS[selected.name]}1a`,
                  }}
                >
                  {PLANET_SYMBOLS[selected.name]}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-sm font-medium text-foreground">
                      {PLANET_RU[selected.name] ?? selected.name}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      {SIGN_SYMBOLS[selected.sign]} {SIGN_RU[selected.sign] ?? selected.sign} · {selected.house} дом
                    </span>
                  </div>
                  <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                    {planetNatalDescription(selected.name, selected.house, selected.sign)}
                  </p>
                  <p className="mt-1 text-[10px] tabular-nums text-muted-foreground/70">
                    {selected.sign} {Math.floor(selected.longitude % 30)}°{Math.floor((selected.longitude % 1) * 60)}′ · долгота {selected.longitude.toFixed(1)}°
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Aspect summary */}
        <div className="mt-3 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
          <span className="font-medium text-foreground/70">Аспекты ({aspects.length}):</span>
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
    </section>
  )
}

function planetNatalDescription(name: string, house: number, sign: string): string {
  const houseThemes: Record<number, string> = {
    1: "личность, внешность, самовыражение",
    2: "ценности, ресурсы, деньги",
    3: "общение, обучение, ближний круг",
    4: "дом, семья, корни",
    5: "творчество, романтика, дети",
    6: "работа, здоровье, рутина",
    7: "партнёрство, брак, открытые враги",
    8: "трансформация, кризисы, общие ресурсы",
    9: "мировоззрение, дальние поездки, высшее образование",
    10: "карьера, статус, призвание",
    11: "друзья, цели, надежды",
    12: "тайное, уединение, подсознание",
  }
  const planetThemes: Record<string, string> = {
    Sun: "Ядро личности, воля, сознание, жизненная сила",
    Moon: "Эмоции, подсознание, привычки, мать, дом",
    Mercury: "Мышление, речь, обучение, коммуникация",
    Venus: "Любовь, ценности, красота, деньги, отношения",
    Mars: "Действие, воля, страсть, конфликт, энергия",
    Jupiter: "Расширение, удача, мудрость, вера",
    Saturn: "Ограничения, ответственность, дисциплина, карма",
    Uranus: "Свобода, перемены, оригинальность, бунт",
    Neptune: "Мечты, иллюзии, духовность, вдохновение",
    Pluto: "Трансформация, власть, разрушение и возрождение",
  }
  return `${planetThemes[name] ?? ""}. В натальной карте — ${house} дом (${houseThemes[house] ?? ""}), знак ${SIGN_RU[sign] ?? sign}.`
}
