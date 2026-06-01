// AI_HEADER
// module: M-API-READINGS-CLIENT
// wave: W-2.5
// purpose: Production API client for readings

import type { ReadingsList, ReadingEntry } from '@/lib/contracts/readings';
import type { ReadingsCatalog } from '@/lib/readings';
import type { components } from '@/packages/contracts/_generated';

import { Sparkles, Star, CalendarDays, Calendar, Users } from 'lucide-react';

type TodayPayload = components['schemas']['TodayPayload'];

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
        key: "natal",
        title: "Натальная карта",
        description: "Персональный разбор вашей натальной карты",
        icon: Star,
        teaser: "Планеты, дома, аспекты — глубокий разбор вашей карты рождения",
      },
      {
        key: "horary",
        title: "Хорар",
        description: "Спросите о конкретной ситуации",
        icon: Sparkles,
        teaser: "Скоро: задайте точный вопрос и получите ответ",
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
