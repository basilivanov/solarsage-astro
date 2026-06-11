
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_APP_SHELL
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-SHELL-NAVIGATION
// #########################################// START_MODULE_CONTRACT
// purpose: Module: app-shell.tsx
// owns:
//   - components/app-shell.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: Logging via v2 logging spine
// emitted_logs: v2 logging: logEvent/logStart/logSuccess/logFailure (frontend) or logger.* (backend)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { TabBar } from "@/components/today/tab-bar"
import { useOnboarded } from "@/hooks/use-onboarded"
import { logger } from "@/lib/log"

export function AppShell({ children }: { children: React.ReactNode }) {
  const { onboarded } = useOnboarded()

  logger.debug('[AppShell] Render', { extra: { onboarded } })

  return (
    <main className="h-[var(--app-height)] overflow-hidden bg-background">
      <div className="mx-auto flex h-full max-w-md flex-col border-x border-border/50 bg-background">
        <div className="flex-1 overflow-y-auto overscroll-contain">
          {children}
        </div>
        <TabBar />
      </div>
    </main>
  )
}
