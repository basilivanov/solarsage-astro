
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_READINGS
// ROLE: Lib — readings.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: Library: readings
// owns:
//   - lib/contracts/readings.ts
// inputs: Function arguments
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
