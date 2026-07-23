// ############################################################################
// AI_HEADER: MODULE_ELECTION_SEARCH_CARD
// ROLE: Search history item card
// ############################################################################

"use client"

import Link from "next/link"
import { Calendar, ChevronRight } from "lucide-react"
import { ELECTION_EVENTS, type ElectionSearch } from "@/lib/contracts/election"

type Props = {
  search: ElectionSearch
}

export function ElectionSearchCard({ search }: Props) {
  const eventInfo = ELECTION_EVENTS.find((e) => e.key === search.eventType)
  const emoji = eventInfo?.emoji || "🗓"
  const label = eventInfo?.label || search.eventType

  const getStatusText = () => {
    switch (search.status) {
      case "pending":
      case "processing":
        return <span className="text-amber-500 font-medium">Считаем...</span>
      case "done":
        return <span className="text-emerald-500 font-medium">Готово</span>
      case "refunded":
        return <span className="text-muted-foreground font-medium">Списание возвращено</span>
      default:
        return <span className="text-destructive font-medium">Не удалось</span>
    }
  }

  return (
    <Link
      href={`/readings/election/${search.id}`}
      className="flex items-center justify-between rounded-xl border border-border/70 bg-card p-4 transition hover:border-primary/50 active:scale-[0.99]"
      data-testid={`election-search-card-${search.id}`}
    >
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary text-[18px]">
          {emoji}
        </div>
        <div>
          <div className="text-[14px] font-semibold text-foreground">{label}</div>
          <div className="flex items-center gap-2 text-[12px] text-muted-foreground mt-0.5">
            <Calendar className="h-3.5 w-3.5" />
            <span>{search.windowFrom} — {search.windowTo}</span>
            <span>•</span>
            {getStatusText()}
          </div>
        </div>
      </div>
      <ChevronRight className="h-5 w-5 text-muted-foreground flex-none" />
    </Link>
  )
}
