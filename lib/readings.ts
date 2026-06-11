
// ############################################################################
// AI_HEADER: MODULE_LIB_READINGS
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/readings.ts
// owns:
//   - lib/readings.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

import type { LucideIcon } from "lucide-react"

export type AvailableReading = {
  key: "natal" | "horary"
  title: string
  description: string
  icon: LucideIcon
  /** Короткое описание того, что внутри — для экрана разбора в будущем */
  teaser?: string
}

export type ComingReading = {
  key: "month" | "year" | "synastry" | "themes" | "history"
  title: string
  description: string
  icon: LucideIcon
}

export type ReadingsCatalog = {
  available: AvailableReading[]
  coming: ComingReading[]
}
