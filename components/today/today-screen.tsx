
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

import { useRef } from "react"

import { DateHeader } from "./date-header"
import { TodayNotes } from "./today-notes"
import { DayReading } from "./day-reading"
import { WhyExpanded } from "./why-expanded"
import { WeekStrip } from "./week-strip"
import { DayChart } from "./day-chart"
import { DayEnergyMeter } from "./day-energy-meter"
import { DaySummaryCard } from "./day-summary-card"
import { Paywall } from "@/components/paywall"
import { TrialBanner } from "@/components/trial-banner"
import { TodayImportantAccordion } from "@/components/today-important-accordion"
import { addDays, sameDay, TODAY, type AdaptedTodayPayload, type AdaptedTopFlag } from "@/lib/today"
import { isDayAccessible, type AccessInfo } from "@/lib/access"
import type { TodayImportantEvent } from "@/packages/contracts"

type Props = {
  selectedDate: Date
  access: AccessInfo
  payload: AdaptedTodayPayload
  onDateChange: (_d: Date) => void
  importantToday?: TodayImportantEvent[]
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
}: Props) {
  const accessible = isDayAccessible(selectedDate, access)
  const isToday = sameDay(selectedDate, TODAY)

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
        className="flex-none"
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

      {/* Headline — заголовок/инсайт дня */}
      {payload.headline ? (
        <div className="px-5 pt-4 pb-2">
          <p className="text-center font-sans text-lg font-medium leading-snug text-foreground/90">
            {payload.headline}
          </p>
        </div>
      ) : null}

      {/* TopFlags — карточки топ-сигналов */}
      {payload.topFlags.length > 0 && (
        <div className="px-5 pb-2">
          <div className="flex flex-wrap gap-2">
            {payload.topFlags.map((flag: AdaptedTopFlag, idx: number) => (
              <div
                key={idx}
                className="flex-1 min-w-[140px] rounded-xl border border-border/40 bg-card/50 p-3"
              >
                <p className="text-xs font-semibold text-foreground/80 mb-0.5">
                  {flag.title}
                </p>
                <p className="text-[11px] leading-tight text-foreground/50">
                  {flag.summary}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {accessible ? (
        <div className="space-y-8 pb-8">
          {access.state === "trial" ? (
            <TrialBanner daysLeft={access.daysLeft} />
          ) : null}
          <TodayImportantAccordion items={importantToday || []} />
          <div className="section-rise section-rise-1">
            <DaySummaryCard
              date={selectedDate}
              dayStatus={payload.dayStatus}
              planetInfluences={payload.planetInfluences}
              sphereScores={payload.sphereScores}
            />
          </div>
          {!(importantToday && importantToday.length > 0) && <TodayNotes notes={payload.notes} />}
          <div className="section-rise section-rise-2">
            <DayChart
              chart={payload.dayChart}
              dateLabel={formatDateLabel(selectedDate)}
              dayStatus={payload.dayStatus}
            />
          </div>
          <div className="section-rise section-rise-3">
            <DayEnergyMeter
              planetInfluences={payload.planetInfluences}
              sphereScores={payload.sphereScores}
              dayStatus={payload.dayStatus}
            />
          </div>
          <DayReading paragraphs={payload.reading.paragraphs} />
          <WhyExpanded
            sections={payload.why}
            keyInsight={payload.keyInsight}
          />
          <WeekStrip
            selectedDate={selectedDate}
            access={access}
            onSelect={onDateChange}
          />
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

function formatDateLabel(d: Date): string {
  const months = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
  return `${d.getDate()} ${months[d.getMonth()]}`
}
