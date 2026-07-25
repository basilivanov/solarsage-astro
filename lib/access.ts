// ############################################################################
// AI_HEADER: MODULE_LIB_ACCESS
// ROLE: Access control utilities and access window boundary checks
// DEPENDENCIES: lib/today, lib/contracts/access
// GRACE_ANCHORS: [ACCESS_UTILITIES]
// SLICE: SLICE-FRONTEND-API-FACADES
// ############################################################################

// START_MODULE_CONTRACT: M-LIB-ACCESS
// purpose: Provide access state types and pure helper functions for date access boundary checks.
// owns:
//   - lib/access.ts
// inputs: date (Date), info (AccessInfo)
// outputs: boolean isDayAccessible result
// dependencies: lib/today, lib/contracts/access
// side_effects: none (pure)
// emitted_logs: none
// invariants:
//   - returns false when info.hasAccess is false
// failure_policy: none
// END_MODULE_CONTRACT: M-LIB-ACCESS

// START_MODULE_MAP: M-LIB-ACCESS
// public_entrypoints:
//   - isDayAccessible
// semantic_blocks:
//   - ACCESS_UTILITIES: isDayAccessible calculation helper
// owned_tests:
//   - __tests__/lib/access.test.ts
// END_MODULE_MAP: M-LIB-ACCESS

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

// START_BLOCK: ACCESS_UTILITIES
/** Доступен ли конкретный день внутри текущего окна доступа. */
export function isDayAccessible(date: Date, info: AccessInfo): boolean {
  // START_FUNCTION_CONTRACT: F-M-LIB-ACCESS.isDayAccessible
  // purpose: Check whether a specific Date is within active access window boundaries.
  // inputs: date (Date), info (AccessInfo)
  // returns: boolean
  // side_effects: none
  // error_behavior: returns false if info.hasAccess is false
  // END_FUNCTION_CONTRACT: F-M-LIB-ACCESS.isDayAccessible
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
// END_BLOCK: ACCESS_UTILITIES
