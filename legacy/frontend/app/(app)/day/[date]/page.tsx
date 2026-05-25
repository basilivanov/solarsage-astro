"use client"

import { use, useCallback, useEffect, useMemo } from "react"
import { useRouter } from "next/navigation"

import { TodayScreen } from "@/components/today/today-screen"
import { useAccess } from "@/hooks/use-access"
import { fromDateParam, toDateParam } from "@/lib/date"
import { TODAY } from "@/lib/today"
import { getTodayPayload } from "@/lib/api/today"

type Params = { date: string }

/**
 * Страница дня: /day/YYYY-MM-DD.
 *
 * Дата — источник истины в URL, значит deeplink работает «из коробки».
 * Стрелки ←/→ и плашки недели переписывают URL через router.push, а
 * не локальный state — поэтому back в Telegram Mini App отлистывает
 * историю дней корректно.
 *
 * Payload берём через getTodayPayload(date). Сейчас это mock, позже —
 * fetch/SWR к /api/day/[date]. Компонент TodayScreen уже не знает,
 * откуда данные, и работает в обоих режимах.
 */
export default function DayPage({ params }: { params: Promise<Params> }) {
  const { date } = use(params)
  const router = useRouter()
  const { access } = useAccess()

  const selectedDate = useMemo(() => fromDateParam(date), [date])

  // Если кто-то подсунул кривую дату в URL — чиним на сегодня
  useEffect(() => {
    if (!selectedDate) {
      router.replace(`/day/${toDateParam(TODAY)}`)
    }
  }, [selectedDate, router])

  const payload = useMemo(
    () => (selectedDate ? getTodayPayload(selectedDate) : null),
    [selectedDate],
  )

  const onDateChange = useCallback(
    (d: Date) => {
      router.push(`/day/${toDateParam(d)}`)
    },
    [router],
  )

  if (!selectedDate || !payload) {
    return null
  }

  return (
    <TodayScreen
      selectedDate={selectedDate}
      access={access}
      payload={payload}
      onDateChange={onDateChange}
    />
  )
}
