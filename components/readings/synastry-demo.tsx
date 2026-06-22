"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Users, Heart, Sparkles, X, ChevronRight, Check, AlertTriangle } from "lucide-react"
import { DEMO_NATAL_RESPONSE } from "@/lib/demo-data"

/**
 * SynastryDemo — a compatibility demo card for the Readings screen.
 *
 * Lets the user pick a partner's sun sign and computes a playful
 * compatibility score + key aspect pairs using the user's natal Sun,
 * Moon, Venus, Mars from DEMO_NATAL_RESPONSE vs. the partner's
 * deterministic planet positions for the chosen sign.
 *
 * The calculation is intentionally light (sign-element math + a few
 * aspect rules) — this is a teaser, not a full synastry report.
 */

const ZODIAC = [
  { name: "Овен", symbol: "♈", element: "Огонь", longitude: 0, color: "oklch(0.65 0.15 27)" },
  { name: "Телец", symbol: "♉", element: "Земля", longitude: 30, color: "oklch(0.55 0.08 150)" },
  { name: "Близнецы", symbol: "♊", element: "Воздух", longitude: 60, color: "oklch(0.62 0.08 230)" },
  { name: "Рак", symbol: "♋", element: "Вода", longitude: 90, color: "oklch(0.60 0.10 260)" },
  { name: "Лев", symbol: "♌", element: "Огонь", longitude: 120, color: "oklch(0.65 0.15 27)" },
  { name: "Дева", symbol: "♍", element: "Земля", longitude: 150, color: "oklch(0.55 0.08 150)" },
  { name: "Весы", symbol: "♎", element: "Воздух", longitude: 180, color: "oklch(0.62 0.08 230)" },
  { name: "Скорпион", symbol: "♏", element: "Вода", longitude: 210, color: "oklch(0.60 0.10 260)" },
  { name: "Стрелец", symbol: "♐", element: "Огонь", longitude: 240, color: "oklch(0.65 0.15 27)" },
  { name: "Козерог", symbol: "♑", element: "Земля", longitude: 270, color: "oklch(0.55 0.08 150)" },
  { name: "Водолей", symbol: "♒", element: "Воздух", longitude: 300, color: "oklch(0.62 0.08 230)" },
  { name: "Рыбы", symbol: "♓", element: "Вода", longitude: 330, color: "oklch(0.60 0.10 260)" },
]

const SIGN_RU_TO_INDEX: Record<string, number> = {
  "Овен": 0, "Телец": 1, "Близнецы": 2, "Рак": 3, "Лев": 4, "Дева": 5,
  "Весы": 6, "Скорпион": 7, "Стрелец": 8, "Козерог": 9, "Водолей": 10, "Рыбы": 11,
}

const SIGN_EN_TO_RU: Record<string, string> = {
  Aries: "Овен", Taurus: "Телец", Gemini: "Близнецы", Cancer: "Рак",
  Leo: "Лев", Virgo: "Дева", Libra: "Весы", Scorpio: "Скорпион",
  Sagittarius: "Стрелец", Capricorn: "Козерог", Aquarius: "Водолей", Pisces: "Рыбы",
}

const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
  Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
}

const PLANET_RU: Record<string, string> = {
  Sun: "Солнце", Moon: "Луна", Venus: "Венера", Mars: "Марс",
}

// Map user's natal planet → its sign index (from DEMO_NATAL_RESPONSE)
function getUserPlanetSign(planetName: string): number {
  const p = DEMO_NATAL_RESPONSE.planets.find((p) => p.name === planetName)
  if (!p) return 0
  const ru = SIGN_EN_TO_RU[p.sign] ?? "Овен"
  return SIGN_RU_TO_INDEX[ru] ?? 0
}

type Aspect = {
  name: string
  orb: number
  angle: number
  tone: "harmonious" | "tense" | "soft"
}

const ASPECT_NAMES: Record<number, { name: string; tone: Aspect["tone"] }> = {
  0: { name: "Соединение", tone: "harmonious" },
  60: { name: "Секстиль", tone: "soft" },
  90: { name: "Квадрат", tone: "tense" },
  120: { name: "Трин", tone: "harmonious" },
  180: { name: "Оппозиция", tone: "tense" },
}

