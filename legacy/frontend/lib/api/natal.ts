/**
 * API-фасад для разбора натальной карты.
 *
 * Контракт фиксирован в `lib/contracts/natal.ts` (`schemaVersion: "natal/v1"`).
 * Переключение между fixtures и реальным API — через ENV.
 */

import { type NatalReport, type ReportSection } from "@/lib/contracts/natal"
import { USE_FIXTURES } from "./config"

export type { NatalReport, ReportSection }

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function getNatalReport(): NatalReport {
  if (USE_FIXTURES) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { getNatalReportFixture } = require("./natal.fixtures") as typeof import("./natal.fixtures")
    return getNatalReportFixture()
  }

  // Production stub
  throw new Error(
    "Production API not implemented. Set NEXT_PUBLIC_USE_FIXTURES=true for development."
  )
}

export function getNatalSection(id: string) {
  if (USE_FIXTURES) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { getNatalSectionFixture } = require("./natal.fixtures") as typeof import("./natal.fixtures")
    return getNatalSectionFixture(id)
  }

  // Production stub
  throw new Error(
    "Production API not implemented. Set NEXT_PUBLIC_USE_FIXTURES=true for development."
  )
}

// ---------------------------------------------------------------------------
// Async versions for future backend integration
// ---------------------------------------------------------------------------

export async function getNatalReportAsync(): Promise<NatalReport> {
  if (USE_FIXTURES) {
    const { getNatalReportFixture } = await import("./natal.fixtures")
    return getNatalReportFixture()
  }

  // TODO: Implement real API call
  throw new Error("Production API not implemented")
}

export async function getNatalSectionAsync(id: string) {
  if (USE_FIXTURES) {
    const { getNatalSectionFixture } = await import("./natal.fixtures")
    return getNatalSectionFixture(id)
  }

  // TODO: Implement real API call
  throw new Error("Production API not implemented")
}
