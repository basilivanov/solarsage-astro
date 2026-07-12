// ############################################################################
// AI_HEADER: MODULE_TODAY_TODAY_SCREEN
// ROLE: UI component — Reworked /day/[date] screen matching the mock-preview
//       visual oracle while keeping real SolarSage/API data.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-TODAY-SCREEN
// purpose: Renders the full /day/[date] screen with oracle-matched layout.
//          Composes DateHeader, access card, today-only check-in reminder,
//          DaySummaryCard, ConcreteDayAdvice, DayChart, reading, why-expanded,
//          week strip, AstroHistoryWidget, and bottom disclaimer. All data
//          flows through adaptTodayPayload — no fabricated astrology. V2 order is
//          summary → story → navigator → Why → chart → reading.
// owns:
//   - components/today/today-screen.tsx
// inputs:
//   - selectedDate, access, payload (AdaptedTodayPayload), calendarLunar,
//     onDateChange, importantToday, optional disableRemoteStatusFetch
// outputs:
//   - TSX layout with data-testid="today-screen" and data-state="ready|locked"
// dependencies:
//   - today/* components
//   - next/navigation useSearchParams for Why deeplink defaults
//   - @/components/paywall, @/components/trial-banner
//   - @/lib/today, @/lib/access
// side_effects: Pointer/touch swipe handlers; controlled V2 selection/Why state;
//               post-commit smooth scroll and focus for hero navigation; optional
//               suppression of WeekStrip remote status fetches for local fixtures.
// invariants:
//   - data-state reflects the real access state (ready=accessible, locked=inaccessible)
//   - data-testid attributes present on all major sections
//   - V2 sphere/Why state resets to the current deeplink default on date changes
//   - Loading/error states handled by the parent page
//   - disableRemoteStatusFetch defaults to false, preserving ordinary WeekStrip behavior
// failure_policy: renders gracefully; missing data hides sections silently
// END_MODULE_CONTRACT: M-TODAY-TODAY-SCREEN

// START_MODULE_MAP: M-TODAY-TODAY-SCREEN
// public_entrypoints:
//   - TodayScreen
// semantic_blocks:
//   - V2_NAVIGATION: useSearchParams deeplink defaults, controlled sphere/Why state, and post-commit scroll/focus.
//   - DAY_SWIPE: bounded pointer/touch date navigation.
//   - SCREEN_COMPOSITION: accessible and locked Today layouts with optional local fixture status suppression.
// owned_tests:
//   - __tests__/components/TodayScreen.test.tsx
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP: M-TODAY-TODAY-SCREEN

"use client"

import { useEffect, useRef, useState } from "react"
import { useSearchParams } from "next/navigation"

import { DateHeader } from "./date-header"
import { TodayNotes } from "./today-notes"
import { DayReading } from "./day-reading"
import { WhyExpanded } from "./why-expanded"
import { WeekStrip } from "./week-strip"
import { DayChart } from "./day-chart"
import { DaySummaryCard } from "./day-summary-card"
import { ConcreteDayAdvice } from "./concrete-day-advice"
import { ActivationEvidenceCard } from "./activation-evidence-card"
import { DevAuditDrawer } from "./dev-audit-drawer"
import { AstroHistoryWidget } from "./astro-history-widget"
import { Paywall } from "@/components/paywall"
import { TrialBanner } from "@/components/trial-banner"
import { YesterdayEchoLoader } from "@/components/checkin/yesterday-echo"
import { addDays, sameDay, TODAY, type AdaptedTodayPayload } from "@/lib/today"
import { isDayAccessible, type AccessInfo } from "@/lib/access"
import type { CalendarLunarFields, TodayImportantEvent } from "@/packages/contracts"

type Props = {
  selectedDate: Date
  access: AccessInfo
  payload: AdaptedTodayPayload
  calendarLunar?: CalendarLunarFields | null
  onDateChange: (_d: Date) => void
  importantToday?: TodayImportantEvent[]
  disableRemoteStatusFetch?: boolean
}

