
// ############################################################################
// AI_HEADER: MODULE_TODAY_TODAY_SCREEN
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TODAY-CALENDAR
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: today-screen.tsx
// owns:
//   - components/today/today-screen.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { useMemo, useRef } from "react"

import { DateHeader } from "./date-header"
import { TodayNotes } from "./today-notes"
import { DayReading } from "./day-reading"
import { WhyExpanded } from "./why-expanded"
import { WeekStrip } from "./week-strip"
import { DayChart, type ChartPlanet, type ChartHouse } from "./day-chart"
import { DayEnergyMeter, type EnergyItem } from "./day-energy-meter"
import { MoonPhaseWidget } from "./moon-phase-widget"
import { DailyAffirmation } from "./daily-affirmation"
import { AstroHistoryWidget } from "./astro-history-widget"
import { Paywall } from "@/components/paywall"
import { TrialBanner } from "@/components/trial-banner"
import { TodayImportantAccordion } from "@/components/today-important-accordion"
import { addDays, sameDay, TODAY, type AdaptedTodayPayload } from "@/lib/today"
import { isDayAccessible, type AccessInfo } from "@/lib/access"
import type { TodayImportantEvent, TodayPayload } from "@/packages/contracts"

type Props = {
  selectedDate: Date
  access: AccessInfo
  payload: AdaptedTodayPayload
  onDateChange: (_d: Date) => void
  importantToday?: TodayImportantEvent[]
  /** Raw API payload (for chart + energy meter derivation). */
  rawData?: TodayPayload | null
}

// Порог срабатывания свайпа — чтобы случайные жесты не перелистывали день
const SWIPE_THRESHOLD = 70
// Максимальное вертикальное смещение: если больше — это скролл, а не свайп
const SWIPE_MAX_VERTICAL = 50

