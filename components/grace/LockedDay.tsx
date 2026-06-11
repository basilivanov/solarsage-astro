
// ############################################################################
// AI_HEADER: MODULE_GRACE_LOCKEDDAY
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/grace/LockedDay.tsx
// owns:
//   - components/grace/LockedDay.tsx
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
// module: M-WEB-LOCKED-DAY
// wave: W-2.7, W-ACCESS.3
// purpose: Locked day with soft lock + CTAs

'use client';

import { useRouter } from 'next/navigation';

export function LockedDay() {
  const router = useRouter();

  return (
    <div
      className="flex flex-col items-center justify-center px-10 py-12 text-center"
      data-testid="locked-day"
    >
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-full border border-border/70 bg-card text-muted-foreground">
        <span className="text-2xl">🔒</span>
      </div>

      <h2 className="font-serif text-[26px] leading-tight tracking-tight text-foreground">
        Этот день заблокирован
      </h2>

      <p className="mt-2 max-w-[22ch] text-[13px] leading-relaxed text-muted-foreground">
        Подпишитесь или пригласите друга, чтобы получить доступ к полному прогнозу
      </p>

      <div className="mt-6 flex flex-col gap-3 w-full max-w-xs">
        <button
          onClick={() => router.push('/paywall')}
          data-testid="cta-subscribe"
          className="rounded-full border border-foreground/85 bg-foreground text-background px-6 py-2.5 text-[13px] font-medium transition active:scale-[0.98]"
        >
          Оформить подписку
        </button>

        <button
          onClick={() => router.push('/referral')}
          data-testid="cta-invite"
          className="rounded-full border border-border/70 bg-card text-foreground px-6 py-2.5 text-[13px] font-medium transition active:scale-[0.98]"
        >
          Пригласить друга (+14 дней)
        </button>
      </div>

      <p className="mt-4 text-[11px] leading-relaxed text-muted-foreground/70">
        Приглашение даёт 14 дней доступа вам и вашему другу
      </p>
    </div>
  );
}
