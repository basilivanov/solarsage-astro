
// ############################################################################
// AI_HEADER: GRACE_DAY_NAVIGATION — previous, calendar and next day links.
// ROLE: Date header that derives previous/next dates and exposes day/calendar links.
// ############################################################################

// START_MODULE_CONTRACT: M-GRACE-COMPONENT-DAY-NAVIGATION
// purpose: Render navigation around a current ISO date.
// owns:
//   - components/grace/DayNavigation.tsx
// inputs: currentDate — ISO-like date string consumed by Date.
// outputs: header with previous-day, calendar and next-day links plus localized label.
// dependencies: next/link; JavaScript Date/Intl locale formatting.
// side_effects: none directly; link activation delegates navigation to Next.js.
// emitted_logs: none.
// invariants:
//   - day-nav-prev/day-nav-calendar/day-nav-next test IDs and aria-labels remain stable.
//   - Previous and next routes remain one calendar day from currentDate.
// failure_policy: Does not validate malformed dates; resulting render behavior propagates.
// END_MODULE_CONTRACT: M-GRACE-COMPONENT-DAY-NAVIGATION

// START_MODULE_MAP: M-GRACE-COMPONENT-DAY-NAVIGATION
// public_entrypoints:
//   - DayNavigation
// semantic_blocks:
//   - DATE_DERIVATION: previous/next ISO date and localized label.
//   - NAVIGATION_HEADER: stable accessible links.
// owned_tests:
//   - none direct.
// END_MODULE_MAP: M-GRACE-COMPONENT-DAY-NAVIGATION

import Link from 'next/link';

interface DayNavigationProps {
  currentDate: string;
}

export function DayNavigation({ currentDate }: DayNavigationProps) {
  const date = new Date(currentDate);

  const prevDate = new Date(date);
  prevDate.setDate(prevDate.getDate() - 1);
  const prevDateStr = prevDate.toISOString().split('T')[0];

  const nextDate = new Date(date);
  nextDate.setDate(nextDate.getDate() + 1);
  const nextDateStr = nextDate.toISOString().split('T')[0];

  const monthName = date.toLocaleDateString('ru-RU', {
    month: 'long',
    day: 'numeric',
  });

  return (
    <header className="flex items-center justify-between px-5 pt-3 pb-4">
      <Link
        href={`/day/${prevDateStr}`}
        data-testid="day-nav-prev"
        className="flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-card text-foreground/70 transition active:scale-95"
        aria-label="Предыдущий день"
      >
        ←
      </Link>

      <div className="flex flex-col items-center gap-0.5">
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          День
        </span>
        <span className="font-serif text-[22px] leading-none text-foreground">
          {monthName}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <Link
          href="/calendar"
          data-testid="day-nav-calendar"
          className="flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-card text-foreground/70 transition active:scale-95"
          aria-label="Календарь"
        >
          <span className="text-xs font-medium">Ка</span>
        </Link>
        <Link
          href={`/day/${nextDateStr}`}
          data-testid="day-nav-next"
          className="flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-card text-foreground/70 transition active:scale-95"
          aria-label="Следующий день"
        >
          →
        </Link>
      </div>
    </header>
  );
}