function computeAspect(longA: number, longB: number): Aspect | null {
  const diff = Math.abs(((longA - longB) % 360 + 540) % 360 - 180)
  for (const angle of [0, 60, 90, 120, 180]) {
    const orb = Math.abs(diff - angle)
    if (orb <= 8) {
      const meta = ASPECT_NAMES[angle]
      return { name: meta.name, tone: meta.tone, angle, orb: Math.round(orb * 10) / 10 }
    }
  }
  return null
}

type SynastryPair = {
  userPlanet: string
  partnerPlanet: string
  aspect: Aspect
  interpretation: string
}

function aspectInterpretation(up: string, pp: string, a: Aspect): string {
  if (up === "Sun" && pp === "Sun") {
    if (a.name === "Соединение") return "Сильное притяжение, общий ритм жизни"
    if (a.name === "Трин" || a.name === "Секстиль") return "Гармония целей и характера"
    if (a.name === "Квадрат" || a.name === "Оппозиция") return "Напряжение воли — вызов роста"
  }
  if (up === "Moon" && pp === "Moon") {
    if (a.name === "Соединение") return "Глубокое эмоциональное родство"
    if (a.name === "Трин" || a.name === "Секстиль") return "Лёгкость в быту и чувствах"
    if (a.name === "Квадрат" || a.name === "Оппозиция") return "Разные эмоциональные языки"
  }
  if ((up === "Venus" && pp === "Mars") || (up === "Mars" && pp === "Venus")) {
    if (a.name === "Соединение" || a.name === "Трин") return "Мощное притяжение, химия"
    if (a.name === "Квадрат" || a.name === "Оппозиция") return "Страсть и конфликты вперемешку"
  }
  if (up === "Sun" && pp === "Moon") {
    if (a.name === "Соединение" || a.name === "Трин") return "Классическая совместимость — ты светишь, он(а) чувствует"
  }
  if (up === "Venus" && pp === "Venus") {
    if (a.name === "Соединение" || a.name === "Трин") return "Общий вкус и ценности"
  }
  return a.tone === "harmonious"
    ? "Гармоничное взаимодействие"
    : a.tone === "tense"
      ? "Точка роста через напряжение"
      : "Лёгкое сотрудничество"
}

