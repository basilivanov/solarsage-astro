// AI_HEADER
// module: M-WEB-WEEK-STRIP
// wave: W-2.2
// purpose: 7-day week strip navigation

import type { WeekStripDay } from '@/packages/contracts/_generated';
import Link from 'next/link';

interface WeekStripProps {
  days: WeekStripDay[];
  currentDate: string;
}

export function WeekStrip({ days, currentDate }: WeekStripProps) {
  return (
    <nav className="week-strip" data-testid="week-strip">
      {days.map((day) => {
        const isActive = day.date === currentDate;
        const statusClass = `week-day-${day.status}`;

        return (
          <Link
            key={day.date}
            href={`/day/${day.date}`}
            className={`week-day ${statusClass} ${isActive ? 'active' : ''}`}
            data-date={day.date}
            data-status={day.status}
          >
            <span className="week-day-number">
              {new Date(day.date).getDate()}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
