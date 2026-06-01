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
    <div className="w-full space-y-8 py-4" data-testid="calendar-grid">
      <CalendarMonth month={payload} />
    </div>
  );
}
