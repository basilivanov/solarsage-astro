'use client'

import { Sparkles } from "lucide-react"
import { useRouter } from 'next/navigation'

export function TrialBanner({ daysLeft }: { daysLeft: number }) {
  const router = useRouter()
  const isDev = process.env.NEXT_PUBLIC_DEV_MODE === 'true'

  return (
    <div className="mx-5 flex items-center gap-3 rounded-xl border border-border/70 bg-secondary/40 px-4 py-3">
      <div className="flex h-8 w-8 flex-none items-center justify-center rounded-full bg-accent text-accent-foreground">
        <Sparkles className="h-4 w-4" strokeWidth={1.75} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[12px] font-medium text-foreground">
          14 дней бесплатного доступа
        </div>
        <div className="text-[11.5px] text-muted-foreground">
          Осталось {daysLeft}{" "}
          {daysLeft === 1 ? "день" : daysLeft < 5 ? "дня" : "дней"}
        </div>
        {isDev && (
          <button
            onClick={() => router.push('/debug')}
            className="text-xs text-purple-600 underline mt-1"
          >
            🔍 Debug
          </button>
        )}
      </div>
      <button
        type="button"
        className="rounded-full border border-border/70 bg-card px-3 py-1.5 text-[11px] font-medium text-foreground transition active:scale-[0.97]"
      >
        Подписка
      </button>
    </div>
  )
}
