
// ############################################################################
// AI_HEADER: GRACE_CALENDAR_GRID — calendar payload wrapper for the legacy month view.
// ROLE: Presentational wrapper that receives one CalendarPayload and delegates month rendering to CalendarMonth.
// ############################################################################

// START_MODULE_CONTRACT: M-GRACE-COMPONENT-CALENDAR-GRID
// purpose: Render the calendar-grid structural container for one calendar payload.
// owns:
//   - components/grace/CalendarGrid.tsx
// inputs: payload — canonical CalendarPayload for the displayed month.
// outputs: calendar-grid div containing one CalendarMonth.
// dependencies: CalendarMonth; packages/contracts CalendarPayload.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - data-testid="calendar-grid" remains stable.
//   - The payload is passed to CalendarMonth unchanged.
// failure_policy: Does not catch child/render errors; they propagate to caller.
// END_MODULE_CONTRACT: M-GRACE-COMPONENT-CALENDAR-GRID

// START_MODULE_MAP: M-GRACE-COMPONENT-CALENDAR-GRID
// public_entrypoints:
//   - CalendarGrid
// semantic_blocks:
//   - GRID_WRAPPER: stable container and CalendarMonth delegation.
// owned_tests:
//   - none direct.
// END_MODULE_MAP: M-GRACE-COMPONENT-CALENDAR-GRID

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