export function TodayScreen({
  selectedDate,
  access,
  payload,
  onDateChange,
  importantToday,
  rawData,
}: Props) {
  const accessible = isDayAccessible(selectedDate, access)
  const isToday = sameDay(selectedDate, TODAY)

  // ── Derive chart + energy data from raw API payload (demo fixtures) ──
  const { chartPlanets, chartHouses, energyItems, dayStatusLabel } = useMemo(() => {
    return deriveChartAndEnergy(rawData, selectedDate)
  }, [rawData, selectedDate])

  // Навигация по дням: можно выходить только в пределах ±180 дней от сегодня
  const dayDiff = Math.round(
    (selectedDate.getTime() - TODAY.getTime()) / (1000 * 60 * 60 * 24),
  )
  const canPrev = dayDiff > -180
  const canNext = dayDiff < 180

  // --- Свайпы (pointer + touch fallback для iOS WKWebView) ---------------
  const start = useRef<{ x: number; y: number; id: number } | null>(null)

  function onPointerDown(e: React.PointerEvent<HTMLDivElement>) {
    start.current = { x: e.clientX, y: e.clientY, id: e.pointerId }
  }
  function onTouchStart(e: React.TouchEvent<HTMLDivElement>) {
    const t = e.touches[0]
    if (!t) return
    start.current = { x: t.clientX, y: t.clientY, id: t.identifier }
  }

  function onPointerUp(e: React.PointerEvent<HTMLDivElement>) {
    const s = start.current
    start.current = null
    if (!s || s.id !== e.pointerId) return

    const dx = e.clientX - s.x
    const dy = e.clientY - s.y

    if (Math.abs(dy) > SWIPE_MAX_VERTICAL) return
    if (Math.abs(dx) < Math.abs(dy)) return
    if (Math.abs(dx) < SWIPE_THRESHOLD) return

    if (dx < 0 && canNext) {
      onDateChange(addDays(selectedDate, 1))
    } else if (dx > 0 && canPrev) {
      onDateChange(addDays(selectedDate, -1))
    }
  }

  function onPointerCancel() {
    start.current = null
  }

  return (
    <div
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerCancel}
      onTouchStart={onTouchStart}
      onTouchEnd={(e) => {
        const s = start.current
        start.current = null
        if (!s) return
        const t = e.changedTouches[0]
        if (!t) return
        const dx = t.clientX - s.x
        const dy = t.clientY - s.y
        if (Math.abs(dy) > SWIPE_MAX_VERTICAL) return
        if (Math.abs(dx) < Math.abs(dy)) return
        if (Math.abs(dx) < SWIPE_THRESHOLD) return
        if (dx < 0 && canNext) onDateChange(addDays(selectedDate, 1))
        else if (dx > 0 && canPrev) onDateChange(addDays(selectedDate, -1))
      }}
      className="touch-pan-y"
      data-testid="today-screen"
    >
      <div
        className="cosmic-header-bg flex-none"
        style={{ paddingTop: "max(env(safe-area-inset-top), 0.5rem)" }}
      >
        <DateHeader
          date={selectedDate}
          onPrev={() => onDateChange(addDays(selectedDate, -1))}
          onNext={() => onDateChange(addDays(selectedDate, 1))}
          canPrev={canPrev}
          canNext={canNext}
          locked={!accessible}
        />
      </div>

      {accessible ? (
        <div className="space-y-8 pb-8">
          {access.state === "trial" ? (
            <TrialBanner daysLeft={access.daysLeft} />
          ) : null}
          <div className="section-rise section-rise-1">
            <MoonPhaseWidget date={selectedDate} />
          </div>
          <div className="section-rise section-rise-1">
            <TodayImportantAccordion items={importantToday || []} />
          </div>
          {!(importantToday && importantToday.length > 0) && <TodayNotes notes={payload.notes} />}
          {chartPlanets.length > 0 && (
            <div className="section-rise section-rise-2">
              <DayChart
                planets={chartPlanets}
                houses={chartHouses}
                dateLabel={formatDateLabel(selectedDate)}
                dayStatus={dayStatusLabel}
              />
            </div>
          )}
          {energyItems.length > 0 && (
            <div className="section-rise section-rise-3">
              <DayEnergyMeter items={energyItems} dayStatus={dayStatusLabel} />
            </div>
          )}
          <div className="section-rise section-rise-3">
            <DailyAffirmation
              date={selectedDate}
              dayStatus={dayStatusLabel}
              dominantPlanet={energyItems[0]?.name}
            />
          </div>
          <div className="section-rise section-rise-4">
            <DayReading paragraphs={payload.reading.paragraphs} />
          </div>
          <div className="section-rise section-rise-5">
            <WhyExpanded
              sections={payload.why}
              keyInsight={payload.keyInsight}
            />
          </div>
          <WeekStrip
            selectedDate={selectedDate}
            access={access}
            onSelect={onDateChange}
          />
          <div className="section-rise section-rise-5">
            <AstroHistoryWidget date={selectedDate} />
          </div>
        </div>
      ) : (
        <div className="space-y-6 pb-8">
          <TodayNotes
            notes={payload.notes}
            limit={2}
            heading="Главное на этот день"
          />
          <DayReading paragraphs={payload.reading.paragraphs} preview />
          <Paywall
            title={
              isToday
                ? "Твой персональный разбор на сегодня уже готов"
                : "Этот день уже рассчитан для тебя"
            }
          />
          <WeekStrip
            selectedDate={selectedDate}
            access={access}
            onSelect={onDateChange}
          />
        </div>
      )}

      {/* Disclaimer */}
      <footer className="px-5 pb-4 pt-2">
        <p className="text-center font-sans text-[11px] leading-relaxed text-foreground/40">
          Данные показаны для ознакомления. Перед принятием важных решений проверяйте информацию.
        </p>
      </footer>
    </div>
  )
}

// ── Helpers: derive chart + energy data from raw API payload ────────────

const SIGN_SYMBOLS_MAP: Record<string, string> = {
  Aries: "♈", Taurus: "♉", Gemini: "♊", Cancer: "♋", Leo: "♌", Virgo: "♍",
  Libra: "♎", Scorpio: "♏", Sagittarius: "♐", Capricorn: "♑", Aquarius: "♒", Pisces: "♓",
}

const PLANET_SYMBOLS_MAP: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
  Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
}

