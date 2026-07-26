// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_SCREEN
// ROLE: Main synastry screen component displaying list of partner comparisons and add CTA
// DEPENDENCIES: react, lucide-react, lib/api/synastry
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-SCREEN
// purpose: Main synastry screen component managing partner list, search filter, and add partner sheet.
// owns:
//   - components/synastry/synastry-screen.tsx
// inputs: onSelectPartner
// outputs: SynastryScreen TSX render
// dependencies: lib/api/synastry, components/synastry/synastry-list-hero, components/synastry/synastry-search-filters, components/synastry/synastry-partner-card, components/synastry/synastry-add-sheet
// side_effects: fetches partners list on mount
// emitted_logs: none
// failure_policy: inline error state
// END_MODULE_CONTRACT: M-SYNASTRY-SCREEN

// START_MODULE_MAP: M-SYNASTRY-SCREEN
// public_entrypoints:
//   - SynastryScreen
// semantic_blocks:
//   - SYNASTRY_SCREEN: Main synastry list screen component
// owned_tests:
//   - __tests__/synastry/synastry-screen.test.tsx
// END_MODULE_MAP: M-SYNASTRY-SCREEN

"use client"

import { useEffect, useState } from "react"
import { AlertCircle, Users, Sparkles, RefreshCw } from "lucide-react"
import {
  deleteSynastryPartner,
  getSynastryPartners,
  type SynastryPartnerListItem,
} from "@/lib/api/synastry"
import { SynastryListHero } from "./synastry-list-hero"
import { SynastrySearchFilters } from "./synastry-search-filters"
import { SynastryPartnerCard } from "./synastry-partner-card"
import { SynastryAddSheet } from "./synastry-add-sheet"
import { normalizeSynastryTone } from "./synastry-tone"

type Props = {
  onSelectPartner: (partnerId: string) => void
}

// START_BLOCK: SYNASTRY_SCREEN
export function SynastryScreen({ onSelectPartner }: Props) {
  const [partners, setPartners] = useState<SynastryPartnerListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [searchQuery, setSearchQuery] = useState("")
  const [activeFilter, setActiveFilter] = useState<"all" | "good" | "mid" | "bad">("all")
  const [addSheetOpen, setAddSheetOpen] = useState(false)

  async function loadPartners() {
    setLoading(true)
    setError(null)
    try {
      const data = await getSynastryPartners()
      setPartners(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить список пар.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadPartners()
  }, [])

  async function handleDeletePartner(partnerId: string) {
    if (!confirm("Удалить совпадение для этого партнёра?")) return

    try {
      await deleteSynastryPartner(partnerId)
      setPartners((prev) => prev.filter((p) => p.id !== partnerId))
    } catch {
      alert("Не удалось удалить партнёра.")
    }
  }

  const filteredPartners = partners.filter((p) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim()
      if (!p.name.toLowerCase().includes(q)) return false
    }
    if (activeFilter !== "all") {
      const normTone = normalizeSynastryTone(p.status)
      if (normTone !== activeFilter) return false
    }
    return true
  })

  // Find max score among ready reports to show "best match" ribbon
  const readyPartners = partners.filter((p) => p.score !== null && p.reportState === "ready")
  const maxScore = readyPartners.length > 1 ? Math.max(...readyPartners.map((p) => p.score || 0)) : -1

  const stateStr = loading ? "loading" : error ? "error" : filteredPartners.length === 0 ? "empty" : "ready"

  return (
    <div className="space-y-6 pb-16" data-testid="synastry-screen" data-state={stateStr}>
      {/* Product Hero */}
      <SynastryListHero onAddClick={() => setAddSheetOpen(true)} />

      {/* Search & Filters */}
      <SynastrySearchFilters
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        activeFilter={activeFilter}
        onFilterChange={setActiveFilter}
      />

      {/* List Section Header */}
      <div className="flex items-baseline justify-between pt-2">
        <h2 className="font-serif text-[20px] font-semibold text-foreground">
          Твои сравнения
        </h2>
        <span className="text-[12px] text-muted-foreground">
          {partners.length} {partners.length === 1 ? "человек" : "человека"}
        </span>
      </div>

      {/* Content States */}
      {loading ? (
        <div className="flex h-48 flex-col items-center justify-center gap-3" role="status">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span className="text-[13px] text-muted-foreground">Загружаем список сравнений…</span>
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-destructive/20 bg-destructive/10 p-5 text-center space-y-3" role="alert">
          <AlertCircle className="mx-auto h-6 w-6 text-destructive" />
          <p className="text-[13.5px] text-destructive">{error}</p>
          <button
            type="button"
            onClick={loadPartners}
            className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-4 py-1.5 text-[12.5px] font-medium text-primary"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Повторить
          </button>
        </div>
      ) : filteredPartners.length === 0 ? (
        <div className="rounded-3xl border border-border/70 bg-card p-8 text-center space-y-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Users className="h-7 w-7" />
          </div>
          {searchQuery.trim() ? (
            <div className="space-y-2">
              <h3 className="font-serif text-[18px] font-semibold text-foreground">По этому имени никого нет</h3>
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("")
                  setActiveFilter("all")
                }}
                className="text-[13px] font-medium text-primary underline"
              >
                Сбросить поиск
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <h3 className="font-serif text-[18px] font-semibold text-foreground">Добавь первого человека</h3>
              <p className="text-[13px] text-muted-foreground max-w-[32ch] mx-auto leading-relaxed">
                Сравним ваши карты и покажем не только общий балл, но и конкретные точки притяжения и трения.
              </p>
              <button
                type="button"
                onClick={() => setAddSheetOpen(true)}
                className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-[13.5px] font-semibold text-primary-foreground transition active:scale-95 shadow-sm"
              >
                <Sparkles className="h-4 w-4" /> Добавить первого человека
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filteredPartners.map((partner) => {
            const isBest =
              maxScore > 0 &&
              partner.score === maxScore &&
              partner.reportState === "ready"

            return (
              <SynastryPartnerCard
                key={partner.id}
                partner={partner}
                isBestMatch={isBest}
                onSelect={onSelectPartner}
                onDelete={handleDeletePartner}
              />
            )
          })}
        </div>
      )}

      {/* Add Partner Modal Sheet */}
      <SynastryAddSheet
        open={addSheetOpen}
        onClose={() => setAddSheetOpen(false)}
        onSuccess={(partnerId) => {
          void loadPartners()
          onSelectPartner(partnerId)
        }}
      />
    </div>
  )
}
// END_BLOCK: SYNASTRY_SCREEN
