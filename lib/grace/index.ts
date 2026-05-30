// AI_HEADER
// module: M-WEB-GRACE-INDEX
// wave: W-2.1
// purpose: Barrel export for GRACE frontend modules

export { fetchDay, fetchCalendar, ApiError } from './api/client';
export { useDay } from './hooks/useDay';
export { useCalendar } from './hooks/useCalendar';
export type { UseDayResult } from './hooks/useDay';
export type { UseCalendarResult } from './hooks/useCalendar';
