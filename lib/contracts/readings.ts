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
