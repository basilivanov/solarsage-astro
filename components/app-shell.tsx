// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_APP_SHELL
// ROLE: App shell layout — tab bar, auth guard, navigation shell.
// DEPENDENCIES: react, @/components/today/tab-bar, @/hooks/use-onboarded, @/lib/log
// GRACE_ANCHORS: [APP_SHELL_COMPONENT]
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

// START_MODULE_MAP: M-COMPONENTS-APP-SHELL
// public_entrypoints:
//   - AppShell
// semantic_blocks:
//   - APP_SHELL_COMPONENT: root application layout shell
// owned_tests:
//   - __tests__/components/TabBar.test.tsx
// END_MODULE_MAP: M-COMPONENTS-APP-SHELL

"use client"

import { usePathname } from "next/navigation"

import { TabBar } from "@/components/today/tab-bar"
import { useOnboarded } from "@/hooks/use-onboarded"
import { logger } from "@/lib/log"

// START_BLOCK: APP_SHELL_COMPONENT
export function AppShell({ children }: { children: React.ReactNode }) {
  // START_FUNCTION_CONTRACT: F-M-COMPONENTS-APP-SHELL.AppShell
  // purpose: Render application root layout shell with TabBar navigation.
  // inputs: children (React.ReactNode)
  // returns: JSX.Element
  // side_effects: logs render event via logger.debug
  // error_behavior: none
  // END_FUNCTION_CONTRACT: F-M-COMPONENTS-APP-SHELL.AppShell
  const { onboarded } = useOnboarded()
  const pathname = usePathname()
  // Day surfaces use the canonical 1120px canvas on lg. Only the Today date
  // screen expands to 1280px on xl so a full event title/time row fits without
  // changing the accepted drilldown and sphere-page baselines.
  const wideCanvas = pathname?.startsWith("/day") ?? false
  const extraWideTodayCanvas = pathname === "/day/today"
    || /^\/day\/\d{4}-\d{2}-\d{2}\/?$/u.test(pathname ?? "")

  logger.debug('[AppShell] Render', { extra: { onboarded } })

  return (
    <main className="h-[var(--app-height)] overflow-hidden bg-background">
      <div className={`mx-auto flex h-full max-w-md flex-col border-x border-border/50 bg-background ${wideCanvas ? "lg:max-w-[1120px]" : ""} ${extraWideTodayCanvas ? "xl:max-w-[1280px]" : ""}`}>
        <div className="flex-1 overflow-y-auto overscroll-contain">
          {children}
        </div>
        <TabBar />
      </div>
    </main>
  )
}
// END_BLOCK: APP_SHELL_COMPONENT
