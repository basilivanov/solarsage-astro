
// ############################################################################
// AI_HEADER: MODULE_CALENDAR_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI page — component
// owns:
//   - app/(grace)/calendar/page.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
