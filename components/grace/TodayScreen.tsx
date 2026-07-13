
// ############################################################################
// AI_HEADER: GRACE_LEGACY_TODAY_SCREEN — legacy TodayPayload composition surface.
// ROLE: Legacy TodayPayload surface for components/grace, distinct from the active components/today/today-screen.tsx V2 surface.
// ############################################################################

// START_MODULE_CONTRACT: M-GRACE-COMPONENT-TODAY-SCREEN
// purpose: Compose locked or unlocked legacy day content from canonical TodayPayload.
// owns:
//   - components/grace/TodayScreen.tsx
// inputs: payload — TodayPayload containing access, date, headline, week, flags, reading and why-this-happens sections.
// outputs: today-screen root; locked branch or full legacy day presentation.
// dependencies: WeekStrip; TopFlags; Reading; DayNavigation; LockedDay; packages/contracts TodayPayload.
// side_effects: none directly; child navigation components may navigate on interaction.
// emitted_logs: none.
// invariants:
//   - data-testid="today-screen" exists in both access branches.
//   - Locked access renders navigation plus LockedDay and suppresses full content.
//   - data-testid="today-headline" and child ordering remain stable when unlocked.
//   - Paragraph and bullet why blocks retain order; unknown kinds render nothing.
// failure_policy: Does not catch malformed payload or child render errors; they propagate.
// END_MODULE_CONTRACT: M-GRACE-COMPONENT-TODAY-SCREEN

// START_MODULE_MAP: M-GRACE-COMPONENT-TODAY-SCREEN
// public_entrypoints:
//   - TodayScreen
// semantic_blocks:
//   - LOCKED_BRANCH: navigation and access lock view.
//   - DAY_HEADER: date navigation and headline/subtitle.
//   - DAY_SUMMARY: week, flags and reading composition.
//   - WHY_SECTIONS: ordered paragraph and bullet explanation cards.
// owned_tests:
//   - none direct; active V2 TodayScreen tests target components/today instead.
// END_MODULE_MAP: M-GRACE-COMPONENT-TODAY-SCREEN

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
