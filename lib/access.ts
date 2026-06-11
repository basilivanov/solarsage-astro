
// ############################################################################
// AI_HEADER: MODULE_LIB_ACCESS
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/access.ts
// owns:
//   - lib/access.ts
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

// AI_HEADER
// module: M-LIB-ACCESS
// wave: W-2.7
// purpose: Access utilities (migrated from legacy)

/**
 * Access — типы и утилиты для работы с доступом.
 *
 * Типы теперь определены в контрактах (lib/contracts/access.ts).
 * Этот файл переэкспортирует их и содержит чистые утилиты.
 */

import { stripTime } from "./today"

// Реэкспорт типов из контрактов
export type { AccessState, AccessInfo } from "@/lib/contracts/access"
import type { AccessInfo } from "@/lib/contracts/access"

/** Доступен ли конкретный день внутри текущего окна доступа. */
export function isDayAccessible(date: Date, info: AccessInfo): boolean {
  if (!info.hasAccess) return false
  // If access window is set, check boundaries
  if (info.accessStart && info.accessEnd) {
    const t = stripTime(date).getTime()
    return (
      t >= stripTime(info.accessStart).getTime() &&
      t <= stripTime(info.accessEnd).getTime()
    )
  }
  // No window = unlimited access
  return true
}
