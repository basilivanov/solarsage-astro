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
// dependencies: lib/api/synastry, components/synastry/synastry-add-sheet
// side_effects: fetches partners list on mount
// emitted_logs: none
// failure_policy: inline error state
// END_MODULE_CONTRACT: M-SYNASTRY-SCREEN

// START_MODULE_MAP: M-SYNASTRY-SCREEN
// public_entrypoints:
//   - SynastryScreen
// semantic_blocks:
//   - SYNASTRY_SCREEN: Main synastry list screen component
// owned_tests: none
// END_MODULE_MAP: M-SYNASTRY-SCREEN

"use client"

import { useEffect, useState } from "react"
import { Plus, Search, Sparkles, AlertCircle, Heart, Users, Trash2 } from "lucide-react"
import {
  deleteSynastryPartner,
  getSynastryPartners,
  type SynastryPartnerListItem,
} from "@/lib/api/synastry"
import { SynastryAddSheet } from "./synastry-add-sheet"

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

  async function handleDeletePartner(e: React.MouseEvent, partnerId: string) {
    e.stopPropagation()
    if (!confirm("Удалить совпадение для этого партнёра?")) return

    try {
      await deleteSynastryPartner(partnerId)
      setPartners((prev) => prev.filter((p) => p.id !== partnerId))
    } catch (err) {
      alert("Не удалось удалить партнёра.")
    }
  }

  const filteredPartners = partners.filter((p) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim()
      if (!p.name.toLowerCase().includes(q)) return false
    }
    if (activeFilter !== "all") {
      if (p.status !== activeFilter) return false
    }
    return true
  })

  const stateStr = loading ? "loading" : error ? "error" : filteredPartners.length === 0 ? "empty" : "ready"

  return (
    <div className="space-y-6 pb-12" data-testid="synastry-screen" data-state={stateStr}>
      {/* Header & Add CTA */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="font-serif text-[26px] font-bold text-foreground leading-tight">Вместе</h1>
          <p className="text-[13.5px] text-muted-foreground">Совместимость и гармония натальных карт</p>
        </div>
        <button
          type="button"
          onClick={() => setAddSheetOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-full bg-primary px-4 py-2.5 text-[13.5px] font-semibold text-primary-foreground transition active:scale-[0.98] shadow-sm"
        >
          <Plus className="h-4 w-4" /> Добавить
        </button>
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Поиск по имени…"
          className="w-full rounded-2xl border border-border/70 bg-card pl-10 pr-4 py-2.5 text-[14px] text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
        />
      </div>

      {/* Status Filter Buttons */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {[
          { id: "all", label: "Все" },
          { id: "good", label: "Хорошо подходит" },
          { id: "mid", label: "Нормально" },
          { id: "bad", label: "Сложно" },
        ].map((btn) => (
          <button
            key={btn.id}
            type="button"
            aria-pressed={activeFilter === btn.id}
            onClick={() => setActiveFilter(btn.id as any)}
            className={`flex-none rounded-full border px-3.5 py-1.5 text-[12.5px] font-medium transition active:scale-95 ${
              activeFilter === btn.id
                ? "border-primary bg-primary text-primary-foreground font-semibold"
                : "border-border/70 bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground"
            }`}
          >
            {btn.label}
          </button>
        ))}
      </div>

      {/* Content States */}
      {loading ? (
        <div className="flex h-48 flex-col items-center justify-center gap-3">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span className="text-[13px] text-muted-foreground">Загружаем список сравнений…</span>
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-destructive/20 bg-destructive/10 p-5 text-center space-y-2">
          <AlertCircle className="mx-auto h-6 w-6 text-destructive" />
          <p className="text-[13.5px] text-destructive">{error}</p>
        </div>
      ) : filteredPartners.length === 0 ? (
        <div className="rounded-3xl border border-border/70 bg-card p-8 text-center space-y-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Users className="h-7 w-7" />
          </div>
          <div className="space-y-1">
            <h3 className="font-serif text-[18px] font-semibold text-foreground">Никого не нашли…</h3>
            <p className="text-[13px] text-muted-foreground max-w-[30ch] mx-auto">
              Добавьте близкого человека, чтобы рассчитать совместимость ваших натальных карт.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setAddSheetOpen(true)}
            className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-[13.5px] font-semibold text-primary-foreground transition active:scale-95"
          >
            <Sparkles className="h-4 w-4" /> Добавить первого человека
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredPartners.map((partner) => (
            <button
              key={partner.id}
              type="button"
              data-testid="synastry-card"
              data-status={partner.status || "mid"}
              onClick={() => onSelectPartner(partner.id)}
              className="flex w-full items-start justify-between rounded-3xl border border-border/70 bg-card p-5 text-left transition hover:border-primary/50 active:scale-[0.99] shadow-sm relative group"
            >
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/20 text-accent-foreground font-serif font-bold text-[16px]">
                    {partner.name.slice(0, 1)}
                  </div>
                  <div>
                    <h3 className="font-serif text-[18px] font-semibold text-foreground leading-snug">
                      {partner.name}
                    </h3>
                    <span className="text-[11.5px] text-muted-foreground capitalize">
                      {partner.relationType === "romantic" ? "Романтическая пара" : partner.relationType}
                    </span>
                  </div>
                </div>

                {partner.summary && (
                  <p className="text-[13px] text-muted-foreground line-clamp-2 leading-relaxed">
                    {partner.summary}
                  </p>
                )}
              </div>

              <div className="flex flex-col items-end gap-2 flex-none pl-3">
                {partner.score !== null ? (
                  <div className="flex items-baseline gap-1">
                    <span className="font-serif text-[24px] font-bold text-primary">{partner.score}</span>
                    <span className="text-[11px] text-muted-foreground">/100</span>
                  </div>
                ) : (
                  <span className="rounded-full bg-muted px-2.5 py-0.5 text-[11px] text-muted-foreground">Считаем…</span>
                )}

                <span
                  role="button"
                  tabIndex={0}
                  onClick={(e) => handleDeletePartner(e, partner.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault()
                      handleDeletePartner(e as any, partner.id)
                    }
                  }}
                  aria-label="Удалить партнёра"
                  className="opacity-0 group-hover:opacity-100 transition text-muted-foreground hover:text-destructive p-1 cursor-pointer"
                >
                  <Trash2 className="h-4 w-4" />
                </span>
              </div>
            </button>
          ))}
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
