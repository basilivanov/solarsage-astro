// AI_HEADER
// module: M-WEB-TODAY-SCREEN
// wave: W-2.2, W-2.3, W-2.7
// purpose: Today screen main component

import type { TodayPayload } from '@/packages/contracts/_generated';
import { WeekStrip } from './WeekStrip';
import { TopFlags } from './TopFlags';
import { Reading } from './Reading';
import { DayNavigation } from './DayNavigation';
import { LockedDay } from './LockedDay';

interface TodayScreenProps {
  payload: TodayPayload;
}

export function TodayScreen({ payload }: TodayScreenProps) {
  // W-2.7: Check if day is locked
  if (payload.access.state === 'locked') {
    return (
      <div className="today-screen" data-testid="today-screen">
        <DayNavigation currentDate={payload.date} />
        <LockedDay />
      </div>
    );
  }

  return (
    <div className="today-screen" data-testid="today-screen">
      {/* Day Navigation */}
      <DayNavigation currentDate={payload.date} />

      {/* Header */}
      <header className="today-header">
        <h1 className="today-title" data-testid="today-headline">
          {payload.headline}
        </h1>
        {payload.subtitle && (
          <p className="today-subtitle">{payload.subtitle}</p>
        )}
      </header>

      {/* Week Strip */}
      <WeekStrip days={payload.weekStrip} currentDate={payload.date} />

      {/* Top Flags */}
      <TopFlags flags={payload.topFlags} />

      {/* Reading */}
      <Reading paragraphs={payload.reading.paragraphs} />

      {/* Why This Happens (if present) */}
      {payload.whyThisHappens.sections.length > 0 && (
        <section className="why-section">
          <h2>Почему так у меня</h2>
          {payload.whyThisHappens.sections.map((section, idx) => (
            <div key={idx} className="why-section-item">
              <h3>{section.title}</h3>
              {section.paragraphs.map((p, pidx) => (
                <p key={pidx}>{p}</p>
              ))}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
