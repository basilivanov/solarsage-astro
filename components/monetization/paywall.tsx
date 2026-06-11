
// ############################################################################
// AI_HEADER: MODULE_MONETIZATION_PAYWALL
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/monetization/paywall.tsx
// owns:
//   - components/monetization/paywall.tsx
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

"use client"

import { Lock, Crown, UserPlus } from "lucide-react"
import { cn } from "@/lib/utils"

type Props = {
  /** Заголовок блока. По умолчанию — «Твой персональный разбор уже готов». */
  title?: string
  /** Подпись под заголовком. По умолчанию — объяснение про подписку и приглашение. */
  description?: string
  /** Компактный вариант — для календаря/списка. */
  compact?: boolean
  className?: string
}

export function Paywall({
  title = "Твой персональный разбор уже готов",
  description = "Полный текст и блок «Почему так у меня» доступны по подписке — или пригласи друга, и вы оба получите 14 дней.",
  compact = false,
  className,
}: Props) {
  return (
    <section
      aria-label="Открыть доступ"
      className={cn(
        "mx-5 overflow-hidden rounded-2xl border border-border/70 bg-card",
        compact ? "p-5" : "p-6",
        className,
      )}
    >
      <div className="flex flex-col items-center text-center">
        <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-full border border-border/70 bg-secondary/60 text-muted-foreground">
          <Lock className="h-[18px] w-[18px]" strokeWidth={1.5} />
        </div>
        <h3 className="text-balance font-serif text-[22px] leading-tight tracking-tight text-foreground">
          {title}
        </h3>
        {description ? (
          <p className="mt-2 max-w-[30ch] text-pretty text-[13.5px] leading-relaxed text-muted-foreground">
            {description}
          </p>
        ) : null}
      </div>

      <div className="mt-5 flex flex-col gap-2">
        <button
          type="button"
          className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-foreground px-5 text-[13px] font-medium text-background transition active:scale-[0.99]"
        >
          <Crown className="h-4 w-4" strokeWidth={1.75} />
          Оформить подписку
        </button>
        <button
          type="button"
          className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-border/70 bg-card px-5 text-[13px] font-medium text-foreground transition active:scale-[0.99]"
        >
          <UserPlus className="h-4 w-4" strokeWidth={1.75} />
          Пригласить друга · +14 дней
        </button>
      </div>
    </section>
  )
}
