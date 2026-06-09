// AI_HEADER
// module: M-WEB-CALENDAR-GRID
// wave: W-2.3
// purpose: 3-month calendar grid display

import { CalendarMonth } from './CalendarMonth';
import type { CalendarPayload } from '@/packages/contracts';

interface CalendarGridProps {
  payload: CalendarPayload;
}

export function CalendarGrid({ payload }: CalendarGridProps) {
  return (
    <div className="w-full space-y-8 py-4" data-testid="calendar-grid">
      <CalendarMonth month={payload} />
    </div>
  );
}
