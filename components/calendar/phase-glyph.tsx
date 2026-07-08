// ############################################################################
// AI_HEADER: MODULE_CALENDAR_PHASE_GLYPH — backend-driven SVG moon phase glyphs.
// ROLE: Presentation-only lunar phase SVG component for calendar surfaces.
// ############################################################################

// START_MODULE_CONTRACT: M-CALENDAR-PHASE-GLYPH
// purpose: Render oracle-style SVG moon phase glyphs from backend phaseIndex
//   values without computing lunar facts from dates.
// owns:
//   - components/calendar/phase-glyph.tsx
// inputs:
//   - phaseIndex: backend CalendarLunarFields.phaseIndex.
//   - size: desired SVG size in CSS pixels.
// outputs: React SVG element for the phase glyph and stable phase colors.
// dependencies: React JSX only.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - never imports frontend lunar date calculation helpers.
//   - unknown phase indexes render a neutral crescent fallback.
// failure_policy: invalid phaseIndex falls back to waning crescent presentation.
// END_MODULE_CONTRACT: M-CALENDAR-PHASE-GLYPH

// START_MODULE_MAP: M-CALENDAR-PHASE-GLYPH
// public_entrypoints:
//   - PhaseGlyph
//   - phaseColor
//   - normalizePhaseIndex
// semantic_blocks:
//   - PHASE_SVG_PRESENTATION: phaseIndex to SVG shape/color presentation
// owned_tests:
//   - __tests__/components/CalendarScreen.test.tsx
//   - e2e/mock-visual/calendar.spec.ts
// END_MODULE_MAP: M-CALENDAR-PHASE-GLYPH

const PHASE_COLORS: Record<number, string> = {
  0: "oklch(0.30 0.02 295)",
  1: "oklch(0.60 0.04 295)",
  2: "oklch(0.55 0.06 305)",
  3: "oklch(0.65 0.05 305)",
  4: "oklch(0.72 0.08 85)",
  5: "oklch(0.65 0.05 305)",
  6: "oklch(0.55 0.06 305)",
  7: "oklch(0.60 0.04 295)",
}

// START_BLOCK: PHASE_SVG_PRESENTATION
export function normalizePhaseIndex(phaseIndex: number | null | undefined): number {
  // START_FUNCTION_CONTRACT: F-M-CALENDAR-PHASE-GLYPH.normalizePhaseIndex
  // purpose: Clamp nullable backend phaseIndex values to a renderable enum index.
  // inputs: phaseIndex — backend phase index, possibly null/unknown.
  // returns: number — 0..7 phase index, defaulting to 7 for unknown values.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: never throws for invalid input.
  // END_FUNCTION_CONTRACT: F-M-CALENDAR-PHASE-GLYPH.normalizePhaseIndex
  return typeof phaseIndex === "number" && phaseIndex >= 0 && phaseIndex <= 7
    ? phaseIndex
    : 7
}

export function phaseColor(phaseIndex: number | null | undefined): string {
  // START_FUNCTION_CONTRACT: F-M-CALENDAR-PHASE-GLYPH.phaseColor
  // purpose: Return the oracle-style accent color for a backend phase index.
  // inputs: phaseIndex — backend phase index, possibly null/unknown.
  // returns: string — CSS oklch color.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: falls back to waning crescent color.
  // END_FUNCTION_CONTRACT: F-M-CALENDAR-PHASE-GLYPH.phaseColor
  return PHASE_COLORS[normalizePhaseIndex(phaseIndex)]
}

