// AI_HEADER
// module: M-WEB-TODAY-SCREEN
// wave: W-2.2, W-2.3, W-2.7
// purpose: Today screen main component — Tailwind styled matching reference design

import { WeekStrip } from './WeekStrip';
import { TopFlags } from './TopFlags';
import { Reading } from './Reading';
import { DayNavigation } from './DayNavigation';
import { LockedDay } from './LockedDay';
import type { TodayPayload } from '@/packages/contracts';

interface TodayScreenProps {
  payload: TodayPayload;
}

export function TodayScreen({ payload }: TodayScreenProps) {
  if (payload.access.state === 'locked') {
    return (
      <div data-testid="today-screen">
        <DayNavigation currentDate={payload.date} />
        <LockedDay />
      </div>
    );
  }

  return (
    <div className="touch-pan-y" data-testid="today-screen">
      <div
        className="flex-none"
        style={{ paddingTop: 'max(env(safe-area-inset-top), 0.5rem)' }}
      >
        <DayNavigation currentDate={payload.date} />
      </div>

      <div className="space-y-8 pb-8">
        {/* Headline */}
        <header className="px-5 pt-4">
          <h1
            className="font-serif text-[34px] leading-[1.05] tracking-[-0.01em] text-foreground text-balance"
            data-testid="today-headline"
          >
            {payload.headline}
          </h1>
          {payload.subtitle && (
            <p className="mt-3 font-sans text-[15px] leading-relaxed text-foreground/60 text-pretty">
              {payload.subtitle}
            </p>
          )}
        </header>

        {/* Week Strip */}
        <WeekStrip days={payload.weekStrip} currentDate={payload.date} />

        {/* Top Flags */}
        <TopFlags flags={payload.topFlags} />

        {/* Reading */}
        <Reading paragraphs={payload.reading.paragraphs} />

        {/* Why This Happens */}
        {payload.whyThisHappens.sections.length > 0 && (
          <section className="px-5">
            <h2 className="mb-4 font-sans text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Почему так у меня
            </h2>
            <div className="space-y-5">
              {payload.whyThisHappens.sections.map((section, idx) => (
                <div
                  key={idx}
                  className="rounded-2xl border border-border/60 bg-card/60 p-5"
                >
                  <h3 className="font-serif text-[20px] leading-tight text-foreground">
                    {section.title}
                  </h3>
                  <div className="mt-3 space-y-3">
                    {section.blocks.map((block, bidx) => {
                      if (block.kind === 'paragraph') {
                        return (
                          <p
                            key={bidx}
                            className="font-sans text-[15px] leading-relaxed text-foreground/70 text-pretty"
                          >
                            {block.text}
                          </p>
                        );
                      }
                      if (block.kind === 'bullets') {
                        return (
                          <ul key={bidx} className="space-y-1.5 pl-4">
                            {block.items.map((item, iidx) => (
                              <li
                                key={iidx}
                                className="flex items-start gap-2 font-sans text-[14px] leading-relaxed text-foreground/65"
                              >
                                <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent" />
                                {item}
                              </li>
                            ))}
                          </ul>
                        );
                      }
                      return null;
                    })}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
