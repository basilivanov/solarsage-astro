// ############################################################################
// AI_HEADER: MODULE_DAY_DATE_PAGE — isolated real-day and local timing-fixture routes.
// ROLE: Chooses a normal authenticated day branch or a development-only fixture
//       branch without allowing either branch's side-effect hooks into the other.
// ############################################################################

// START_MODULE_CONTRACT: M-DAY-DATE-PAGE
// purpose: Render /day/[date] with isolated real API/auth and local fixture branches.
// owns:
//   - app/(grace)/day/[date]/page.tsx
// inputs: route date and fixture query parameter.
// outputs: TodayScreen, loader, or error boundary.
// dependencies: next/navigation; useDay; useOnboarded; dev fixture hook; calendar API.
// side_effects: Normal branch authenticates, fetches day/calendar, and syncs onboarding;
//               fixture branch fetches only the local development fixture endpoint.
// emitted_logs: delegated to useDay and child modules.
// invariants:
//   - Fixture branch requires development mode, 2026-07-08, and fixture=three-horizon-timing.
//   - Normal branch never receives fixture data or a fixture feature flag.
//   - Fixture day navigation drops fixture query and returns to ordinary /day flow.
// failure_policy: Invalid date redirects in normal flow; request failures use ErrorBoundary.
// END_MODULE_CONTRACT: M-DAY-DATE-PAGE

// START_MODULE_MAP: M-DAY-DATE-PAGE
// public_entrypoints:
//   - DayPage
// semantic_blocks:
//   - ROUTE_SELECTION: exact local fixture eligibility.
//   - NORMAL_DAY_BRANCH: Telegram-authenticated real day and calendar loading.
//   - FIXTURE_DAY_BRANCH: development fixture-only loading without real APIs.
// owned_tests:
//   - e2e/dev-timing-fixture.spec.ts
// END_MODULE_MAP: M-DAY-DATE-PAGE

"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useParams, useRouter, useSearchParams } from "next/navigation"
import { TodayScreen } from "@/components/today/today-screen"
import { CosmicLoader } from "@/components/shared/cosmic-loader"
import { ErrorBoundary } from "@/components/grace/ErrorBoundary"
import { useDay } from "@/lib/grace/hooks/useDay"
import { useThreeHorizonTimingFixture } from "@/lib/dev-fixtures/use-three-horizon-timing-fixture"
import { useOnboarded } from "@/hooks/use-onboarded"
import { fromDateParam, toDateParam } from "@/lib/date"
import { TODAY } from "@/lib/today"
import { adaptTodayPayload } from "@/lib/adapters/today-payload"
import { getMonthCalendar } from "@/lib/api/calendar"
import type { CalendarLunarFields, TodayPayload } from "@/packages/contracts"

const TIMING_FIXTURE_DATE = "2026-07-08"

// START_BLOCK: ROUTE_SELECTION
export default function DayPage() {
  // START_FUNCTION_CONTRACT: F-M-DAY-DATE-PAGE.DayPage
  // purpose: Determine whether the request should load the isolated dev timing fixture or proceed with the authenticated normal day page flow.
  // inputs: URL route params, query search params, and process.env.NODE_ENV.
  // returns: TimingFixtureDayPage or NormalDayPage client components.
  // side_effects: none (routing decisions only).
  // emitted_logs: none.
  // error_behavior: bubbles up rendering errors to React/Next error boundary; does not handle them locally.
  // END_FUNCTION_CONTRACT: F-M-DAY-DATE-PAGE.DayPage
  const params = useParams()
  const searchParams = useSearchParams()
  const dateStr = params.date as string
  const useTimingFixture = process.env.NODE_ENV === "development"
    && dateStr === TIMING_FIXTURE_DATE
    && searchParams?.get("fixture") === "three-horizon-timing"

  return useTimingFixture ? <TimingFixtureDayPage dateStr={dateStr} /> : <NormalDayPage dateStr={dateStr} />
}
// END_BLOCK: ROUTE_SELECTION

function NormalDayPage({ dateStr }: { dateStr: string }) {
  const router = useRouter()
  const { setOnboarded } = useOnboarded()
  const selectedDate = useMemo(() => fromDateParam(dateStr) ?? TODAY, [dateStr])
  const { data, loading, error } = useDay(dateStr)
  const [calendarLunar, setCalendarLunar] = useState<CalendarLunarFields | null>(null)

  useEffect(() => {
    if (!fromDateParam(dateStr)) router.replace(`/day/${toDateParam(TODAY)}`)
  }, [dateStr, router])

  useEffect(() => {
    if (data) setOnboarded(true)
  }, [data, setOnboarded])

  useEffect(() => {
    let cancelled = false
    getMonthCalendar(selectedDate.getFullYear(), selectedDate.getMonth())
      .then((calendar) => {
        if (!cancelled) setCalendarLunar(calendar.days.find((item) => item.date === toDateParam(selectedDate))?.lunar ?? null)
      })
      .catch(() => {
        if (!cancelled) setCalendarLunar(null)
      })
    return () => {
      cancelled = true
    }
  }, [selectedDate])

  const onDateChange = useCallback((date: Date) => router.push(`/day/${toDateParam(date)}`), [router])
  return <LoadedDay data={data} loading={loading} error={error} selectedDate={selectedDate} calendarLunar={calendarLunar} onDateChange={onDateChange} />
}

function TimingFixtureDayPage({ dateStr }: { dateStr: string }) {
  const router = useRouter()
  const selectedDate = useMemo(() => fromDateParam(dateStr) ?? TODAY, [dateStr])
  const { data, loading, error } = useThreeHorizonTimingFixture()
  const onDateChange = useCallback((date: Date) => router.push(`/day/${toDateParam(date)}`), [router])

  return (
    <div data-testid="dev-timing-fixture">
      <LoadedDay
        data={data}
        loading={loading}
        error={error}
        selectedDate={selectedDate}
        calendarLunar={null}
        onDateChange={onDateChange}
        disableRemoteStatusFetch
      />
    </div>
  )
}

function LoadedDay({
  data,
  loading,
  error,
  selectedDate,
  calendarLunar,
  onDateChange,
  disableRemoteStatusFetch = false,
}: {
  data: TodayPayload | null
  loading: boolean
  error: Error | null
  selectedDate: Date
  calendarLunar: CalendarLunarFields | null
  onDateChange: (date: Date) => void
  disableRemoteStatusFetch?: boolean
}) {
  const [showLoader, setShowLoader] = useState(true)
  const dismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const ready = Boolean(data) && !loading

  useEffect(() => {
    if (ready) dismissTimer.current = setTimeout(() => setShowLoader(false), 600)
    else setShowLoader(true)
    return () => {
      if (dismissTimer.current) clearTimeout(dismissTimer.current)
    }
  }, [ready])

  if (error) return <ErrorBoundary error={error} title="Не удалось загрузить день" message={error.message} />
  if (showLoader || !data) return <CosmicLoader done={ready} />

  const { payload, access } = adaptTodayPayload(data, selectedDate)
  return (
    <TodayScreen
      selectedDate={selectedDate}
      access={access}
      payload={payload}
      calendarLunar={calendarLunar}
      onDateChange={onDateChange}
      importantToday={data.importantToday || []}
      disableRemoteStatusFetch={disableRemoteStatusFetch}
    />
  )
}
