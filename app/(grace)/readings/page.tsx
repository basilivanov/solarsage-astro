// AI_HEADER
// module: M-WEB-READINGS-PAGE
// wave: W-2.5
// purpose: Readings list page

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ReadingEntry } from '@/lib/contracts/readings';
import { getReadingsList } from '@/lib/api/readings';

export default function ReadingsPage() {
  const router = useRouter();
  const [entries, setEntries] = useState<ReadingEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await getReadingsList();
        setEntries(data.entries);
      } catch (error) {
        console.error('Failed to load readings:', error);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return <div className="p-4">Загрузка...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b p-4">
        <h1 className="text-2xl font-bold">Прошлые дни</h1>
        <p className="text-sm text-gray-600 mt-1">История ваших прогнозов</p>
      </div>

      {/* Entries list */}
      <div className="p-4 space-y-3">
        {entries.map(entry => (
          <div
            key={entry.date}
            onClick={() => router.push(`/day/${entry.date}`)}
            className="bg-white rounded-lg p-4 shadow-sm cursor-pointer hover:shadow-md transition"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm text-gray-500">{entry.date}</div>
              <div className={`text-xs px-2 py-1 rounded ${getStatusColor(entry.dayStatus)}`}>
                {getStatusLabel(entry.dayStatus)}
              </div>
            </div>

            <h3 className="text-lg font-semibold mb-1">{entry.headline}</h3>
            <p className="text-sm text-gray-600 line-clamp-2">{entry.preview}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'supportive':
      return 'bg-green-100 text-green-800';
    case 'tense':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case 'supportive':
      return 'Благоприятный';
    case 'tense':
      return 'Напряжённый';
    default:
      return 'Спокойный';
  }
}
