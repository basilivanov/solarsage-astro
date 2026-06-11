
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_READINGS
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/contracts/readings.ts
// owns:
//   - lib/contracts/readings.ts
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

// AI_HEADER
// module: M-CONTRACTS-READINGS
// wave: W-2.5
// purpose: Readings contracts

export interface ReadingEntry {
  date: string;  // ISO date
  headline: string;
  dayStatus: 'supportive' | 'steady' | 'tense';
  preview: string;  // First paragraph
}

export interface ReadingsList {
  entries: ReadingEntry[];
  hasMore: boolean;
}
