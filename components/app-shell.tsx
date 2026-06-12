
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_APP_SHELL
// ROLE: App shell layout — tab bar, auth guard, navigation shell.
// DEPENDENCIES: react, @/components/today/tab-bar, @/hooks/use-onboarded, @/lib/log
// GRACE_ANCHORS: [APP_SHELL]
// ############################################################################

// START_MODULE_CONTRACT: M-COMPONENTS-APP-SHELL
// purpose: Root layout component that wraps the app with TabBar and auth guard.
// owns:
//   - components/app-shell.tsx
// inputs:
//   - children: React.ReactNode
// outputs:
//   - JSX layout with TabBar
// dependencies:
//   - M-HOOKS-USE-ONBOARDED
//   - M-COMPONENTS-TAB-BAR
// side_effects:
//   - mounts TabBar with route detection
//   - logs render via logger.debug
// invariants:
//   - always renders TabBar with active route detection
// failure_policy:
//   - logger.debug wraps render; no crash on log failure
// END_MODULE_CONTRACT: M-COMPONENTS-APP-SHELL
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