export function PhaseGlyph({
  phaseIndex,
  size = 16,
  className,
}: {
  phaseIndex: number | null | undefined
  size?: number
  className?: string
}) {
  // START_FUNCTION_CONTRACT: F-M-CALENDAR-PHASE-GLYPH.PhaseGlyph
  // purpose: Render an oracle-style two-tone SVG moon glyph for a backend phase index.
  // inputs:
  //   - phaseIndex — backend phase index, possibly null/unknown.
  //   - size — square SVG size in CSS pixels.
  //   - className — optional className for layout/color inheritance.
  // returns: JSX.Element — aria-hidden decorative phase glyph.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: invalid phase index renders the fallback normalized phase.
  // END_FUNCTION_CONTRACT: F-M-CALENDAR-PHASE-GLYPH.PhaseGlyph
  const index = normalizePhaseIndex(phaseIndex)
  const r = size / 2
  const litColor = "oklch(0.92 0.015 85)"
  const darkColor = "oklch(0.35 0.02 295)"
  const strokeColor = "oklch(0.5 0.02 295)"

  if (index === 0) {
    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className={className} aria-hidden>
        <circle cx={r} cy={r} r={r - 0.5} fill={darkColor} />
        <circle cx={r} cy={r} r={r - 0.5} fill="none" stroke={strokeColor} strokeWidth={0.5} strokeOpacity={0.4} />
      </svg>
    )
  }

  if (index === 4) {
    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className={className} aria-hidden>
        <circle cx={r} cy={r} r={r - 0.5} fill={litColor} />
        {size >= 16 ? (
          <>
            <circle cx={r - size * 0.15} cy={r - size * 0.1} r={size * 0.08} fill="oklch(0.82 0.015 85)" opacity={0.5} />
            <circle cx={r + size * 0.12} cy={r + size * 0.08} r={size * 0.1} fill="oklch(0.82 0.015 85)" opacity={0.4} />
          </>
        ) : null}
      </svg>
    )
  }

  if (index === 2 || index === 6) {
    const litOnRight = index === 2
    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className={className} aria-hidden>
        <circle cx={r} cy={r} r={r - 0.5} fill={darkColor} />
        <path
          d={litOnRight
            ? `M ${r} 0.5 A ${r - 0.5} ${r - 0.5} 0 0 1 ${r} ${size - 0.5} Z`
            : `M ${r} 0.5 A ${r - 0.5} ${r - 0.5} 0 0 0 ${r} ${size - 0.5} Z`}
          fill={litColor}
        />
      </svg>
    )
  }

  const isWaxing = index < 4
  const isCrescent = index === 1 || index === 7
  const illumination = isCrescent ? 25 : 75
  const terminatorRx = r * Math.abs(Math.cos((illumination / 100) * Math.PI))
  const litOnRight = isWaxing
  const clipId = `phase-glyph-clip-${index}-${size}`

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className={className} aria-hidden>
      <circle cx={r} cy={r} r={r - 0.5} fill={darkColor} />
      <defs>
        <clipPath id={clipId}>
          {isCrescent ? (
            <path
              d={`${litOnRight
                ? `M ${r} 0.5 A ${r - 0.5} ${r - 0.5} 0 0 1 ${r} ${size - 0.5}`
                : `M ${r} 0.5 A ${r - 0.5} ${r - 0.5} 0 0 0 ${r} ${size - 0.5}`} A ${terminatorRx} ${r - 0.5} 0 0 ${litOnRight ? 1 : 0} ${r} 0.5 Z`}
            />
          ) : (
            <path
              d={`${litOnRight
                ? `M ${r} 0.5 A ${r - 0.5} ${r - 0.5} 0 0 1 ${r} ${size - 0.5}`
                : `M ${r} 0.5 A ${r - 0.5} ${r - 0.5} 0 0 0 ${r} ${size - 0.5}`} A ${terminatorRx} ${r - 0.5} 0 0 ${litOnRight ? 0 : 1} ${r} 0.5 Z`}
            />
          )}
        </clipPath>
      </defs>
      <circle cx={r} cy={r} r={r - 0.5} fill={litColor} clipPath={`url(#${clipId})`} />
    </svg>
  )
}
// END_BLOCK: PHASE_SVG_PRESENTATION
