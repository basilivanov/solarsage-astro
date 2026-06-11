
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_CORRELATION_INIT
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/correlation-init.tsx
// owns:
//   - components/correlation-init.tsx
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

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
