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
  if (!info.hasAccess || !info.accessStart || !info.accessEnd) return false
  const t = stripTime(date).getTime()
  return (
    t >= stripTime(info.accessStart).getTime() &&
    t <= stripTime(info.accessEnd).getTime()
  )
}
