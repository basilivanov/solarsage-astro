// AI_HEADER
// module: M-WEB-ERROR-BOUNDARY
// wave: W-2.2
// purpose: Error state component

'use client'

import { useRouter } from 'next/navigation'

interface ErrorBoundaryProps {
  error: Error;
  title?: string;
  message?: string;
}

export function ErrorBoundary({ error, title, message }: ErrorBoundaryProps) {
  const router = useRouter()
  const displayTitle = title || 'Ошибка';
  const displayMessage = message || error.message || 'Произошла неизвестная ошибка';
  const isDev = process.env.NEXT_PUBLIC_DEV_MODE === 'true'

  return (
    <div
      className="flex flex-col items-center justify-center px-10 py-12 text-center"
      data-testid="error-boundary"
      role="alert"
    >
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-full border border-border/70 bg-card text-muted-foreground">
        <span className="text-2xl">!</span>
      </div>
      <h2 className="font-serif text-[26px] leading-tight tracking-tight text-foreground">
        {displayTitle}
      </h2>
      <p
        className="mt-2 max-w-[26ch] text-[13px] leading-relaxed text-muted-foreground"
        data-testid="error-message"
      >
        {displayMessage}
      </p>
      {isDev && (
        <button
          onClick={() => router.push('/debug')}
          className="mt-6 rounded-full border border-border/70 bg-card px-5 py-2 text-[13px] font-medium text-foreground transition active:scale-[0.98]"
        >
          Debug Info
        </button>
      )}
    </div>
  );
}
