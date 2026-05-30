// AI_HEADER
// module: M-WEB-CALENDAR-MONTH
// wave: W-2.3, W-ACCESS.3
// purpose: Single month in calendar grid with locked badges

import type { components } from '@/packages/contracts/_generated';
import Link from 'next/link';

type CalendarMonth = components['schemas']['CalendarMonth'];

interface CalendarMonthProps {
  month: CalendarMonth;
}

export function CalendarMonth({ month }: CalendarMonthProps) {
  // Parse month name
  const [year, monthNum] = month.month.split('-').map(Number);
  const monthName = new Date(year, monthNum - 1).toLocaleDateString('ru-RU', {
    month: 'long',
    year: 'numeric',
  });

  return (
    <div className="calendar-month">
      <h2 className="calendar-month-title">{monthName}</h2>

      <div className="calendar-weekdays">
        {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map((day) => (
          <div key={day} className="calendar-weekday">
            {day}
          </div>
        ))}
      </div>

      <div className="calendar-days">
        {month.days.map((day) => {
          const statusClass = `calendar-day-${day.dayStatus}`;
          const disabledClass = day.disabled ? 'disabled' : '';
          const todayClass = day.isToday ? 'today' : '';
          const currentMonthClass = day.isCurrentMonth ? '' : 'other-month';
          // W-ACCESS.3: Add locked class
          const lockedClass = day.access?.state === 'locked' ? 'locked' : '';

          return (
            <Link
              key={day.date}
              href={`/day/${day.date}`}
              className={`calendar-day ${statusClass} ${disabledClass} ${todayClass} ${currentMonthClass} ${lockedClass}`}
              data-date={day.date}
              data-status={day.dayStatus}
              data-testid={`calendar-day-${day.date}`}
            >
              <span className="calendar-day-number">{day.dayNumber}</span>
              {/* W-ACCESS.3: Show lock badge for locked days */}
              {day.access?.state === 'locked' && (
                <span className="calendar-day-lock" data-testid="calendar-day-lock">
                  🔒
                </span>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
