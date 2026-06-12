
// ############################################################################
// AI_HEADER: MODULE_LIB_READINGS
// ROLE: Lib — readings.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Library: readings
// owns:
//   - lib/readings.ts
// inputs: Function arguments
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
