/**
 * API-фасад для экрана дня.
 *
 * Компоненты ходят сюда, никогда напрямую в fixtures.
 * Переключение между fixtures и реальным API — через ENV.
 */

import { type TodayPayload } from "@/lib/contracts/today"
import { USE_FIXTURES } from "./config"

export type { TodayPayload }

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function getTodayPayload(date: Date): TodayPayload {
  if (USE_FIXTURES) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { getTodayPayloadFixture } = require("./today.fixtures") as typeof import("./today.fixtures")
    return getTodayPayloadFixture(date)
  }

  // Production stub
  throw new Error(
    "Production API not implemented. Set NEXT_PUBLIC_USE_FIXTURES=true for development."
  )
}

// ---------------------------------------------------------------------------
// Async version for future backend integration
// ---------------------------------------------------------------------------

export async function getTodayPayloadAsync(date: Date): Promise<TodayPayload> {
  if (USE_FIXTURES) {
    const { getTodayPayloadFixture } = await import("./today.fixtures")
    return getTodayPayloadFixture(date)
  }

  // TODO: Implement real API call
  throw new Error("Production API not implemented")
}
