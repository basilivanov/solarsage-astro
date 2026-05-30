// AI_HEADER
// module: M-WEB-READING-CARD
// wave: W-2.5
// purpose: Reading card component

import React from 'react';
import { ReadingEntry } from '@/lib/contracts/readings';

interface ReadingCardProps {
  entry: ReadingEntry;
  onClick: () => void;
}

export function ReadingCard({ entry, onClick }: ReadingCardProps) {
  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg p-4 shadow-sm cursor-pointer hover:shadow-md transition"
      data-testid="reading-card"
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
