"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Star, Heart, ChevronRight, X, Sparkles, Check, AlertTriangle } from "lucide-react"
import { DEMO_NATAL_RESPONSE } from "@/lib/demo-data"

/**
 * CelebrityCompatibility — pick a famous person and see compatibility.
 *
 * Uses a small curated database of celebrities with their Sun/Moon/Venus/Mars
 * signs. Computes a synastry score against the user's natal chart using
 * the same aspect logic as SynastryDemo.
 */

type Celebrity = {
  name: string
  role: string
  emoji: string
  sun: number  // sign index 0-11
  moon: number
  venus: number
  mars: number
}

const CELEBRITIES: Celebrity[] = [
  { name: "Альберт Эйнштейн", role: "физик", emoji: "🧠", sun: 9, moon: 5, venus: 11, mars: 5 }, // Козерог
  { name: "Фрида Кало", role: "художница", emoji: "🎨", sun: 5, moon: 5, venus: 4, mars: 7 }, // Дева
  { name: "Моцарт", role: "композитор", emoji: "🎼", sun: 9, moon: 5, venus: 10, mars: 0 }, // Козерог
  { name: "Коко Шанель", role: "модельер", emoji: "👗", sun: 5, moon: 4, venus: 5, mars: 6 }, // Дева
  { name: "Стив Джобс", role: "предприниматель", emoji: "💻", sun: 5, moon: 3, venus: 5, mars: 3 }, // Дева
  { name: "Мария Кюри", role: "учёная", emoji: "⚛️", sun: 6, moon: 10, venus: 8, mars: 0 }, // Весы
  { name: "Чарли Чаплин", role: "актёр", emoji: "🎬", sun: 2, moon: 11, venus: 0, mars: 3 }, // Близнецы
  { name: "Агата Кристи", role: "писательница", emoji: "📚", sun: 5, moon: 0, venus: 5, mars: 4 }, // Дева
]

const ZODIAC = [
  { name: "Овен", symbol: "♈", element: "Огонь", color: "oklch(0.65 0.15 27)" },
  { name: "Телец", symbol: "♉", element: "Земля", color: "oklch(0.55 0.08 150)" },
  { name: "Близнецы", symbol: "♊", element: "Воздух", color: "oklch(0.62 0.08 230)" },
  { name: "Рак", symbol: "♋", element: "Вода", color: "oklch(0.60 0.10 260)" },
  { name: "Лев", symbol: "♌", element: "Огонь", color: "oklch(0.65 0.15 27)" },
  { name: "Дева", symbol: "♍", element: "Земля", color: "oklch(0.55 0.08 150)" },
  { name: "Весы", symbol: "♎", element: "Воздух", color: "oklch(0.62 0.08 230)" },
  { name: "Скорпион", symbol: "♏", element: "Вода", color: "oklch(0.60 0.10 260)" },
  { name: "Стрелец", symbol: "♐", element: "Огонь", color: "oklch(0.65 0.15 27)" },
  { name: "Козерог", symbol: "♑", element: "Земля", color: "oklch(0.55 0.08 150)" },
  { name: "Водолей", symbol: "♒", element: "Воздух", color: "oklch(0.62 0.08 230)" },
  { name: "Рыбы", symbol: "♓", element: "Вода", color: "oklch(0.60 0.10 260)" },
]

const SIGN_EN_TO_RU: Record<string, string> = {
  Aries: "Овен", Taurus: "Телец", Gemini: "Близнецы", Cancer: "Рак",
  Leo: "Лев", Virgo: "Дева", Libra: "Весы", Scorpio: "Скорпион",
  Sagittarius: "Стрелец", Capricorn: "Козерог", Aquarius: "Водолей", Pisces: "Рыбы",
}
const SIGN_RU_TO_INDEX: Record<string, number> = Object.fromEntries(
  ZODIAC.map((z, i) => [z.name, i]),
)

const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉", Moon: "☽", Venus: "♀", Mars: "♂",
}
const PLANET_RU: Record<string, string> = {
  Sun: "Солнце", Moon: "Луна", Venus: "Венера", Mars: "Марс",
}

