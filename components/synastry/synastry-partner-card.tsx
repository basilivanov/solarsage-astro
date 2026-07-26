// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_PARTNER_CARD
// ROLE: Partner comparison item card for synastry list screen
// DEPENDENCIES: react, lucide-react, components/synastry/synastry-tone
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-PARTNER-CARD
// purpose: Render partner summary card with score, status pill, summary, tone counters, precision indicator, and best match ribbon.
// owns:
//   - components/synastry/synastry-partner-card.tsx
// inputs: partner, isBestMatch, onSelect, onDelete
// outputs: SynastryPartnerCard TSX render
// dependencies: components/synastry/synastry-tone, lib/api/synastry
// side_effects: none
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-SYNASTRY-PARTNER-CARD

// START_MODULE_MAP: M-SYNASTRY-PARTNER-CARD
// public_entrypoints:
//   - SynastryPartnerCard
// semantic_blocks: none
// owned_tests:
//   - __tests__/synastry/synastry-partner-card.test.tsx
// END_MODULE_MAP: M-SYNASTRY-PARTNER-CARD

"use client"

import { Trash2, Info, Loader2 } from "lucide-react"
import type { SynastryPartnerListItem } from "@/lib/api/synastry"
import {
  getRelationLabel,
  getToneStatusLabel,
  normalizeSynastryTone,
} from "./synastry-tone"

type Props = {
  partner: SynastryPartnerListItem
  isBestMatch?: boolean
  onSelect: (id: string) => void
  onDelete: (id: string) => void
}

// START_BLOCK: SYNASTRY_PARTNER_CARD
export function SynastryPartnerCard({
  partner,
  isBestMatch = false,
  onSelect,
  onDelete,
}: Props) {
  const tone = normalizeSynastryTone(partner.status)
  const isPending =
    partner.reportState &&
    ["pending", "calculating", "narrative_generating"].includes(partner.reportState)
  const isApproximate = partner.precision === "approximate"

  const counters = partner.counters || { good: 0, mid: 0, bad: 0 }

  return (
    <article
      data-testid="synastry-card"
      data-status={partner.status || "mid"}
      className="relative flex flex-col rounded-[24px] border border-border/70 bg-card p-5 transition hover:border-primary/40 shadow-sm space-y-3 group"
    >
      {/* Best Match Ribbon */}
      {isBestMatch && !isPending && partner.score !== null && (
        <div
          data-testid="synastry-best-match-ribbon"
          className="self-start rounded-full bg-[var(--syn-good-bg)] text-[var(--syn-good)] px-3 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em]"
        >
          ЛУЧШЕЕ СОВПАДЕНИЕ
        </div>
      )}

      {/* Main card interactive area */}
      <button
        type="button"
        data-testid="synastry-card-click"
        onClick={() => onSelect(partner.id)}
        className="w-full text-left space-y-3 focus:outline-none"
      >
        {/* Top Header Row: Avatar, Name, Relation, Score */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-[46px] w-[46px] flex-none items-center justify-center rounded-[17px] bg-primary/10 text-primary font-serif font-bold text-[18px]">
              {partner.name.slice(0, 1).toUpperCase()}
            </div>
            <div>
              <h3 className="font-serif text-[18px] font-semibold leading-snug text-foreground">
                {partner.name}
              </h3>
              <div className="text-[12px] text-muted-foreground">
                {getRelationLabel(partner.relationType)}
              </div>
            </div>
          </div>

          <div className="flex flex-col items-end flex-none">
            {isPending ? (
              <div className="flex items-center gap-1.5 text-[12px] text-muted-foreground" role="status">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
              </div>
            ) : partner.score !== null ? (
              <div className="flex items-baseline gap-0.5">
                <span className="font-serif text-[29px] font-normal leading-none text-foreground">
                  {partner.score}
                </span>
                <span className="text-[11px] font-normal text-muted-foreground/70">/100</span>
              </div>
            ) : null}
          </div>
        </div>

        {/* Status Pill or Pending Stage */}
        {isPending ? (
          <div className="text-[12.5px] font-medium text-primary">
            {partner.reportState === "narrative_generating"
              ? "Готовим человеческий перевод…"
              : "Собираем аспекты…"}
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <span
              className={`inline-flex rounded-full px-3 py-1 text-[11.5px] font-semibold ${
                tone === "good"
                  ? "bg-[var(--syn-good-bg)] text-[var(--syn-good)]"
                  : tone === "bad"
                  ? "bg-[var(--syn-bad-bg)] text-[var(--syn-bad)]"
                  : "bg-[var(--syn-mid-bg)] text-[var(--syn-mid)]"
              }`}
            >
              {getToneStatusLabel(tone)}
            </span>
          </div>
        )}

        {/* Summary */}
        {partner.summary && !isPending && (
          <p className="text-[14px] leading-relaxed text-foreground/80 line-clamp-2">
            {partner.summary}
          </p>
        )}

        {/* 3 Tone Counter Mini-Blocks */}
        {!isPending && (
          <div className="grid grid-cols-3 gap-2 pt-1" data-testid="synastry-card-counters">
            <div className="rounded-[12px] bg-[var(--syn-good-bg)] px-2.5 py-1.5 text-center">
              <span className="text-[11.5px] font-semibold text-[var(--syn-good)]">
                {counters.good || 0} поддерживают
              </span>
            </div>
            <div className="rounded-[12px] bg-[var(--syn-mid-bg)] px-2.5 py-1.5 text-center">
              <span className="text-[11.5px] font-semibold text-[var(--syn-mid)]">
                {counters.mid || 0} неоднозначны
              </span>
            </div>
            <div className="rounded-[12px] bg-[var(--syn-bad-bg)] px-2.5 py-1.5 text-center">
              <span className="text-[11.5px] font-semibold text-[var(--syn-bad)]">
                {counters.bad || 0} напрягают
              </span>
            </div>
          </div>
        )}

        {/* Approximate precision line */}
        {isApproximate && (
          <div
            data-testid="synastry-precision-note"
            className="flex items-center gap-1.5 text-[11.5px] text-amber-800/90 dark:text-amber-200/90 pt-1"
          >
            <Info className="h-3.5 w-3.5 flex-none" />
            <span>Время рождения неизвестно · расчёт без домов партнёра</span>
          </div>
        )}
      </button>

      {/* Delete button (separate interactive element outside card button) */}
      <button
        type="button"
        aria-label="Удалить партнёра"
        data-testid="synastry-delete-btn"
        onClick={(e) => {
          e.stopPropagation()
          onDelete(partner.id)
        }}
        className="absolute top-4 right-4 flex h-8 w-8 items-center justify-center rounded-full text-muted-foreground/50 hover:text-destructive transition active:scale-95 opacity-0 group-hover:opacity-100 focus:opacity-100"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </article>
  )
}
// END_BLOCK: SYNASTRY_PARTNER_CARD
