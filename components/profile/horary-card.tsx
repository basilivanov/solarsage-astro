// ############################################################################
// AI_HEADER: MODULE_PROFILE_HORARY_CARD
// ROLE: UI component for shared credit wallet
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################
// START_MODULE_CONTRACT: M-PROFILE-HORARY-CARD
// purpose: Render shared credit wallet status card on Profile screen.
// owns:
//   - components/profile/horary-card.tsx
// inputs: horary (HoraryMeta)
// outputs: HoraryCard React component
// dependencies: lib/profile-meta
// side_effects: none (pure UI)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-PROFILE-HORARY-CARD

// START_MODULE_MAP: M-PROFILE-HORARY-CARD
// public_entrypoints:
//   - HoraryCard
// semantic_blocks:
//   - HORARY_CARD_COMPONENT: shared credits card component
// owned_tests:
//   - __tests__/components/ProfileScreen.test.tsx
// END_MODULE_MAP: M-PROFILE-HORARY-CARD
import { HelpCircle } from "lucide-react"
import type { HoraryMeta } from "@/lib/profile-meta"

type Props = {
  horary: HoraryMeta
}

// START_BLOCK: HORARY_CARD_COMPONENT
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
    <div className="rounded-2xl border border-border/70 bg-card p-5 space-y-3" data-testid="credits-card">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-accent/60 text-foreground/75">
          <HelpCircle className="h-[18px] w-[18px]" strokeWidth={1.75} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Кредиты на разборы
          </div>
          <div className="mt-1 font-serif text-[19px] leading-tight tracking-tight text-foreground">
            Осталось {total} {pluralRazbor(total)}
          </div>
          <div className="mt-2 text-[13px] leading-snug text-muted-foreground space-y-1">
            {weeklyFreeAvailable ? (
              <div>
                • Бесплатный еженедельный: активен
                {weeklyFreeExpiresAt && ` (до ${formatDate(weeklyFreeExpiresAt)})`}
              </div>
            ) : (
              <div>• Бесплатный еженедельный: потрачен</div>
            )}

            {!weeklyFreeAvailable && nextWeeklyFreeAt && (
              <div>• Следующий бесплатный: {formatDate(nextWeeklyFreeAt)}</div>
            )}

            {bonusCredits > 0 && (
              <div>• Бонусные: {bonusCredits}</div>
            )}

            {paidCredits > 0 && (
              <div>• Платные: {paidCredits}</div>
            )}
          </div>
        </div>
      </div>

      <div className="border-t border-border/40 pt-2 text-[11px] text-muted-foreground/80 leading-relaxed">
        Общие кредиты для хорарных вопросов, выбора дат и синастрии
      </div>
    </div>
  )
}
// END_BLOCK: HORARY_CARD_COMPONENT

function pluralRazbor(n: number) {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return "разбор"
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "разбора"
  return "разборов"
}