export function SynastryDemo() {
  const [open, setOpen] = useState(false)
  const [partnerSign, setPartnerSign] = useState(6) // Весы default

  const result = useMemo(() => {
    // User's Sun/Moon/Venus/Mars sign indices
    const userSun = getUserPlanetSign("Sun")
    const userMoon = getUserPlanetSign("Moon")
    const userVenus = getUserPlanetSign("Venus")
    const userMars = getUserPlanetSign("Mars")

    // Partner: assume Sun=Moon=Venus=Mars=chosen sign (simplified)
    const pSun = partnerSign
    const pMoon = partnerSign
    const pVenus = partnerSign
    const pMars = partnerSign

    const pairs: SynastryPair[] = []
    const combos: [string, number, string, number][] = [
      ["Sun", userSun, "Sun", pSun],
      ["Sun", userSun, "Moon", pMoon],
      ["Moon", userMoon, "Moon", pMoon],
      ["Venus", userVenus, "Venus", pVenus],
      ["Mars", userMars, "Mars", pMars],
      ["Venus", userVenus, "Mars", pMars],
      ["Mars", userMars, "Venus", pVenus],
    ]
    for (const [up, ul, pp, pl] of combos) {
      const longA = ul * 30 + 15
      const longB = pl * 30 + 15
      const aspect = computeAspect(longA, longB)
      if (aspect) {
        pairs.push({
          userPlanet: up,
          partnerPlanet: pp,
          aspect,
          interpretation: aspectInterpretation(up, pp, aspect),
        })
      }
    }

    // Score: harmonious +3, soft +2, tense -2
    let score = 50
    for (const p of pairs) {
      if (p.aspect.tone === "harmonious") score += 8
      else if (p.aspect.tone === "soft") score += 5
      else if (p.aspect.tone === "tense") score -= 4
    }
    // Element compatibility bonus
    const userEl = ZODIAC[userSun].element
    const partnerEl = ZODIAC[partnerSign].element
    if (userEl === partnerEl) score += 6
    if (
      (userEl === "Огонь" && partnerEl === "Воздух") ||
      (userEl === "Воздух" && partnerEl === "Огонь") ||
      (userEl === "Земля" && partnerEl === "Вода") ||
      (userEl === "Вода" && partnerEl === "Земля")
    ) {
      score += 4
    }
    score = Math.max(15, Math.min(98, score))

    let label: string
    if (score >= 80) label = "Сильная совместимость"
    else if (score >= 65) label = "Хорошая совместимость"
    else if (score >= 50) label = "Средняя совместимость"
    else if (score >= 35) label = "Нужны усилия"
    else label = "Сложное сочетание"

    return { pairs, score, label, userEl, partnerEl, userSun }
  }, [partnerSign])

  return (
    <>
      {/* Trigger card */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="group relative w-full overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20 p-4 text-left transition-all hover:border-primary/40 hover:shadow-md"
      >
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-30"
          style={{
            background:
              "radial-gradient(circle at 90% 10%, oklch(0.70 0.12 15 / 0.10), transparent 50%), radial-gradient(circle at 10% 90%, oklch(0.65 0.13 145 / 0.08), transparent 50%)",
          }}
        />
        <div className="relative flex items-center gap-3">
          <div className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-primary/10">
            <Users className="h-5 w-5 text-primary" strokeWidth={1.8} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="font-serif text-[15px] text-foreground">Синастрия</span>
              <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-[0.1em] text-primary">
                демо
              </span>
            </div>
            <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
              Совместимость с партнёром по знаку
            </p>
          </div>
          <ChevronRight className="h-4 w-4 flex-none text-muted-foreground transition-transform group-hover:translate-x-0.5" strokeWidth={1.8} />
        </div>
      </button>

      {/* Full overlay */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 backdrop-blur-sm sm:items-center"
            onClick={() => setOpen(false)}
          >
            <motion.div
              initial={{ y: 40, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 40, opacity: 0 }}
              transition={{ type: "spring", stiffness: 280, damping: 30 }}
              className="relative max-h-[88vh] w-full max-w-md overflow-y-auto rounded-t-3xl border border-border/60 bg-background p-5 sm:rounded-3xl"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Close */}
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-full bg-secondary/60 text-muted-foreground transition-colors hover:bg-secondary"
                aria-label="Закрыть"
              >
                <X className="h-4 w-4" strokeWidth={2} />
              </button>

              {/* Header */}
              <div className="mb-4 flex items-center gap-3 pr-10">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                  <Heart className="h-5 w-5 text-primary" strokeWidth={1.8} />
                </div>
                <div>
                  <h2 className="font-serif text-[20px] leading-tight text-foreground">Синастрия</h2>
                  <p className="text-[11.5px] text-muted-foreground">Совместимость по знаку Солнца</p>
                </div>
              </div>

              {/* Sign picker */}
              <div className="mb-4">
                <div className="mb-2 text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                  Знак партнёра
                </div>
                <div className="grid grid-cols-4 gap-1.5">
                  {ZODIAC.map((z, i) => (
                    <button
                      key={z.name}
                      type="button"
                      onClick={() => setPartnerSign(i)}
                      className={`flex flex-col items-center gap-0.5 rounded-xl border px-1 py-2 text-[10px] transition-all ${
                        partnerSign === i
                          ? "border-primary/50 bg-primary/10 text-foreground"
                          : "border-border/50 bg-card/40 text-muted-foreground hover:border-border"
                      }`}
                    >
                      <span className="text-[16px] leading-none" style={{ color: z.color }}>
                        {z.symbol}
                      </span>
                      <span className="leading-tight">{z.name}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Score */}
              <div className="mb-4 overflow-hidden rounded-2xl border border-border/50 bg-gradient-to-br from-secondary/30 to-card p-4">
                <div className="flex items-end justify-between">
                  <div>
                    <div className="text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                      Индекс совместимости
                    </div>
                    <div className="mt-0.5 font-serif text-[36px] leading-none tabular-nums text-foreground">
                      {result.score}
                      <span className="text-[14px] text-muted-foreground">/100</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary">
                      <Sparkles className="h-3 w-3" strokeWidth={2} />
                      {result.label}
                    </div>
                    <div className="mt-1 text-[10px] text-muted-foreground">
                      {ZODIAC[result.userSun].symbol} {ZODIAC[result.userSun].name} × {ZODIAC[partnerSign].symbol} {ZODIAC[partnerSign].name}
                    </div>
                  </div>
                </div>
                {/* Score bar */}
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-secondary">
                  <motion.div
                    className="shimmer-sweep h-full rounded-full"
                    style={{
                      background: `linear-gradient(90deg, oklch(0.65 0.15 60), oklch(0.65 0.13 145), oklch(0.62 0.08 230))`,
                    }}
                    initial={{ width: 0 }}
                    animate={{ width: `${result.score}%` }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                  />
                </div>
              </div>

              {/* Aspect pairs */}
              <div className="mb-3 text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                Ключевые аспекты ({result.pairs.length})
              </div>
              <div className="space-y-2">
                {result.pairs.map((p, i) => (
                  <motion.div
                    key={`${p.userPlanet}-${p.partnerPlanet}-${i}`}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center gap-3 rounded-xl border border-border/40 bg-card/60 px-3 py-2"
                  >
                    {/* Planet pair */}
                    <div className="flex items-center gap-1 text-[14px]">
                      <span title={PLANET_RU[p.userPlanet]}>{PLANET_SYMBOLS[p.userPlanet]}</span>
                      <span className="text-muted-foreground/50">·</span>
                      <span title={PLANET_RU[p.partnerPlanet]}>{PLANET_SYMBOLS[p.partnerPlanet]}</span>
                    </div>
                    {/* Aspect name */}
                    <div className="flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[12.5px] font-medium text-foreground">{p.aspect.name}</span>
                        <span className="text-[10px] tabular-nums text-muted-foreground">
                          орб {p.aspect.orb}°
                        </span>
                      </div>
                      <div className="text-[11px] leading-snug text-muted-foreground">
                        {p.interpretation}
                      </div>
                    </div>
                    {/* Tone icon */}
                    <span className="flex-none">
                      {p.aspect.tone === "harmonious" && (
                        <Check className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" strokeWidth={2.5} />
                      )}
                      {p.aspect.tone === "soft" && (
                        <Sparkles className="h-3.5 w-3.5 text-primary" strokeWidth={2} />
                      )}
                      {p.aspect.tone === "tense" && (
                        <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" strokeWidth={2} />
                      )}
                    </span>
                  </motion.div>
                ))}
              </div>

              {/* Element summary */}
              <div className="mt-4 rounded-xl bg-secondary/30 px-3 py-2.5 text-[11px] leading-relaxed text-muted-foreground">
                <span className="font-medium text-foreground">
                  {result.userEl} × {result.partnerEl}:
                </span>{" "}
                {elementSummary(result.userEl, result.partnerEl)}
              </div>

              <div className="mt-3 text-center text-[10px] text-muted-foreground/60">
                Демо-расчёт по знаку Солнца. Полная синастрия учитывает все планеты и дома.
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

function elementSummary(a: string, b: string): string {
  if (a === b) {
    const qualities: Record<string, string> = {
      "Огонь": "Общая искра и энтузиазм — легко зажигать друг друга.",
      "Земля": "Общая почва и практичность — стабильный союз.",
      "Воздух": "Общая стихия мысли — лёгкое общение и идеи.",
      "Вода": "Общая глубина чувств — интуитивное понимание.",
    }
    return qualities[a] ?? ""
  }
  const pairs: Record<string, string> = {
    "Огонь-Воздух": "Взаимное усиление — искра и ветер.",
    "Воздух-Огонь": "Взаимное усиление — ветер и искра.",
    "Земля-Вода": "Плодородное сочетание — почва и влага.",
    "Вода-Земля": "Плодородное сочетание — влага и почва.",
    "Огонь-Земля": "Разные ритмы — нужен мост между импульсом и устойчивостью.",
    "Огонь-Вода": "Кипение — страсть и эмоции требуют осторожности.",
    "Воздух-Земля": "Разные языки — мысль и форма учатся друг у друга.",
    "Воздух-Вода": "Лёгкость и глубина — интуиция и разум дополняют.",
  }
  return pairs[`${a}-${b}`] ?? "Сочетание стихий требует осознанности."
}