const PLANET_COLORS_MAP: Record<string, string> = {
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

// Static natal houses from DEMO_NATAL_RESPONSE — used as the house ring
// backdrop for the day chart. In production these would come from the
// transit calculation, but for the demo the natal houses are stable.
const NATAL_HOUSES = [
  { number: 1, cusp: 181.24, sign: "Libra" },
  { number: 2, cusp: 211.01, sign: "Scorpio" },
  { number: 3, cusp: 236.56, sign: "Scorpio" },
  { number: 4, cusp: 259.65, sign: "Sagittarius" },
  { number: 5, cusp: 299.47, sign: "Capricorn" },
  { number: 6, cusp: 334.67, sign: "Pisces" },
  { number: 7, cusp: 1.24, sign: "Aries" },
  { number: 8, cusp: 31.01, sign: "Taurus" },
  { number: 9, cusp: 56.56, sign: "Taurus" },
  { number: 10, cusp: 79.65, sign: "Gemini" },
  { number: 11, cusp: 119.47, sign: "Cancer" },
  { number: 12, cusp: 154.67, sign: "Virgo" },
]

// Static natal planet longitudes — used as the base. We add a small
// day-based offset so the chart visually shifts day-to-day in the demo.
const NATAL_PLANETS = [
  { name: "Sun", sign: "Capricorn", longitude: 294.5, house: 4 },
  { name: "Moon", sign: "Leo", longitude: 129.1, house: 11 },
  { name: "Mercury", sign: "Sagittarius", longitude: 267.6, house: 3 },
  { name: "Venus", sign: "Aquarius", longitude: 310.7, house: 5 },
  { name: "Mars", sign: "Sagittarius", longitude: 253.4, house: 3 },
  { name: "Jupiter", sign: "Cancer", longitude: 94.3, house: 10 },
  { name: "Saturn", sign: "Capricorn", longitude: 289.0, house: 4 },
]

function formatDateLabel(d: Date): string {
  const months = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
  return `${d.getDate()} ${months[d.getMonth()]}`
}

function deriveChartAndEnergy(rawData: TodayPayload | null | undefined, selectedDate: Date): {
  chartPlanets: ChartPlanet[]
  chartHouses: ChartHouse[]
  energyItems: EnergyItem[]
  dayStatusLabel: "steady" | "supportive" | "tense"
} {
  // Day-based pseudo-random offset so the chart shifts day-to-day
  const dayOffset = Math.floor(selectedDate.getTime() / (1000 * 60 * 60 * 24))
  const moonShift = (dayOffset * 13.1) % 360 // Moon moves ~13°/day
  const sunShift = (dayOffset * 0.98) % 360 // Sun moves ~1°/day

  const chartPlanets: ChartPlanet[] = NATAL_PLANETS.map((p) => {
    const shift = p.name === "Moon" ? moonShift : p.name === "Sun" ? sunShift : (dayOffset * 0.3) % 360
    const longitude = (p.longitude + shift) % 360
    return {
      name: p.name,
      symbol: PLANET_SYMBOLS_MAP[p.name] ?? "•",
      sign: p.sign,
      signSymbol: SIGN_SYMBOLS_MAP[p.sign] ?? "?",
      longitude,
      house: p.house,
    }
  })

  const chartHouses: ChartHouse[] = NATAL_HOUSES.map((h) => ({
    number: h.number,
    cusp: h.cusp,
    sign: h.sign,
    signSymbol: SIGN_SYMBOLS_MAP[h.sign] ?? "?",
  }))

  // Energy items: parse strength from topFlags summaries (format: "Орб: X°, сила: 0.94")
  const energyItems: EnergyItem[] = []
  const topFlags = (rawData as any)?.topFlags ?? []
  for (const flag of topFlags) {
    const title: string = flag?.title || flag?.iconName || ""
    // Extract planet name from title (e.g. "Солнце напротив Марса" → Sun, Mars)
    const planetMap: Record<string, string> = {
      "Солнце": "Sun",
      "Луна": "Moon",
      "Меркурий": "Mercury",
      "Венера": "Venus",
      "Марс": "Mars",
      "Юпитер": "Jupiter",
      "Сатурн": "Saturn",
      "Уран": "Uranus",
      "Нептун": "Neptune",
      "Плутон": "Pluto",
    }
    for (const [ru, en] of Object.entries(planetMap)) {
      if (title.includes(ru) && !energyItems.find((e) => e.name === en)) {
        const strengthMatch = (flag?.summary || "").match(/сила:\s*([\d.]+)/)
        const strength = strengthMatch ? parseFloat(strengthMatch[1]) : 0.5
        energyItems.push({
          name: en,
          symbol: PLANET_SYMBOLS_MAP[en] ?? "•",
          strength: Math.min(1, Math.max(0, strength)),
          color: PLANET_COLORS_MAP[en] ?? "oklch(0.55 0.05 295)",
        })
      }
    }
  }

  // Always include Sun + Moon even if no topFlags mention them
  if (!energyItems.find((e) => e.name === "Sun")) {
    energyItems.push({
      name: "Sun",
      symbol: "☉",
      strength: 0.6,
      color: PLANET_COLORS_MAP.Sun,
    })
  }
  if (!energyItems.find((e) => e.name === "Moon")) {
    energyItems.push({
      name: "Moon",
      symbol: "☽",
      strength: 0.55,
      color: PLANET_COLORS_MAP.Moon,
    })
  }

  const rawStatus = (rawData as any)?.dayStatus ?? "steady"
  const dayStatusLabel: "steady" | "supportive" | "tense" =
    rawStatus === "supportive" || rawStatus === "tense" ? rawStatus : "steady"

  return { chartPlanets, chartHouses, energyItems, dayStatusLabel }
}