const ASPECT_NAMES: Record<number, { name: string; tone: "harmonious" | "tense" | "soft" }> = {
  0: { name: "Соединение", tone: "harmonious" },
  60: { name: "Секстиль", tone: "soft" },
  90: { name: "Квадрат", tone: "tense" },
  120: { name: "Трин", tone: "harmonious" },
  180: { name: "Оппозиция", tone: "tense" },
}

function getUserSign(planet: string): number {
  const p = DEMO_NATAL_RESPONSE.planets.find((x) => x.name === planet)
  if (!p) return 0
  return SIGN_RU_TO_INDEX[SIGN_EN_TO_RU[p.sign] ?? "Овен"] ?? 0
}

function computeAspect(longA: number, longB: number) {
  const diff = Math.abs(((longA - longB) % 360 + 540) % 360 - 180)
  for (const angle of [0, 60, 90, 120, 180]) {
    const orb = Math.abs(diff - angle)
    if (orb <= 8) {
      return { ...ASPECT_NAMES[angle], angle, orb: Math.round(orb * 10) / 10 }
    }
  }
  return null
}

export function CelebrityCompatibility() {
  const [open, setOpen] = useState(false)
  const [selectedIdx, setSelectedIdx] = useState(0)

  const result = useMemo(() => {
    const celeb = CELEBRITIES[selectedIdx]
    const userSun = getUserSign("Sun")
    const userMoon = getUserSign("Moon")
    const userVenus = getUserSign("Venus")
    const userMars = getUserSign("Mars")

    const pairs: { up: string; pp: string; aspect: { name: string; tone: "harmonious" | "tense" | "soft"; orb: number } | null }[] = []
    const combos: [string, number, string, number][] = [
      ["Sun", userSun, "Sun", celeb.sun],
      ["Sun", userSun, "Moon", celeb.moon],
      ["Moon", userMoon, "Moon", celeb.moon],
      ["Venus", userVenus, "Venus", celeb.venus],
      ["Mars", userMars, "Mars", celeb.mars],
      ["Venus", userVenus, "Mars", celeb.mars],
      ["Mars", userMars, "Venus", celeb.venus],
    ]
    let score = 50
    let aspectCount = 0
    for (const [up, ul, pp, pl] of combos) {
      const a = computeAspect(ul * 30 + 15, pl * 30 + 15)
      pairs.push({ up, pp, aspect: a })
      if (a) {
        aspectCount++
        if (a.tone === "harmonious") score += 8
        else if (a.tone === "soft") score += 5
        else if (a.tone === "tense") score -= 4
      }
    }

    // Element bonus
    const userEl = ZODIAC[userSun].element
    const celebEl = ZODIAC[celeb.sun].element
    if (userEl === celebEl) score += 6
    if (
      (userEl === "Огонь" && celebEl === "Воздух") ||
      (userEl === "Воздух" && celebEl === "Огонь") ||
      (userEl === "Земля" && celebEl === "Вода") ||
      (userEl === "Вода" && celebEl === "Земля")
    ) {
      score += 4
    }
    score = Math.max(15, Math.min(98, score))

    let label: string
    if (score >= 80) label = "Сильное родство"
    else if (score >= 65) label = "Хорошая совместимость"
    else if (score >= 50) label = "Средняя совместимость"
    else if (score >= 35) label = "Разные ритмы"
    else label = "Сложное сочетание"

    return { celeb, pairs, score, label, userSun, aspectCount }
  }, [selectedIdx])

  return (
    <>
      {/* Trigger card */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="card-glow-hover group relative w-full overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20 p-4 text-left transition-all hover:border-primary/40 hover:shadow-md"
      >
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-30"
          style={{
            background: "radial-gradient(circle at 90% 10%, oklch(0.72 0.15 60 / 0.10), transparent 50%)",
          }}
        />
        <div className="relative flex items-center gap-3">
          <div className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-primary/10">
            <Star className="h-5 w-5 text-primary" strokeWidth={1.8} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="font-serif text-[15px] text-foreground">Совместимость с известными людьми</span>
              <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-[0.1em] text-primary">
                демо
              </span>
            </div>
            <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
              Узнай, с кем из великих у тебя резонанс
            </p>
          </div>
          <ChevronRight className="h-4 w-4 flex-none text-muted-foreground transition-transform group-hover:translate-x-0.5" strokeWidth={1.8} />
        </div>
      </button>

      {/* Modal */}
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
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-full bg-secondary/60 text-muted-foreground transition-colors hover:bg-secondary"
                aria-label="Закрыть"
              >
                <X className="h-4 w-4" strokeWidth={2} />
              </button>

              <div className="mb-4 flex items-center gap-3 pr-10">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                  <Heart className="h-5 w-5 text-primary" strokeWidth={1.8} />
                </div>
                <div>
                  <h2 className="font-serif text-[20px] leading-tight text-foreground">Совместимость</h2>
                  <p className="text-[11.5px] text-muted-foreground">с известными людьми</p>
                </div>
              </div>

              {/* Celebrity picker — horizontal scroll */}
              <div className="mb-4 -mx-1 overflow-x-auto px-1 pb-1">
                <div className="flex gap-2">
                  {CELEBRITIES.map((c, i) => (
                    <button
                      key={c.name}
                      type="button"
                      onClick={() => setSelectedIdx(i)}
                      className={`flex flex-none flex-col items-center gap-1 rounded-xl border px-3 py-2 text-center transition-all ${
                        selectedIdx === i
                          ? "border-primary/50 bg-primary/10"
                          : "border-border/50 bg-card/40 hover:border-border"
                      }`}
                      style={{ minWidth: "72px" }}
                    >
                      <span className="text-[20px] leading-none">{c.emoji}</span>
                      <span className="text-[10px] font-medium leading-tight text-foreground">{c.name.split(" ")[0]}</span>
                      <span className="text-[8px] leading-tight text-muted-foreground">{c.role}</span>
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
                      Ты {ZODIAC[result.userSun].symbol} {ZODIAC[result.userSun].name} × {result.celeb.emoji} {result.celeb.name}
                    </div>
                  </div>
                </div>
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

              {/* Aspects */}
              <div className="mb-3 text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                Аспекты ({result.aspectCount})
              </div>
              <div className="space-y-1.5">
                {result.pairs.map((p, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-xl border border-border/40 bg-card/60 px-3 py-2">
                    <div className="flex items-center gap-1 text-[14px]">
                      <span title={PLANET_RU[p.up]}>{PLANET_SYMBOLS[p.up]}</span>
                      <span className="text-muted-foreground/50">·</span>
                      <span title={PLANET_RU[p.pp]}>{PLANET_SYMBOLS[p.pp]}</span>
                    </div>
                    <div className="flex-1 text-[12px]">
                      {p.aspect ? (
                        <span className="flex items-center gap-1.5">
                          <span className="font-medium text-foreground">{p.aspect.name}</span>
                          <span className="text-[10px] tabular-nums text-muted-foreground">орб {p.aspect.orb}°</span>
                        </span>
                      ) : (
                        <span className="text-muted-foreground/60">нет аспекта</span>
                      )}
                    </div>
                    {p.aspect && (
                      <span className="flex-none">
                        {p.aspect.tone === "harmonious" && <Check className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" strokeWidth={2.5} />}
                        {p.aspect.tone === "soft" && <Sparkles className="h-3.5 w-3.5 text-primary" strokeWidth={2} />}
                        {p.aspect.tone === "tense" && <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" strokeWidth={2} />}
                      </span>
                    )}
                  </div>
                ))}
              </div>

              <div className="mt-3 rounded-xl bg-secondary/30 px-3 py-2 text-[11px] leading-relaxed text-muted-foreground">
                <span className="font-medium text-foreground">{result.celeb.name}</span> — {result.celeb.role}.
                Солнце в {ZODIAC[result.celeb.sun].symbol} {ZODIAC[result.celeb.sun].name},
                Луна в {ZODIAC[result.celeb.moon].symbol} {ZODIAC[result.celeb.moon].name}.
              </div>

              <div className="mt-3 text-center text-[10px] text-muted-foreground/60">
                Демо-расчёт по знакам Солнца, Луны, Венеры и Марса.
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
