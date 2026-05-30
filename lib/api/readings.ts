// AI_HEADER
// module: M-API-READINGS-CLIENT
// wave: W-2.5
// purpose: Production API client for readings (replaces fixtures)

import type { ReadingsList, ReadingEntry } from '@/lib/contracts/readings';
import type { components } from '@/packages/contracts/_generated';

type TodayPayload = components['schemas']['TodayPayload'];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

/**
 * Get list of past readings by fetching recent days
 * @param limit - Number of entries to fetch
 * @param offset - Offset for pagination
 * @returns List of reading entries with hasMore flag
 */
export async function getReadingsList(limit: number = 10, offset: number = 0): Promise<ReadingsList> {
  const entries: ReadingEntry[] = [];

  // Calculate date range: fetch last N days
  const today = new Date();
  const startDate = new Date(today);
  startDate.setDate(today.getDate() - offset - limit);

  // Fetch days in parallel
  const promises: Promise<TodayPayload | null>[] = [];
  for (let i = 0; i < limit; i++) {
    const date = new Date(today);
    date.setDate(today.getDate() - offset - i - 1); // -1 to exclude today
    const dateStr = date.toISOString().split('T')[0];
    promises.push(fetchDayForReadings(dateStr));
  }

  const results = await Promise.all(promises);

  // Convert TodayPayload to ReadingEntry
  for (const payload of results) {
    if (payload && payload.access.state !== 'locked') {
      entries.push({
        date: payload.date,
        headline: payload.headline,
        dayStatus: mapDayStatus(payload.topFlags),
        preview: payload.reading.paragraphs[0] || '',
      });
    }
  }

  // Check if there are more entries
  const hasMore = entries.length === limit;

  return { entries, hasMore };
}

/**
 * Fetch a single day for readings list
 * Returns null if day is not accessible
 */
async function fetchDayForReadings(date: string): Promise<TodayPayload | null> {
  try {
    const res = await fetch(`${API_BASE}/api/day/${date}`, {
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!res.ok) {
      return null;
    }

    return res.json();
  } catch {
    return null;
  }
}

/**
 * Map topFlags to dayStatus for readings list
 */
function mapDayStatus(topFlags: Array<{ label: string; sentiment: string }>): string {
  if (topFlags.length === 0) {
    return 'steady';
  }

  // Count sentiments
  const sentiments = topFlags.map(f => f.sentiment);
  const positiveCount = sentiments.filter(s => s === 'positive').length;
  const negativeCount = sentiments.filter(s => s === 'negative').length;

  if (positiveCount > negativeCount) {
    return 'supportive';
  } else if (negativeCount > positiveCount) {
    return 'tense';
  }

  return 'steady';
}
