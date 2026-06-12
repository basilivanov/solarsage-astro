
// ############################################################################
// AI_HEADER: MODULE_LIB_ACCESS
// ROLE: Lib — access.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Library: access
// owns:
//   - lib/access.ts
// inputs: Function arguments
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
