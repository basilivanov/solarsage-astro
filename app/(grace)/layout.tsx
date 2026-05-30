// AI_HEADER
// module: M-WEB-GRACE-LAYOUT
// wave: W-2.2
// purpose: Grace app layout with Telegram Web App authentication

'use client';

import { useTelegramAuth } from '@/hooks/use-telegram-auth';

export default function GraceLayout({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated, error } = useTelegramAuth();

  if (isLoading) {
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

  // In dev mode (not in Telegram) - show content without auth
  // In production (Telegram) - show error if not authenticated
  if (error && typeof window !== 'undefined' && window.Telegram?.WebApp) {
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

  // Show content (works both with auth and without in dev mode)
  return <>{children}</>;
}
