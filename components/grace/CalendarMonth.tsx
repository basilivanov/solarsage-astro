
// ############################################################################
// AI_HEADER: GRACE_CALENDAR_MONTH — linked legacy calendar month grid.
// ROLE: Presentational month grid that converts CalendarPayload days into dated Next.js links with status and lock semantics.
// ############################################################################

// START_MODULE_CONTRACT: M-GRACE-COMPONENT-CALENDAR-MONTH
// purpose: Render month title, weekday headings and day navigation cells.
// owns:
//   - components/grace/CalendarMonth.tsx
// inputs: month — CalendarPayload containing month id and day entries.
// outputs: localized Russian month heading and role=grid list of /day/:date links.
// dependencies: next/link; lib/utils cn; packages/contracts CalendarPayload.
// side_effects: none directly; link activation delegates navigation to Next.js.
// emitted_logs: none.
// invariants:
//   - data-testid="calendar-day-${date}", data-date and data-status remain stable.
//   - Locked days retain the lock marker and remain linked to their day route.
//   - Current-month, today and access styling decisions remain unchanged.
// failure_policy: Assumes valid YYYY-MM month data; render errors propagate.
// END_MODULE_CONTRACT: M-GRACE-COMPONENT-CALENDAR-MONTH

// START_MODULE_MAP: M-GRACE-COMPONENT-CALENDAR-MONTH
// public_entrypoints:
//   - CalendarMonth
// semantic_blocks:
//   - MONTH_HEADING: localized month/year label.
//   - WEEKDAY_HEADER: Russian weekday abbreviations.
//   - DAY_GRID: linked day cells with current, locked and status state.
// owned_tests:
//   - none direct.
// END_MODULE_MAP: M-GRACE-COMPONENT-CALENDAR-MONTH

import Link from 'next/link';
import { cn } from '@/lib/utils';
import type { CalendarPayload } from '@/packages/contracts';

interface CalendarMonthProps {
  month: CalendarPayload;
}

const WEEKDAYS_SHORT = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

export function CalendarMonth({ month }: CalendarMonthProps) {
  const [year, monthNum] = month.month.split('-').map(Number);
  const monthName = new Date(year, monthNum - 1).toLocaleDateString('ru-RU', {
    month: 'long',
    year: 'numeric',
  });

  return (
    <div className="w-full">
      <h2 className="font-serif text-[22px] leading-none tracking-tight text-foreground mb-4 px-5">
        {monthName}
      </h2>

      <div className="grid grid-cols-7 px-5 mb-2">
        {WEEKDAYS_SHORT.map((day, i) => (
          <div
            key={day}
            className={cn(
              "text-center text-[10px] uppercase tracking-[0.14em]",
              i >= 5 ? "text-muted-foreground/60" : "text-muted-foreground/80",
            )}
          >
            {day}
          </div>
        ))}
      </div>

      <ol role="grid" className="grid grid-cols-7 gap-y-1 px-3 pb-2">
        {month.days.map((day) => {
          const isToday = day.isToday;
          const isCurrentMonth = day.isCurrentMonth;
          const isAccessible = day.access?.state !== 'locked';

          return (
            <li key={day.date} className="flex items-center justify-center py-1">
              <Link
                href={`/day/${day.date}`}
                data-date={day.date}
                data-status={day.dayStatus}
                data-testid={`calendar-day-${day.date}`}
                className={cn(
                  "relative flex h-11 w-11 flex-col items-center justify-center rounded-full text-[15px] transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60",
                  !isCurrentMonth && "text-muted-foreground/35",
                  isCurrentMonth && !isToday && "text-foreground/85 hover:bg-muted/60",
                  isToday && "text-foreground ring-1 ring-border",
                  isCurrentMonth && !isAccessible && "opacity-65",
                )}
              >
                <span className="font-serif leading-none">{day.dayNumber}</span>

                {isCurrentMonth && !isAccessible && (
                  <span
                    className="absolute right-1.5 top-1.5 text-[9px] text-muted-foreground/50"
                    data-testid="calendar-day-lock"
                  >
                    🔒
                  </span>
                )}
              </Link>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
