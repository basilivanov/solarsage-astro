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

  // Axis normalization: markers are already 0..1 fractions of the backend's
  // (mean+std)*1.5 scale; bands arrive in RAW score units and must be divided
  // by the same axis max. The bar's axis is EASINESS (left = тяжелее,
  // right = легче), so tension-dominant days are mirrored: more tension = left.
  const baselineMean = isTenseDominant
    ? relativeStatus.baseline.tensionMean
    : relativeStatus.baseline.supportMean
  const baselineStd = isTenseDominant
    ? relativeStatus.baseline.tensionStd
    : relativeStatus.baseline.supportStd
  const axisMax = Math.max(1.0, (baselineMean + baselineStd) * 1.5)

  const rawBand = isTenseDominant ? relativeStatus.tensionBand : relativeStatus.supportBand
  const clamp01 = (v: number) => Math.min(1, Math.max(0, v))
  let bandLow = rawBand && rawBand.length >= 2 ? clamp01(rawBand[0] / axisMax) : 0.25
  let bandHigh = rawBand && rawBand.length >= 2 ? clamp01(rawBand[1] / axisMax) : 0.75
  let marker01 = clamp01(isTenseDominant ? relativeStatus.tensionMarker : relativeStatus.supportMarker)

  if (isTenseDominant) {
    marker01 = 1 - marker01
    ;[bandLow, bandHigh] = [1 - bandHigh, 1 - bandLow]
  }

  const markerPercent = Math.round(marker01 * 100)
  const bandLowPct = Math.round(bandLow * 100)
  const bandWidthPct = Math.max(10, Math.round((bandHigh - bandLow) * 100))
  // "Обычно" anchor sits over the band center, clamped away from the edges
  const bandCenter = Math.min(88, Math.max(12, bandLowPct + bandWidthPct / 2))

  return (
    <div
      data-testid="day-zone-indicator"
      className="mt-3.5 pt-3 border-t border-slate-100 dark:border-slate-800/60"
    >
      {/* Track bar: green band = your usual range, dot = today */}
      <div className="relative h-2.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
        {/* Normal zone band */}
        <div
          aria-hidden="true"
          className="absolute top-0 bottom-0 bg-emerald-500/20 dark:bg-emerald-400/25 rounded-sm"
          style={{
            left: `${bandLowPct}%`,
            width: `${bandWidthPct}%`,
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

      {/* Axis anchors: left = harder than usual, right = easier */}
      <div className="relative mt-1.5 h-4 text-[11px] font-medium text-slate-400 dark:text-slate-500">
        <span className="absolute left-0">Тяжелее</span>
        <span
          data-testid="day-zone-label"
          className="absolute -translate-x-1/2"
          style={{ left: `${bandCenter}%` }}
        >
          Обычно
        </span>
        <span className="absolute right-0">Легче</span>
      </div>
    </div>
  )
}
// END_BLOCK: ZONE_INDICATOR_RENDER
