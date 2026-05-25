"use client"

import { useRef } from "react"

import { DateHeader } from "./date-header"
import { TodayNotes } from "./today-notes"
import { DayReading } from "./day-reading"
import { WhyExpanded } from "./why-expanded"
import { WeekStrip } from "./week-strip"
import { Paywall } from "@/components/paywall"
import { TrialBanner } from "@/components/trial-banner"
import { addDays, sameDay, TODAY, type TodayPayload } from "@/lib/today"
import { isDayAccessible, type AccessInfo } from "@/lib/access"

type Props = {
  selectedDate: Date
  access: AccessInfo
  payload: TodayPayload
  onDateChange: (d: Date) => void
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
}: Props) {
  const accessible = isDayAccessible(selectedDate, access)
  const isToday = sameDay(selectedDate, TODAY)

  // Навигация по дням: можно выходить только в пределах ±180 дней от сегодня
  const dayDiff = Math.round(
    (selectedDate.getTime() - TODAY.getTime()) / (1000 * 60 * 60 * 24),
  )
  const canPrev = dayDiff > -180
  const canNext = dayDiff < 180

  // --- Свайпы ---------------------------------------------------------------
  const start = useRef<{ x: number; y: number; id: number } | null>(null)

  function onPointerDown(e: React.PointerEvent<HTMLDivElement>) {
    if (e.pointerType === "mouse") return
    start.current = { x: e.clientX, y: e.clientY, id: e.pointerId }
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
      // touch-pan-y = вертикальный скролл остаётся у браузера, горизонтальные
      // жесты приходят к нам.
      className="touch-pan-y"
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
          <TodayNotes notes={payload.notes} />
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
    </div>
  )
}
