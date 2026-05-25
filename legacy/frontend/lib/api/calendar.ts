/**
 * API-фасад для календаря.
 *
 * Компоненты ходят сюда, никогда напрямую в fixtures.
 * Переключение между fixtures и реальным API — через ENV.
 *
 * Когда появится бэкенд:
 *
 *   async function fetchMonthStatuses(year, month) {
 *     const res = await fetch(`${API_BASE_URL}/calendar/${year}-${month + 1}`)
 *     if (!res.ok) throw new Error(...)
 *     return validateDayStatusMap(await res.json())
 *   }
 */

import {
  type DayStatus,
  type DayStatusMap,
} from "@/lib/contracts/calendar"
import { USE_FIXTURES } from "./config"

export type { DayStatus, DayStatusMap }

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function getDayStatus(date: Date): DayStatus {
  if (USE_FIXTURES) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { getDayStatusFixture } = require("./calendar.fixtures") as typeof import("./calendar.fixtures")
    return getDayStatusFixture(date)
  }

  // Production stub
  throw new Error(
    "Production API not implemented. Set NEXT_PUBLIC_USE_FIXTURES=true for development."
  )
}

export function getMonthStatuses(year: number, month: number): DayStatusMap {
  if (USE_FIXTURES) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { getMonthStatusesFixture } = require("./calendar.fixtures") as typeof import("./calendar.fixtures")
    return getMonthStatusesFixture(year, month)
  }

  // Production stub
  throw new Error(
    "Production API not implemented. Set NEXT_PUBLIC_USE_FIXTURES=true for development."
  )
}

// ---------------------------------------------------------------------------
// Async versions for future backend integration
// ---------------------------------------------------------------------------

export async function getDayStatusAsync(date: Date): Promise<DayStatus> {
  if (USE_FIXTURES) {
    const { getDayStatusFixture } = await import("./calendar.fixtures")
    return getDayStatusFixture(date)
  }

  // TODO: Implement real API call
  throw new Error("Production API not implemented")
}

export async function getMonthStatusesAsync(
  year: number,
  month: number,
): Promise<DayStatusMap> {
  if (USE_FIXTURES) {
    const { getMonthStatusesFixture } = await import("./calendar.fixtures")
    return getMonthStatusesFixture(year, month)
  }

  // TODO: Implement real API call
  throw new Error("Production API not implemented")
}