// Порог срабатывания свайпа — чтобы случайные жесты не перелистывали день
const SWIPE_THRESHOLD = 70
// Максимальное вертикальное смещение: если больше — это скролл, а не свайп
const SWIPE_MAX_VERTICAL = 50

// START_BLOCK: SCREEN_COMPOSITION
export function TodayScreen({
  selectedDate,
  access,
  payload,
  calendarLunar,
  onDateChange,
  importantToday,
  disableRemoteStatusFetch,
}: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-TODAY-SCREEN.TodayScreen
  // purpose: Render the main screen for a specific day, handling access check, checkin, summary, advice, reading, why-expanded, and week strip sections.
  // inputs: Props containing selectedDate, access state, adapted payload, calendar fields, callbacks, and flags.
  // returns: Main Today layout JSX.
  // side_effects: coordinates sub-components, triggers scroll and focus transitions on sphere select or why expand, sets up swipe navigation handlers.
  // emitted_logs: none (delegates logs to child hooks/methods).
  // error_behavior: bubbles rendering exceptions to the parent boundary; missing optional data is hidden gracefully.
  // END_FUNCTION_CONTRACT: F-M-TODAY-TODAY-SCREEN.TodayScreen
  const searchParams = useSearchParams()
  const accessible = isDayAccessible(selectedDate, access)
  const isToday = sameDay(selectedDate, TODAY)
  const [selectedSphereKey, setSelectedSphereKey] = useState<string | null>(null)
  const whyDeeplinkDefault = searchParams?.get("why") === "1"
  const [whyOpen, setWhyOpen] = useState(whyDeeplinkDefault)

  // Навигация по дням: можно выходить только в пределах ±180 дней от сегодня
  const dayDiff = Math.round(
    (selectedDate.getTime() - TODAY.getTime()) / (1000 * 60 * 60 * 24),
  )
  const canPrev = dayDiff > -180
  const canNext = dayDiff < 180

  // Screen state for test contract
  const screenState = accessible ? "ready" : "locked"

  // --- Свайпы (pointer + touch fallback для iOS WKWebView) ---------------
  const start = useRef<{ x: number; y: number; id: number } | null>(null)

  useEffect(() => {
    setSelectedSphereKey(null)
    setWhyOpen(whyDeeplinkDefault)
  }, [selectedDate, whyDeeplinkDefault])

  useEffect(() => {
    if (!selectedSphereKey) return
    scrollAndFocusSphere(selectedSphereKey)
  }, [selectedSphereKey])

  function scrollAndFocusSphere(key: string) {
    const schedule = window.requestAnimationFrame ?? ((callback: FrameRequestCallback) => window.setTimeout(() => callback(Date.now()), 0))
    schedule(() => {
      const navigator = document.querySelector('[data-testid="concrete-day-advice"]')
      navigator?.scrollIntoView({ behavior: "smooth", block: "start" })
      const sphereButton = Array.from(
        document.querySelectorAll<HTMLButtonElement>('[data-testid="concrete-day-advice-row"]'),
      ).find((element) => element.dataset.sphereKey === key)
      sphereButton?.focus({ preventScroll: true })
    })
  }

  function selectPersonalStorySphere(key: string) {
    if (key === selectedSphereKey) {
      scrollAndFocusSphere(key)
      return
    }
    setSelectedSphereKey(key)
  }

  useEffect(() => {
    if (!whyOpen) return
    scrollAndFocusWhy()
  }, [whyOpen])

  function scrollAndFocusWhy() {
    const schedule = window.requestAnimationFrame ?? ((callback: FrameRequestCallback) => window.setTimeout(() => callback(Date.now()), 0))
    schedule(() => {
      document.getElementById("why-expanded")?.scrollIntoView({ behavior: "smooth", block: "start" })
      document.getElementById("why-expanded-toggle")?.focus({ preventScroll: true })
    })
  }

  function openWhy() {
    if (whyOpen) {
      scrollAndFocusWhy()
      return
    }
    setWhyOpen(true)
  }

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
      data-state={screenState}
    >
      {/* Date Header with prev/next controls */}
      <div
        className="flex-none"
        style={{ paddingTop: "max(env(safe-area-inset-top), 0.5rem)" }}
        data-testid="day-header"
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
        <div className="space-y-5 pb-8">
          {/* Access / trial card */}
          {access.state === "trial" || access.state === "subscription" ? (
            <div data-testid="access-card">
              <TrialBanner daysLeft={access.daysLeft} />
            </div>
          ) : null}

          {isToday ? (
            <div className="px-5" data-testid="evening-checkin-reminder">
              <YesterdayEchoLoader />
            </div>
          ) : null}

          {/* Compact day summary card */}
          <DaySummaryCard
            date={selectedDate}
            dayStatus={payload.dayStatus}
            daySummary={payload.daySummary}
            humanFirst={Boolean(payload.v2)}
          />

          {/* Personal V2 story immediately below summary; null when V2 is absent. */}
          <ActivationEvidenceCard
            v2={payload.v2}
            concreteAdvice={payload.concreteAdvice}
            onSphereSelect={selectPersonalStorySphere}
            onWhyOpen={openWhy}
            headlineFallback={payload.headline}
          />

          <ConcreteDayAdvice
            concreteAdvice={payload.concreteAdvice}
            selectedKey={selectedSphereKey}
            onSelectedKeyChange={setSelectedSphereKey}
            onWhyOpen={openWhy}
          />

          {/* Why comes before technical visualization and reading in human-first V2. */}
          <WhyExpanded
            sections={payload.why}
            keyInsight={payload.keyInsight}
            v2={payload.v2}
            concreteAdvice={payload.concreteAdvice}
            onSphereSelect={selectPersonalStorySphere}
            open={payload.v2 ? whyOpen : undefined}
            onOpenChange={payload.v2 ? setWhyOpen : undefined}
          />

          <DayChart
            chart={payload.dayChart}
            dateLabel={formatDateLabel(selectedDate)}
            dayStatus={payload.dayStatus}
          />

          {/* Сегодня важно — hidden on /day in Wave 11 (intentional) */}

          {/* Day reading */}
          <DayReading paragraphs={payload.reading.paragraphs} />

          <DevAuditDrawer audit={payload.v2?.audit} />

          {/* Week strip navigation */}
          <WeekStrip
            selectedDate={selectedDate}
            access={access}
            onSelect={onDateChange}
            disableRemoteStatusFetch={disableRemoteStatusFetch}
          />

          <AstroHistoryWidget date={selectedDate} />
        </div>
      ) : (
        <div className="space-y-6 pb-8">
          {/* Access / paywall card */}
          <div data-testid="access-card">
            <Paywall
              title={
                isToday
                  ? "Твой персональный разбор на сегодня уже готов"
                  : "Этот день уже рассчитан для тебя"
              }
            />
          </div>

          {/* Preview notes */}
          <TodayNotes
            notes={payload.notes}
            limit={2}
            heading="Главное на этот день"
          />

          {/* Preview reading */}
          <DayReading paragraphs={payload.reading.paragraphs} preview />

          {/* Week strip */}
          <WeekStrip
            selectedDate={selectedDate}
            access={access}
            onSelect={onDateChange}
            disableRemoteStatusFetch={disableRemoteStatusFetch}
          />

          <AstroHistoryWidget date={selectedDate} />
        </div>
      )}

      {/* Footer disclaimer — stable across all states */}
      <footer className="px-5 pb-4 pt-2" data-testid="today-bottom-disclaimer">
        <p className="text-center font-sans text-[11px] leading-relaxed text-foreground/40">
          Данные показаны для ознакомления. Перед принятием важных решений проверяйте информацию.
        </p>
      </footer>
    </div>
  )
}
// END_BLOCK: SCREEN_COMPOSITION

function formatDateLabel(d: Date): string {
  const months = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
  return `${d.getDate()} ${months[d.getMonth()]}`
}
