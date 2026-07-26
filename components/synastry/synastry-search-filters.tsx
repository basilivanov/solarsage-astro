// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_SEARCH_FILTERS
// ROLE: Search input and status filter chips for synastry partner list
// DEPENDENCIES: react, lucide-react, components/synastry/synastry-tone
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-SEARCH-FILTERS
// purpose: Search by partner name and filter by compatibility tone status.
// owns:
//   - components/synastry/synastry-search-filters.tsx
// inputs: searchQuery, onSearchChange, activeFilter, onFilterChange
// outputs: SynastrySearchFilters TSX render
// dependencies: components/synastry/synastry-tone
// side_effects: none
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-SYNASTRY-SEARCH-FILTERS

// START_MODULE_MAP: M-SYNASTRY-SEARCH-FILTERS
// public_entrypoints:
//   - SynastrySearchFilters
// semantic_blocks: none
// owned_tests: none
// END_MODULE_MAP: M-SYNASTRY-SEARCH-FILTERS

"use client"

import { Search } from "lucide-react"

type FilterOption = "all" | "good" | "mid" | "bad"

type Props = {
  searchQuery: string
  onSearchChange: (val: string) => void
  activeFilter: FilterOption
  onFilterChange: (filter: FilterOption) => void
}

const FILTERS: Array<{ id: FilterOption; label: string }> = [
  { id: "all", label: "Все" },
  { id: "good", label: "Хорошо подходит" },
  { id: "mid", label: "Нормально" },
  { id: "bad", label: "Сложно" },
]

// START_BLOCK: SYNASTRY_SEARCH_FILTERS
export function SynastrySearchFilters({
  searchQuery,
  onSearchChange,
  activeFilter,
  onFilterChange,
}: Props) {
  return (
    <div className="space-y-3" data-testid="synastry-search-filters">
      {/* Search Input */}
      <div className="relative">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground/70" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Найти по имени"
          data-testid="synastry-search-input"
          className="w-full h-12 rounded-[17px] border border-border/70 bg-card/80 pl-11 pr-4 py-2.5 text-[14px] text-foreground placeholder:text-muted-foreground/60 focus:border-primary/60 focus:ring-2 focus:ring-primary/20 focus:outline-none transition"
        />
      </div>

      {/* Filter Chips */}
      <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
        {FILTERS.map((item) => {
          const isActive = activeFilter === item.id
          return (
            <button
              key={item.id}
              type="button"
              aria-pressed={isActive}
              data-testid={`synastry-filter-${item.id}`}
              onClick={() => onFilterChange(item.id)}
              className={`flex-none h-8 px-3.5 rounded-full text-[12px] font-medium transition active:scale-95 ${
                isActive
                  ? "bg-[#3e3347] dark:bg-[#f1e9f4] text-[#fffdf9] dark:text-[#3e3347] font-semibold"
                  : "bg-card border border-border/70 text-muted-foreground hover:border-primary/40 hover:text-foreground"
              }`}
            >
              {item.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
// END_BLOCK: SYNASTRY_SEARCH_FILTERS
