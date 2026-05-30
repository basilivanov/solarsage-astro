// AI_HEADER
// module: M-WEB-CALENDAR-PAGE
// wave: W-2.3
// purpose: Calendar screen - 3-month grid view

'use client';

import { useState } from 'react';
import { useCalendar } from '@/lib/grace/hooks/useCalendar';
import { CalendarGrid } from '@/components/grace/CalendarGrid';
import { LoadingSpinner } from '@/components/grace/LoadingSpinner';
import { ErrorBoundary } from '@/components/grace/ErrorBoundary';

export default function CalendarPage() {
  // Default to current month
  const now = new Date();
  const defaultMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

  const [month, setMonth] = useState(defaultMonth);
  const { data, loading, error } = useCalendar(month);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <ErrorBoundary
        error={error}
        title="Не удалось загрузить календарь"
        message={error.message}
      />
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="calendar-page">
      <header className="calendar-header">
        <h1>Календарь</h1>
        <div className="calendar-nav">
          <button
            onClick={() => {
              const [year, m] = month.split('-').map(Number);
              const prevMonth = m === 1 ? 12 : m - 1;
              const prevYear = m === 1 ? year - 1 : year;
              setMonth(`${prevYear}-${String(prevMonth).padStart(2, '0')}`);
            }}
            data-testid="calendar-prev"
          >
            ←
          </button>
          <span>{month}</span>
          <button
            onClick={() => {
              const [year, m] = month.split('-').map(Number);
              const nextMonth = m === 12 ? 1 : m + 1;
              const nextYear = m === 12 ? year + 1 : year;
              setMonth(`${nextYear}-${String(nextMonth).padStart(2, '0')}`);
            }}
            data-testid="calendar-next"
          >
            →
          </button>
        </div>
      </header>

      <CalendarGrid payload={data} />
    </div>
  );
}
