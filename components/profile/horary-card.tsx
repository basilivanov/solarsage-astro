import { HelpCircle } from "lucide-react"
import type { HoraryMeta } from "@/lib/profile-meta"

type Props = {
  horary: HoraryMeta
}

/**
 * Карточка-сводка по балансу хорарных вопросов на /profile.
 * Чистый presentational-компонент: данные приходят сверху, действий внутри нет.
 */
export function HoraryCard({ horary }: Props) {
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
            Доступно {horary.left} {horary.left === 1 ? "вопрос" : "вопроса"}
          </div>
          <div className="mt-1 text-[13px] leading-snug text-muted-foreground">
            Следующий начислится через {horary.nextInDays} дн.
          </div>
        </div>
      </div>
    </div>
  )
}
