
// ############################################################################
// AI_HEADER: MODULE_GRACE_TOPFLAGS
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: Module: TopFlags.tsx
// owns:
//   - components/grace/TopFlags.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-WEB-TOP-FLAGS
// wave: W-2.2
// purpose: Top flags display

import type { TopFlag } from '@/packages/contracts';

interface TopFlagsProps {
  flags: TopFlag[];
}

export function TopFlags({ flags }: TopFlagsProps) {
  if (flags.length === 0) return null;

  return (
    <section className="px-5" data-testid="top-flags">
      <div className="overflow-hidden rounded-2xl border border-border/70 bg-card">
        {flags.map((flag, idx) => {
          const isLast = idx === flags.length - 1;
          return (
            <div
              key={idx}
              className={isLast ? "" : "border-b border-border/60"}
            >
              <div className="flex items-start gap-4 px-4 py-4">
                <div className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-accent">
                  <span className="text-[18px] leading-none text-accent-foreground" data-icon={flag.iconName}>
                    {flag.iconName}
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[15px] font-medium leading-snug text-foreground">
                    {flag.title}
                  </div>
                  <div className="mt-0.5 text-[13px] leading-snug text-muted-foreground">
                    {flag.summary}
                  </div>
                  {flag.hint && (
                    <div className="mt-2 rounded-lg border border-border/60 bg-secondary/40 px-3 py-2.5 space-y-2">
                      {flag.hint.howItFeels && (
                        <div>
                          <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                            Ощущения
                          </div>
                          <p className="mt-0.5 font-serif text-[14px] leading-[1.5] text-foreground/85">
                            {flag.hint.howItFeels}
                          </p>
                        </div>
                      )}
                      {flag.hint.whyToday && (
                        <div>
                          <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                            Почему сегодня
                          </div>
                          <p className="mt-0.5 font-serif text-[14px] leading-[1.5] text-foreground/85">
                            {flag.hint.whyToday}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
