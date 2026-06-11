
// ############################################################################
// AI_HEADER: MODULE_GRACE_CALENDARMONTH
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/grace/CalendarMonth.tsx
// owns:
//   - components/grace/CalendarMonth.tsx
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

// AI_HEADER
// module: M-WEB-CALENDAR-MONTH
// wave: W-2.3, W-ACCESS.3
// purpose: Single month in calendar grid with locked badges

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
