"use client"

import { useRef } from "react"

import { DateHeader } from "./date-header"
import { TodayNotes } from "./today-notes"
import { DayReading } from "./day-reading"
import { WhyExpanded } from "./why-expanded"
import { WeekStrip } from "./week-strip"
import { Paywall } from "@/components/paywall"
import { TrialBanner } from "@/components/trial-banner"
import { TodayImportantAccordion } from "@/components/today-important-accordion"
import { addDays, sameDay, TODAY, type AdaptedTodayPayload } from "@/lib/today"
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

      {accessible ? (
        <div className="space-y-8 pb-8">
          {access.state === "trial" ? (
            <TrialBanner daysLeft={access.daysLeft} />
          ) : null}
          <TodayImportantAccordion items={importantToday || []} />
          {!(importantToday && importantToday.length > 0) && <TodayNotes notes={payload.notes} />}
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

