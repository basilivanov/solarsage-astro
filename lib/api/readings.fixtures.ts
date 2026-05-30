// AI_HEADER
// module: M-API-READINGS-FIXTURES
// wave: W-2.5
// purpose: Readings fixtures

import { ReadingsList, ReadingEntry } from '@/lib/contracts/readings';

const FIXTURE_ENTRIES: ReadingEntry[] = [
  {
    date: '2026-05-29',
    headline: 'День возможностей',
    dayStatus: 'supportive',
    preview: 'Сегодня благоприятный день для начинаний. Марс поддерживает ваши инициативы.',
  },
  {
    date: '2026-05-28',
    headline: 'Спокойный день',
    dayStatus: 'steady',
    preview: 'Ровный день без особых событий. Хорошее время для рутинных задач.',
  },
  {
    date: '2026-05-27',
    headline: 'День вызовов',
    dayStatus: 'tense',
    preview: 'Сегодня могут возникнуть сложности. Будьте внимательны к деталям.',
  },
];

export async function getReadingsList(limit: number = 10, offset: number = 0): Promise<ReadingsList> {
  // Fixture: simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));

  const entries = FIXTURE_ENTRIES.slice(offset, offset + limit);
  const hasMore = offset + limit < FIXTURE_ENTRIES.length;

  return { entries, hasMore };
}
