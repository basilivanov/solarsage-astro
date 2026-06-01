"use client"

import { useEffect, useRef } from "react"
import { setCorrelationId } from "@/lib/log"

/**
 * Инициализирует correlation ID для всей сессии.
 * Генерирует UUIDv4 и устанавливает его глобально для логгера.
 * ID живёт в рамках одной загрузки страницы.
 */
export function CorrelationInit() {
  const done = useRef(false)

  useEffect(() => {
    if (done.current) return
    done.current = true

    try {
      const id = crypto.randomUUID()
      setCorrelationId(id)
      console.log(`%c📎 CORR ${id.slice(0, 8)} %c— все логи этой сессии`,
        'color:#a78bfa', 'color:inherit')
    } catch {
      // crypto unavailable — logger will use null
    }
  }, [])

  return null
}
