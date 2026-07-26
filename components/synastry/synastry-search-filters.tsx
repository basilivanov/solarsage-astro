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
    <div className="space-y-3 px-4" data-testid="synastry-search-filters">
      {/* Search Input */}
      <div className="relative">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-[#7d7284]" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Найти по имени"
          data-testid="synastry-search-input"
          className="w-full h-[48px] rounded-[17px] border border-[#e8e0e8] bg-white/82 dark:bg-[#2d2233]/82 px-[44px] text-[16px] text-black dark:text-[#f1e9f4] placeholder:text-[#7d7284]/70 focus:border-[#795a86]/50 focus:ring-4 focus:ring-[#795a86]/08 focus:outline-none transition"
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
              className={`flex-none rounded-full px-3 py-[9px] text-[12px] font-[730] transition active:scale-95 ${
                isActive
                  ? "bg-[#3e3347] dark:bg-[#f1e9f4] text-white dark:text-[#3e3347]"
                  : "bg-white/72 dark:bg-[#2d2233]/72 border border-[#e8e0e8] text-[#7d7284] hover:border-[#795a86]/40 hover:text-[#3e3347]"
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
