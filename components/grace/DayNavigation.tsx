
// ############################################################################
// AI_HEADER: MODULE_GRACE_DAYNAVIGATION
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: Tests for DayNavigation.tsx behavior
// owns:
//   - components/grace/DayNavigation.tsx
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-WEB-DAY-NAVIGATION
// wave: W-2.3
// purpose: Day navigation arrows (prev/next)

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
