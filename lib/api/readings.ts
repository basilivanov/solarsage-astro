
// ############################################################################
// AI_HEADER: MODULE_API_READINGS
// ROLE: Tests — readings.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ####// START_MODULE_CONTRACT
// purpose: Tests for readings.ts behavior
// owns:
//   - lib/api/readings.ts
// inputs: Endpoint params, request body
// outputs: Parsed response / typed data
// dependencies: local modules
// side_effects: Network calls to API
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT// AI_HEADER
// module: M-API-READINGS-CLIENT
// wave: W-2.5
// purpose: Production API client for readings

import type { ReadingsList, ReadingEntry } from '@/lib/contracts/readings';
import type { ReadingsCatalog } from '@/lib/readings';
import type { TodayPayload } from '@/packages/contracts';

import { Sparkles, Star, CalendarDays, Calendar, Users } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

/**
 * Get list of past readings by fetching recent days
 */
export async function getReadingsList(limit: number = 10, offset: number = 0): Promise<ReadingsList> {
  const entries: ReadingEntry[] = [];

  const today = new Date();
  const startDate = new Date(today);
  startDate.setDate(today.getDate() - offset - limit);

  const promises: Promise<TodayPayload | null>[] = [];
  for (let i = 0; i < limit; i++) {
    const date = new Date(today);
    date.setDate(today.getDate() - offset - i - 1);
    const dateStr = date.toISOString().split('T')[0];
    promises.push(fetchDayForReadings(dateStr));
  }

  const results = await Promise.all(promises);

  for (const payload of results) {
    if (payload && payload.access.state !== 'locked') {
      entries.push({
        date: payload.date,
        headline: payload.headline,
        dayStatus: payload.dayStatus,
        preview: payload.reading.paragraphs[0] || '',
      });
    }
  }

  const hasMore = entries.length === limit;
  return { entries, hasMore };
}

async function fetchDayForReadings(date: string): Promise<TodayPayload | null> {
  try {
    const res = await fetch(`${API_BASE}/api/day/${date}`, {
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!res.ok) return null;

    return res.json();
  } catch {
    return null;
  }
}

export function listReadings(): ReadingsCatalog {
  return {
    available: [
      {
        key: "horary",
        title: "Хорар",
        description: "Задай точный вопрос и получи ответ карты",
        icon: Sparkles,
        teaser: "Конкретный вопрос — конкретный ответ по моменту вопроса",
      },
      {
        key: "natal",
        title: "Натальная карта",
        description: "Глубокий разбор карты рождения",
        icon: Star,
        teaser: "Планеты, дома, аспекты — всё о тебе по данным рождения",
      },
    ],
    coming: [
      {
        key: "month",
        title: "Прогноз на месяц",
        description: "Что готовит ближайший месяц",
        icon: CalendarDays,
      },
      {
        key: "year",
        title: "Прогноз на год",
        description: "Главные темы года",
        icon: Calendar,
      },
      {
        key: "themes",
        title: "Темы периода",
        description: "Сквозные темы текущего жизненного этапа",
        icon: Users,
      },
    ],
  }
}

export async function listReadingsAsync(): Promise<ReadingsCatalog> {
  return listReadings()
}
