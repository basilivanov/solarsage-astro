
// ############################################################################
// AI_HEADER: GRACE_LOCKED_DAY — locked-access explanation and recovery actions.
// ROLE: Client locked-access view with subscription and referral navigation actions.
// ############################################################################

// START_MODULE_CONTRACT: M-GRACE-COMPONENT-LOCKED-DAY
// purpose: Explain a locked day and expose two access recovery CTAs.
// owns:
//   - components/grace/LockedDay.tsx
// inputs: none.
// outputs: locked-day view with subscribe and invite buttons.
// dependencies: next/navigation useRouter.
// side_effects: router.push('/paywall') or router.push('/referral') on CTA click.
// emitted_logs: none.
// invariants:
//   - locked-day, cta-subscribe and cta-invite test IDs remain stable.
//   - Subscribe and invite routes remain /paywall and /referral.
//   - Referral copy continues to promise the existing 14-day behavior.
// failure_policy: Navigation failures are not caught locally.
// END_MODULE_CONTRACT: M-GRACE-COMPONENT-LOCKED-DAY

// START_MODULE_MAP: M-GRACE-COMPONENT-LOCKED-DAY
// public_entrypoints:
//   - LockedDay
// semantic_blocks:
//   - LOCK_EXPLANATION: locked state icon and user-facing copy.
//   - ACCESS_ACTIONS: subscription and referral buttons.
//   - REFERRAL_NOTE: existing 14-day explanatory copy.
// owned_tests:
//   - none direct.
// END_MODULE_MAP: M-GRACE-COMPONENT-LOCKED-DAY

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
