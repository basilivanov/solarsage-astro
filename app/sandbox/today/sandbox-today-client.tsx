// ############################################################################
// AI_HEADER: MODULE_SANDBOX_TODAY_CLIENT — client frame for the Today prototype.
// ROLE: Renders the real TodayScreen with fixture payload inside the app shell frame.
// ############################################################################

// START_MODULE_CONTRACT: M-SANDBOX-TODAY-CLIENT
// purpose: Compose the real TodayScreen and TabBar around a fixture payload for visual iteration.
// owns:
//   - app/sandbox/today/sandbox-today-client.tsx
// inputs: fixture payload (generated Today envelope shape) and its name.
// outputs: app-framed interactive preview; fixture badge.
// dependencies: TodayScreen; TabBar.
// side_effects: none.
// emitted_logs: none.
// invariants: no auth, no API calls from the frame itself; screen behaves as in production.
// failure_policy: fixture shape errors surface as the screen's own error states.
// END_MODULE_CONTRACT: M-SANDBOX-TODAY-CLIENT

// START_MODULE_MAP: M-SANDBOX-TODAY-CLIENT
// public_entrypoints:
//   - SandboxTodayClient
// semantic_blocks:
//   - FRAME: app-shell-like container, wide canvas like /day routes.
// owned_tests:
//   - none (dev tooling)
// END_MODULE_MAP: M-SANDBOX-TODAY-CLIENT

"use client";

import type { TodayConvergencePayload } from "@/packages/contracts/today-convergence";
import { TodayScreen } from "@/components/today-convergence/today-screen";
import { TabBar } from "@/components/today/tab-bar";

type Props = {
  payload: unknown;
  fixtureName: string;
};

// START_BLOCK: FRAME
export function SandboxTodayClient({ payload, fixtureName }: Props) {
  return (
    <main className="h-[var(--app-height)] overflow-hidden bg-background">
      <div className="mx-auto flex h-full max-w-md flex-col border-x border-border/50 bg-background lg:max-w-[1120px]">
        <div className="flex-none border-b border-border/40 bg-secondary/40 px-4 py-1.5 text-center text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
          sandbox · {fixtureName}
        </div>
        <div className="flex-1 overflow-y-auto overscroll-contain">
          <TodayScreen
            payload={payload as TodayConvergencePayload}
            screenState="ready"
            onRetry={() => {}}
            birthTimeDismissed={false}
            onBirthTimeDismiss={() => {}}
          />
        </div>
        <TabBar />
      </div>
    </main>
  );
}
// END_BLOCK: FRAME
