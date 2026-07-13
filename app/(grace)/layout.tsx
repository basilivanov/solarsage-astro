// ############################################################################
// AI_HEADER: MODULE_GRACE_LAYOUT — isolates local fixture shell from authenticated app shell.
// ROLE: Selects a development-only local fixture shell before mounting normal
//       authentication, onboarding, profile, and AppShell side effects.
// ############################################################################

// START_MODULE_CONTRACT: M-GRACE-LAYOUT
// purpose: Wrap Grace routes in either an authenticated normal shell or an isolated local fixture shell via Suspense-safe route selection.
// owns:
//   - app/(grace)/layout.tsx
// inputs: pathname, fixture query parameter, and children.
// outputs: Normal AppShell/ProfileReset or a local non-auth fixture shell.
// dependencies: next/navigation, Telegram auth/provider, AppShell, TabBar, ProfileReset.
// side_effects: Normal branch performs Telegram auth and mounts onboarding/profile hooks;
//               local fixture branch and Suspense fallback perform none of those side effects.
// emitted_logs: normal branch logger events only.
// invariants:
//   - Local fixture shell requires development mode, exact day path, and exact fixture query.
//   - Fixture shell never mounts useTelegramAuth, AppShell, or ProfileReset.
//   - The outer layout is prerender-safe; search parameters resolve only beneath Suspense.
// failure_policy: Normal branch retains existing auth loading/error states.
// END_MODULE_CONTRACT: M-GRACE-LAYOUT

// START_MODULE_MAP: M-GRACE-LAYOUT
// public_entrypoints:
//   - GraceLayout
// semantic_blocks:
//   - SUSPENSE_ROUTER: side-effect-free fallback and query-aware shell selection.
//   - AUTHENTICATED_SHELL: normal Telegram authentication and app shell.
//   - FIXTURE_SHELL: local non-auth browser preview shell.
// owned_tests:
//   - e2e/dev-timing-fixture.spec.ts
// END_MODULE_MAP: M-GRACE-LAYOUT

"use client"

import { Suspense } from "react"
import { usePathname, useSearchParams } from "next/navigation"
import { useTelegramAuth } from "@/hooks/use-telegram-auth"
import { useTelegram } from "@/components/telegram-provider"
import { AppShell } from "@/components/app-shell"
import { TabBar } from "@/components/today/tab-bar"
import { ProfileReset } from "@/components/profile-reset"
import { logger } from "@/lib/log"

const TIMING_FIXTURE_PATH = "/day/2026-07-08"

// START_BLOCK: SUSPENSE_ROUTER
export default function GraceLayout({ children }: { children: React.ReactNode }) {
  // START_FUNCTION_CONTRACT: F-M-GRACE-LAYOUT.GraceLayout
  // purpose: Wrap Grace routes in a Suspense boundary for client routing.
  // inputs: children React node.
  // returns: Suspense boundary wrapping GraceShellRouter.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: bubbles up on render error.
  // END_FUNCTION_CONTRACT: F-M-GRACE-LAYOUT.GraceLayout
  return (
    <Suspense fallback={<ShellSelectionFallback />}>
      <GraceShellRouter>{children}</GraceShellRouter>
    </Suspense>
  )
}
// END_BLOCK: SUSPENSE_ROUTER

function GraceShellRouter({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const isTimingFixture = process.env.NODE_ENV === "development"
    && pathname === TIMING_FIXTURE_PATH
    && searchParams?.get("fixture") === "three-horizon-timing"

  return isTimingFixture ? <FixtureShell>{children}</FixtureShell> : <AuthenticatedShell pathname={pathname}>{children}</AuthenticatedShell>
}

function ShellSelectionFallback() {
  return <div role="status" aria-busy="true" data-testid="grace-shell-loading" />
}

function AuthenticatedShell({ children, pathname }: { children: React.ReactNode; pathname: string | null }) {
  const { isLoading, isAuthenticated, error } = useTelegramAuth()
  const { inTelegram } = useTelegram()

  logger.debug("[GraceLayout] Render", { extra: { isLoading, isAuthenticated, error, pathname } })

  if (isLoading) {
    logger.info("[GraceLayout] Showing loading spinner")
    return (
      <div className="flex min-h-screen items-center justify-center bg-background" data-testid="auth-loading">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Авторизация...</p>
        </div>
      </div>
    )
  }

  if (error && inTelegram) {
    logger.warn("[GraceLayout] Auth error", { extra: { error } })
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-6" data-testid="auth-error">
        <div className="flex w-full max-w-md flex-col gap-3">
          <h1 className="text-balance text-xl font-semibold tracking-tight text-foreground">Ошибка авторизации</h1>
          <p className="text-pretty text-sm leading-relaxed text-muted-foreground">{error}</p>
          <p className="text-pretty text-xs leading-relaxed text-muted-foreground">Пожалуйста, откройте приложение через Telegram бот.</p>
        </div>
      </div>
    )
  }

  logger.info("[GraceLayout] Showing content", { extra: { pathname } })
  const isOnboarding = pathname?.startsWith("/onboarding")
  return isOnboarding ? <>{children}</> : <><AppShell>{children}</AppShell><ProfileReset /></>
}

function FixtureShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="h-[var(--app-height)] overflow-hidden bg-background" data-testid="dev-timing-fixture-shell">
      <div className="mx-auto flex h-full max-w-md flex-col border-x border-border/50 bg-background">
        <div className="flex-1 overflow-y-auto overscroll-contain">{children}</div>
        <TabBar />
      </div>
    </main>
  )
}
