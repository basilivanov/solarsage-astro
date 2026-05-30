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

  // Previous day
  const prevDate = new Date(date);
  prevDate.setDate(prevDate.getDate() - 1);
  const prevDateStr = prevDate.toISOString().split('T')[0];

  // Next day
  const nextDate = new Date(date);
  nextDate.setDate(nextDate.getDate() + 1);
  const nextDateStr = nextDate.toISOString().split('T')[0];

  return (
    <nav className="day-navigation">
      <Link
        href={`/day/${prevDateStr}`}
        className="day-nav-button"
        data-testid="day-nav-prev"
      >
        ← Вчера
      </Link>

      <Link
        href="/calendar"
        className="day-nav-calendar"
        data-testid="day-nav-calendar"
      >
        Календарь
      </Link>

      <Link
        href={`/day/${nextDateStr}`}
        className="day-nav-button"
        data-testid="day-nav-next"
      >
        Завтра →
      </Link>
    </nav>
  );
}
