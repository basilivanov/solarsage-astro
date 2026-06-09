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
