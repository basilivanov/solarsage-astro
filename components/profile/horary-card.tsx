
// ############################################################################
// AI_HEADER: MODULE_PROFILE_HORARY_CARD
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/profile/horary-card.tsx
// owns:
//   - components/profile/horary-card.tsx
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

import { HelpCircle } from "lucide-react"
import type { HoraryMeta } from "@/lib/profile-meta"

type Props = {
  horary: HoraryMeta
}

export function HoraryCard({ horary }: Props) {
  const {
    weeklyFreeAvailable,
    weeklyFreeExpiresAt,
    nextWeeklyFreeAt,
    bonusCredits,
    paidCredits,
  } = horary

  const total = (weeklyFreeAvailable ? 1 : 0) + bonusCredits + paidCredits

  const formatDate = (isoStr?: string | null) => {
    if (!isoStr) return ""
    try {
      const d = new Date(isoStr)
      return d.toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "short",
      })
    } catch {
      return isoStr
    }
  }

  return (
    <div className="rounded-2xl border border-border/70 bg-card p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-accent/60 text-foreground/75">
          <HelpCircle className="h-[18px] w-[18px]" strokeWidth={1.75} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Хорарные вопросы
          </div>
          <div className="mt-1 font-serif text-[19px] leading-tight tracking-tight text-foreground">
            Доступно {total} {pluralQuestions(total)}
          </div>
          <div className="mt-1 text-[13px] leading-snug text-muted-foreground space-y-0.5">
            {weeklyFreeAvailable ? (
              <span>
                • Еженедельный бесплатный: активен
                {weeklyFreeExpiresAt && ` (до ${formatDate(weeklyFreeExpiresAt)})`}
              </span>
            ) : nextWeeklyFreeAt ? (
              <span>
                • Новый бесплатный: {formatDate(nextWeeklyFreeAt)}
              </span>
            ) : null}
            {(paidCredits > 0 || bonusCredits > 0) && (
              <span className="block">
                • Платные/бонусные: {paidCredits + bonusCredits} шт.
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function pluralQuestions(n: number) {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return "вопрос"
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "вопроса"
  return "вопросов"
}
