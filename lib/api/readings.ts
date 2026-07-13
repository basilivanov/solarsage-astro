
// ############################################################################
// AI_HEADER: FRONTEND_API_READINGS — past-day reading aggregation and static product catalog.
// ROLE: Past-day reading aggregator and static readings catalog provider.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-READINGS
// purpose: Build unlocked reading previews from recent day payloads and expose available or coming reading products.
// owns:
//   - lib/api/readings.ts
// inputs: limit and offset for history; authenticated session.
// outputs: ReadingsList, ReadingsCatalog and async catalog alias.
// dependencies: readings contracts and catalog types; TodayPayload; lucide icons; Date; Promise.all; fetch.
// side_effects: parallel credentialed GET /api/day/:date calls for history.
// emitted_logs: none.
// invariants:
//   - Requested dates remain prior days derived from offset and limit.
//   - Failed or non-ok day fetches and locked payloads are omitted.
//   - Preview remains the first reading paragraph or an empty string.
//   - hasMore remains entries.length equal to limit.
//   - Stable catalog keys, copy, icons and order remain unchanged.
// failure_policy: Per-day transport or non-ok failures return null and are omitted; catalog functions do not throw.
// END_MODULE_CONTRACT: M-FRONTEND-API-READINGS

// START_MODULE_MAP: M-FRONTEND-API-READINGS
// public_entrypoints:
//   - getReadingsList
//   - listReadings
//   - listReadingsAsync
// semantic_blocks:
//   - HISTORY_DATE_PLAN: derive prior dates from offset and limit.
//   - DAY_FETCH_FAIL_SOFT: fetch a day and map request failures to null.
//   - HISTORY_ASSEMBLY: omit locked or missing days and build previews.
//   - PRODUCT_CATALOG: expose the stable available and coming products.
//   - ASYNC_CATALOG_ALIAS: resolve the synchronous catalog asynchronously.
// owned_tests:
//   - __tests__/api/readings.test.ts
//   - __tests__/components/ReadingsScreen.test.tsx
// END_MODULE_MAP: M-FRONTEND-API-READINGS

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
        key: "synastry",
        title: "Синастрия",
        description: "Совместимость с партнёром",
        icon: Users,
      },
    ],
  }
}

export async function listReadingsAsync(): Promise<ReadingsCatalog> {
  return listReadings()
}
