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
