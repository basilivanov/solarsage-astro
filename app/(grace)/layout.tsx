
// ############################################################################
// AI_HEADER: MODULE_(GRACE)_LAYOUT
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Next.js page — app/(grace)/layout.tsx
// owns:
//   - app/(grace)/layout.tsx
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
// module: M-WEB-GRACE-LAYOUT
// wave: W-2.7
// purpose: Grace app layout with Telegram Web App authentication and AppShell

'use client';

import { useTelegramAuth } from '@/hooks/use-telegram-auth';
import { AppShell } from '@/components/app-shell';
import { ProfileReset } from '@/components/profile-reset';
import { usePathname } from 'next/navigation';
import { logger } from '@/lib/log';

export default function GraceLayout({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated, error } = useTelegramAuth();
  const pathname = usePathname();

  logger.debug('[GraceLayout] Render', { extra: { isLoading, isAuthenticated, error, pathname } });

  if (isLoading) {
    logger.info('[GraceLayout] Showing loading spinner');
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-background"
        data-testid="auth-loading"
      >
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
          <p className="text-sm text-muted-foreground">Авторизация...</p>
        </div>
      </div>
    );
  }

  if (error && typeof window !== 'undefined' && window.Telegram?.WebApp) {
    logger.warn('[GraceLayout] Auth error', { extra: { error } });
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-background px-6"
        data-testid="auth-error"
      >
        <div className="flex w-full max-w-md flex-col gap-3">
          <h1 className="text-balance text-xl font-semibold tracking-tight text-foreground">
            Ошибка авторизации
          </h1>
          <p className="text-pretty text-sm leading-relaxed text-muted-foreground">
            {error}
          </p>
          <p className="text-pretty text-xs leading-relaxed text-muted-foreground">
            Пожалуйста, откройте приложение через Telegram бот.
          </p>
        </div>
      </div>
    );
  }

  logger.info('[GraceLayout] Showing content', { extra: { pathname } });
  const isOnboarding = pathname?.startsWith('/onboarding');

  return (
    <>
      {isOnboarding ? (
        <>{children}</>
      ) : (
        <>
          <AppShell>{children}</AppShell>
          <ProfileReset />
        </>
      )}
    </>
  );
}
