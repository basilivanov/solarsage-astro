
// ############################################################################
// AI_HEADER: MODULE_GRACE_CALENDARGRID
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: Module: CalendarGrid.tsx
// owns:
//   - components/grace/CalendarGrid.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
