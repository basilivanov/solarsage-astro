// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_BIRTH_TIME_BANNER — honest time-precision prompt.
// ROLE: Shows one dismissible profile prompt for bucket and unknown birth time modes.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-BIRTH-TIME-BANNER
// purpose: Render the birth-time precision banner without exposing exact capabilities.
// owns:
//   - components/today-convergence/birth-time-banner.tsx
// inputs: generated BirthTime mode and parent-owned dismissed flag/callback.
// outputs: data-testid=birth-time-banner and dismiss action.
// dependencies: packages/contracts/today-convergence.ts.
// side_effects: invokes onDismiss after explicit click.
// emitted_logs: none.
// invariants: exact mode and dismissed state render no banner; no exact time is invented.
// failure_policy: callback absence makes the button a safe no-op.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-BIRTH-TIME-BANNER

// START_MODULE_MAP: M-TODAY-CONVERGENCE-BIRTH-TIME-BANNER
// public_entrypoints:
//   - BirthTimeBanner
// semantic_blocks:
//   - BIRTH_TIME_PROMPT: bucket/unknown notice and dismiss control.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-BIRTH-TIME-BANNER

import type { TodayConvergenceBirthTime } from "@/packages/contracts/today-convergence";

type Props = {
  birthTime: TodayConvergenceBirthTime;
  dismissed?: boolean;
  onDismiss?: () => void;
};

// START_BLOCK: BIRTH_TIME_PROMPT
export function BirthTimeBanner({ birthTime, dismissed = false, onDismiss }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-BIRTH-TIME-BANNER.BirthTimeBanner
  // purpose: Render a one-shot dismissible prompt for non-exact birth-time modes.
  // inputs: birthTime — generated mode; dismissed — parent persistence state; onDismiss — parent callback.
  // returns: prompt aside or null for exact/dismissed states.
  // side_effects: invokes onDismiss on click.
  // emitted_logs: none.
  // error_behavior: no-op when exact or already dismissed.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-BIRTH-TIME-BANNER.BirthTimeBanner
  if (birthTime.mode === "exact" || dismissed) return null;

  const message =
    birthTime.mode === "bucket"
      ? "Время рождения указано диапазоном: точные часы и дома не показываем."
      : "Время рождения не указано: точные часы и дома не показываем.";

  return (
    <aside
      data-testid="birth-time-banner"
      className="flex items-start gap-3 rounded-2xl border border-border/60 bg-card/70 px-4 py-3 text-[13px]"
    >
      <span aria-hidden className="mt-0.5 text-base">ⓘ</span>
      <p className="flex-1 leading-5">{message} Уточнить можно в профиле.</p>
      <button
        type="button"
        onClick={() => onDismiss?.()}
        aria-label="Скрыть подсказку о времени рождения"
        className="min-h-11 min-w-11 rounded-full border border-border/70 px-2 text-xs text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        Скрыть
      </button>
    </aside>
  );
}
// END_BLOCK: BIRTH_TIME_PROMPT
