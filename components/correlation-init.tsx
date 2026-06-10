"use client"

import { useEffect, useRef } from "react"
import { setCorrelationId, logEvent } from "@/lib/log"

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
      logEvent("system.startup", {}, { msg: `CORR ${id.slice(0, 8)} — все логи этой сессии`, slice: "W-SYSTEM", module: "M-CORRELATION-INIT", block: "INIT" })
    } catch {
      // crypto unavailable — logger will use null
    }
  }, [])

  return null
}
