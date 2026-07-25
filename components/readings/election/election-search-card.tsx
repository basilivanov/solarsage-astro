// ############################################################################
// AI_HEADER: MODULE_ELECTION_SEARCH_CARD
// ROLE: Search history item card
// ############################################################################

// START_MODULE_CONTRACT: M-ELECTION-SEARCH-CARD
// purpose: Render election search history card component.
// owns:
//   - components/readings/election/election-search-card.tsx
// inputs: search (ElectionSearch)
// outputs: ElectionSearchCard React component
// dependencies: lib/contracts/election
// side_effects: none (pure rendering / Link)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-ELECTION-SEARCH-CARD

// START_MODULE_MAP: M-ELECTION-SEARCH-CARD
// public_entrypoints:
//   - ElectionSearchCard
// semantic_blocks:
//   - ELECTION_SEARCH_CARD_COMPONENT: Search history list item card component
// owned_tests:
//   - __tests__/readings/election-form.test.tsx
// END_MODULE_MAP: M-ELECTION-SEARCH-CARD

"use client"

import Link from "next/link"
import { Calendar, ChevronRight } from "lucide-react"
import { ELECTION_CATEGORIES, type ElectionSearch } from "@/lib/contracts/election"

type Props = {
  search: ElectionSearch
}

// START_BLOCK: ELECTION_SEARCH_CARD_COMPONENT
export function ElectionSearchCard({ search }: Props) {
  let emoji = "🗓"
  let label = search.eventType

  for (const cat of ELECTION_CATEGORIES) {
    if (search.eventType.startsWith(cat.key)) {
      emoji = cat.emoji
    }
    for (const sub of cat.subs) {
      if (search.eventType.endsWith(sub.key)) {
        label = sub.label
      }
    }
  }

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
// END_BLOCK: ELECTION_SEARCH_CARD_COMPONENT
