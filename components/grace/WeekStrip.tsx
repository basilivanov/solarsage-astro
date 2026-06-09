// AI_HEADER
// module: M-WEB-WEEK-STRIP
// wave: W-2.2
// purpose: 7-day week strip navigation

import Link from 'next/link';
import { cn } from '@/lib/utils';
import type { WeekStripDay } from '@/packages/contracts';

interface WeekStripProps {
  days: WeekStripDay[];
  currentDate: string;
}

const WEEKDAYS_MINI = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

export function WeekStrip({ days, currentDate }: WeekStripProps) {
  return (
    <section className="px-5" aria-label="Неделя" data-testid="week-strip">
      <h3 className="mb-3 font-serif text-[20px] leading-none tracking-tight">
        Неделя
      </h3>
      <ul className="grid grid-cols-7 gap-[6px]" role="list">
        {days.map((day) => {
          const isActive = day.date === currentDate;
          const date = new Date(day.date);
          const dayOfWeek = (date.getDay() + 6) % 7;

          return (
            <li key={day.date}>
              <Link
                href={`/day/${day.date}`}
                aria-label={`${WEEKDAYS_MINI[dayOfWeek]} ${date.getDate()}`}
                data-date={day.date}
                data-status={day.dayStatus}
                className={cn(
                  "relative flex w-full flex-col items-center gap-1.5 rounded-[12px] border px-0 py-2.5 text-center transition active:scale-[0.96]",
                  isActive
                    ? "border-primary/50 bg-primary text-primary-foreground shadow-[0_1px_0_0_rgba(0,0,0,0.04)]"
                    : "border-border/70 bg-card text-foreground",
                )}
              >
                <span
                  className={cn(
                    "text-[9px] font-medium uppercase tracking-[0.08em]",
                    isActive
                      ? "text-primary-foreground/80"
                      : "text-muted-foreground",
                  )}
                >
                  {WEEKDAYS_MINI[dayOfWeek]}
                </span>
                <span className="font-serif text-[19px] leading-none">
                  {date.getDate()}
                </span>
                <span
                  className={cn(
                    "flex h-4 items-center justify-center text-[10px]",
                    isActive
                      ? "text-primary-foreground/70"
                      : "text-muted-foreground",
                  )}
                >
                  {day.dayStatus === 'supportive'
                    ? '+'
                    : day.dayStatus === 'tense'
                      ? '−'
                      : '·'}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
