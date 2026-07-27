// ############################################################################
// AI_HEADER: MODULE_DAY_ZONE_INDICATOR
// ROLE: Visual zone indicator showing personal 14-day baseline band and today's score marker.
// DEPENDENCIES: react, lib/api/day
// GRACE_ANCHORS: [DAY_ZONE_INDICATOR]
// ############################################################################

// START_MODULE_CONTRACT: M-DAY-ZONE-INDICATOR
// purpose: Render relative day status zone indicator with baseline range band and today's marker.
// owns:
//   - components/today/day-zone-indicator.tsx
// inputs: relativeStatus (RelativeDayStatus | null | undefined)
// outputs: React element (or null if mode is absolute or history < 5 days)
// dependencies: lib/api/day
// side_effects: none (pure UI)
// emitted_logs: none
// failure_policy: returns null if relativeStatus missing or invalid
// END_MODULE_CONTRACT: M-DAY-ZONE-INDICATOR

// START_MODULE_MAP: M-DAY-ZONE-INDICATOR
// public_entrypoints:
//   - DayZoneIndicator
// semantic_blocks:
//   - ZONE_INDICATOR_RENDER: render baseline band and marker dot
// owned_tests:
//   - __tests__/today/day-summary-card.test.tsx
// END_MODULE_MAP: M-DAY-ZONE-INDICATOR

import React from "react"
import type { RelativeDayStatus } from "@/lib/api/day"

interface DayZoneIndicatorProps {
  relativeStatus?: RelativeDayStatus | null
}

// START_BLOCK: ZONE_INDICATOR_RENDER
export function DayZoneIndicator({ relativeStatus }: DayZoneIndicatorProps) {
  if (
    !relativeStatus ||
    relativeStatus.mode !== "relative" ||
    !relativeStatus.baseline ||
    relativeStatus.baseline.days < 5
  ) {
    return null
  }

  // Use support_marker or tension_marker (whichever is more expressive based on z-score)
  const isTenseDominant = Math.abs(relativeStatus.zTension) > Math.abs(relativeStatus.zSupport)
  const marker = isTenseDominant ? relativeStatus.tensionMarker : relativeStatus.supportMarker
  const markerPercent = Math.min(100, Math.max(0, Math.round(marker * 100)))

  // Band calculations for zone highlight
  const band = isTenseDominant ? relativeStatus.tensionBand : relativeStatus.supportBand
  const bandLow = band && band.length >= 2 ? Math.max(0, Math.min(100, band[0])) : 25
  const bandHigh = band && band.length >= 2 ? Math.max(0, Math.min(100, band[1])) : 75
  const bandWidth = Math.max(10, bandHigh - bandLow)

  return (
    <div
      data-testid="day-zone-indicator"
      className="mt-3.5 pt-3 border-t border-slate-100 dark:border-slate-800/60"
    >
      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1.5 font-medium">
        <span data-testid="day-zone-label">Ваша обычная зона</span>
        <span className="text-slate-700 dark:text-slate-200 font-semibold">{relativeStatus.label}</span>
      </div>

      {/* Track bar */}
      <div className="relative h-2.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
        {/* Normal zone band */}
        <div
          aria-hidden="true"
          className="absolute top-0 bottom-0 bg-emerald-500/20 dark:bg-emerald-400/25 rounded-sm"
          style={{
            left: `${bandLow}%`,
            width: `${bandWidth}%`,
          }}
        />

        {/* Marker dot */}
        <div
          aria-hidden="true"
          className="absolute top-1/2 -translate-y-1/2 w-3.5 h-3.5 bg-indigo-600 dark:bg-indigo-400 ring-2 ring-white dark:ring-slate-900 rounded-full shadow-sm transition-all duration-300"
          style={{
            left: `calc(${markerPercent}% - 7px)`,
          }}
        />
      </div>
    </div>
  )
}
// END_BLOCK: ZONE_INDICATOR_RENDER
