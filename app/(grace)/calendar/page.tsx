
// ############################################################################
// AI_HEADER: APP_CALENDAR_PAGE — monthly calendar route and day-navigation adapter.
// ROLE: Client Next.js page called by /calendar; binds access state and converts CalendarScreen date selections into canonical day routes.
// ############################################################################

// START_MODULE_CONTRACT: M-APP-CALENDAR-PAGE
// purpose: Render the monthly calendar route and bridge selected Date values to /day/YYYY-MM-DD navigation.
// owns:
//   - app/(grace)/calendar/page.tsx
// inputs: useAccess result and Date values emitted by CalendarScreen.onOpenDay.
// outputs: CalendarScreen with access and onOpenDay props.
// dependencies: React useCallback; next/navigation; CalendarScreen; useAccess; toDateParam.
// side_effects: Reads access hook state and performs client router.push navigation.
// emitted_logs: none.
// invariants:
//   - Selected days navigate only through toDateParam to /day/YYYY-MM-DD.
//   - Calendar rendering and per-day access remain owned by CalendarScreen/API payloads.
// failure_policy: Rendering/hook failures bubble to the route boundary; navigation failures are delegated to Next router.
// END_MODULE_CONTRACT: M-APP-CALENDAR-PAGE

// START_MODULE_MAP: M-APP-CALENDAR-PAGE
// public_entrypoints:
//   - CalendarPage (default).
// semantic_blocks:
//   - ACCESS_BINDING: obtain current access read model.
//   - DAY_NAVIGATION: create stable canonical day-route callback.
//   - PAGE_COMPOSITION: render CalendarScreen.
// owned_tests:
//   - e2e/calendar.spec.ts
// END_MODULE_MAP: M-APP-CALENDAR-PAGE
"use client"

import { useCallback } from "react"
import { useRouter } from "next/navigation"

import { CalendarScreen } from "@/components/calendar/calendar-screen"
import { useAccess } from "@/hooks/use-access"
import { toDateParam } from "@/lib/date"

/**
 * /calendar — помесячная сетка.
 * «Открыть день» переводит на /day/YYYY-MM-DD, так что навигация
 * ложится в обычный браузерный back-stack.
 */
export default function CalendarPage() {
  const router = useRouter()
  const { access } = useAccess()

  const onOpenDay = useCallback(
    (d: Date) => {
      router.push(`/day/${toDateParam(d)}`)
    },
    [router],
  )

  return <CalendarScreen access={access} onOpenDay={onOpenDay} />
}
