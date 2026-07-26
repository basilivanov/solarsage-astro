// ############################################################################
// AI_HEADER: MODULE_CHART_GEOMETRY
// ROLE: Astrological chart geometry and coordinate math utilities
// DEPENDENCIES: none
// ############################################################################

// START_MODULE_CONTRACT: M-CHART-GEOMETRY
// purpose: Provide math functions for ecliptic longitude to angle, polar coordinates, and collision resolution.
// owns:
//   - lib/astro/chart-geometry.ts
// inputs: longitude (degrees), polar radius, center coordinates
// outputs: Cartesian points {x, y}, adjusted angles
// dependencies: none
// side_effects: none
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-CHART-GEOMETRY

// START_MODULE_MAP: M-CHART-GEOMETRY
// public_entrypoints:
//   - longitudeToAngle
//   - polarToCartesian
//   - resolveCollisionOffsets
//   - describeArc
// semantic_blocks: none
// owned_tests: none
// END_MODULE_MAP: M-CHART-GEOMETRY

/**
 * Convert ecliptic longitude (0..360, 0=Aries 0°) to SVG angle in degrees.
 * Standard astrological orientation: 0° Aries is at 9 o'clock (180° in SVG polar math), moving counter-clockwise.
 */
export function longitudeToAngle(longitude: number, ascendantOffset: number = 0): number {
  const normalizedLon = ((longitude - ascendantOffset) % 360 + 360) % 360
  return (180 - normalizedLon + 360) % 360
}

/**
 * Convert polar coordinates (radius, angle in degrees) to Cartesian {x, y}.
 */
export function polarToCartesian(
  centerX: number,
  centerY: number,
  radius: number,
  angleDegrees: number
): { x: number; y: number } {
  const angleInRadians = ((angleDegrees - 90) * Math.PI) / 180.0
  return {
    x: centerX + radius * Math.cos(angleInRadians),
    y: centerY + radius * Math.sin(angleInRadians),
  }
}

/**
 * Resolve overlapping planet angles by adding collision displacement offsets.
 */
export function resolveCollisionOffsets(
  longitudes: number[],
  minDistanceDegrees: number = 7.0
): number[] {
  if (longitudes.length <= 1) return [...longitudes]

  const items = longitudes.map((lon, idx) => ({ lon: ((lon % 360) + 360) % 360, idx }))
  items.sort((a, b) => a.lon - b.lon)

  const result = [...items]
  for (let pass = 0; pass < 5; pass++) {
    for (let i = 0; i < result.length; i++) {
      const j = (i + 1) % result.length
      let diff = (result[j].lon - result[i].lon + 360) % 360
      if (i === result.length - 1 && j === 0) {
        diff = (result[0].lon + 360 - result[i].lon) % 360
      }
      if (diff < minDistanceDegrees) {
        const overlap = minDistanceDegrees - diff
        result[i].lon = (result[i].lon - overlap / 2.0 + 360) % 360
        result[j].lon = (result[j].lon + overlap / 2.0) % 360
      }
    }
  }

  const output = new Array<number>(longitudes.length)
  for (const item of result) {
    output[item.idx] = item.lon
  }
  return output
}

/**
 * Describe SVG path string for an arc sector.
 */
export function describeArc(
  x: number,
  y: number,
  radius: number,
  startAngle: number,
  endAngle: number
): string {
  const start = polarToCartesian(x, y, radius, endAngle)
  const end = polarToCartesian(x, y, radius, startAngle)
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1"
  return ["M", start.x, start.y, "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y].join(" ")
}
