/**
 * API-фасад для каталога разборов.
 *
 * Компоненты ходят сюда, никогда напрямую в fixtures.
 * Переключение между fixtures и реальным API — через ENV.
 */

import type { ReadingsCatalog } from "@/lib/readings"
import { USE_FIXTURES } from "./config"

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function listReadings(): ReadingsCatalog {
  if (USE_FIXTURES) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { listReadingsFixture } = require("./readings.fixtures") as typeof import("./readings.fixtures")
    return listReadingsFixture()
  }

  // Production stub
  throw new Error(
    "Production API not implemented. Set NEXT_PUBLIC_USE_FIXTURES=true for development."
  )
}

// ---------------------------------------------------------------------------
// Async version for future backend integration
// ---------------------------------------------------------------------------

export async function listReadingsAsync(): Promise<ReadingsCatalog> {
  if (USE_FIXTURES) {
    const { listReadingsFixture } = await import("./readings.fixtures")
    return listReadingsFixture()
  }

  // TODO: Implement real API call
  throw new Error("Production API not implemented")
}
