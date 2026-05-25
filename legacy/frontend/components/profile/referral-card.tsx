"use client"

import { Gift, Users } from "lucide-react"
import type { ReferralMeta } from "@/lib/profile-meta"

type Props = {
  referral: ReferralMeta
  onInvite: () => void
}

/**
 * Карточка реферальной программы на /profile.
 * Показывает потенциальную награду и, если уже есть приглашённые —
 * прогресс-полоску.
 */
export function ReferralCard({ referral, onInvite }: Props) {
  return (
    <div className="rounded-2xl border border-border/70 bg-card p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-primary/10 text-primary">
          <Gift className="h-[18px] w-[18px]" strokeWidth={1.75} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Рефералка
          </div>
          <div className="mt-1 font-serif text-[19px] leading-tight tracking-tight text-foreground">
            Пригласи друга
          </div>
          <div className="mt-1 text-[13px] leading-snug text-muted-foreground">
            Вы оба получите {referral.rewardDays} дней доступа
          </div>
        </div>
      </div>

      {referral.count > 0 ? (
        <div className="mt-4 flex items-center gap-4 rounded-xl bg-muted/50 px-4 py-3 text-[12.5px] text-foreground/75">
          <Users className="h-4 w-4 text-foreground/60" strokeWidth={1.75} />
          <span>
            Приглашено: {referral.count} · начислено {referral.bonusDays} дн.
          </span>
        </div>
      ) : null}

      <button
        type="button"
        onClick={onInvite}
        className="mt-4 flex h-11 w-full items-center justify-center gap-2 rounded-full bg-foreground px-5 text-[14px] font-medium text-background transition active:scale-[0.99]"
      >
        <Gift className="h-4 w-4" strokeWidth={1.75} />
        Пригласить
      </button>
    </div>
  )
}
