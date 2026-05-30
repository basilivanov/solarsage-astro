// AI_HEADER
// module: M-WEB-CALENDAR-GRID
// wave: W-2.3
// purpose: 3-month calendar grid display

import type { components } from '@/packages/contracts/_generated';
import { CalendarMonth } from './CalendarMonth';

type CalendarPayload = components['schemas']['CalendarPayload'];

interface CalendarGridProps {
  payload: CalendarPayload;
}

export function CalendarGrid({ payload }: CalendarGridProps) {
  return (
    <div className="calendar-grid" data-testid="calendar-grid">
      {payload.months.map((month) => (
        <CalendarMonth key={month.month} month={month} />
      ))}
    </div>
  );
}
