
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_CORRELATION_INIT
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for correlation-init.tsx behavior
// owns:
//   - components/correlation-init.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: Logging via v2 logging spine; React state management
// emitted_logs: v2 logging: logEvent/logStart/logSuccess/logFailure (frontend) or logger.* (backend)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
