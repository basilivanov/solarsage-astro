// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_PAIR_HERO
// ROLE: Pair hero section for synastry report screen
// DEPENDENCIES: react, lucide-react, hooks/use-profile, components/synastry/synastry-tone
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-PAIR-HERO
// purpose: Render pair hero with topbar, overlapping avatars, relation eyebrow, title, birth metadata, and precision badge.
// owns:
//   - components/synastry/synastry-pair-hero.tsx
// inputs: partnerName, relationType, partnerBirthDate, partnerBirthTime, partnerBirthCity, precision, onBack
// outputs: SynastryPairHero TSX render
// dependencies: hooks/use-profile, components/synastry/synastry-tone
// side_effects: none
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-SYNASTRY-PAIR-HERO

// START_MODULE_MAP: M-SYNASTRY-PAIR-HERO
// public_entrypoints:
//   - SynastryPairHero
// semantic_blocks: none
// owned_tests: none
// END_MODULE_MAP: M-SYNASTRY-PAIR-HERO

"use client"

import { ChevronLeft, Share2, Info } from "lucide-react"
import { useProfile } from "@/hooks/use-profile"
import { getRelationLabel } from "./synastry-tone"

type Props = {
  partnerName: string
  relationType: string
  partnerBirthDate: string
  partnerBirthTime?: string | null
  partnerBirthCity?: string | null
  precision: "exact" | "approximate"
  onBack: () => void
}

function formatDateRu(isoDateStr: string): string {
  try {
    const d = new Date(isoDateStr)
    return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" })
  } catch {
    return isoDateStr
  }
}

// START_BLOCK: SYNASTRY_PAIR_HERO
export function SynastryPairHero({
  partnerName,
  relationType,
  partnerBirthDate,
  partnerBirthTime,
  partnerBirthCity,
  precision,
  onBack,
}: Props) {
  const { profile } = useProfile()

  const isApproximate = precision === "approximate"

  const ownerDateStr = profile.birthday ? formatDateRu(profile.birthday) : ""
  const partnerDateStr = partnerBirthDate ? formatDateRu(partnerBirthDate) : ""

  const metaParts = [ownerDateStr, partnerDateStr]
  if (!isApproximate && partnerBirthTime) {
    metaParts.push(partnerBirthTime.slice(0, 5))
  }
  if (partnerBirthCity) {
    metaParts.push(partnerBirthCity)
  }

  const metaLine = metaParts.filter(Boolean).join(" · ")

  return (
    <section className="space-y-5" data-testid="synastry-hero">
      {/* Topbar */}
      <div className="flex h-[58px] items-center justify-between">
        <button
          type="button"
          aria-label="Назад"
          onClick={onBack}
          className="flex h-10 w-10 items-center justify-center rounded-[14px] border border-border/70 bg-card text-foreground transition active:scale-95 shadow-sm"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>

        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Совместимость
        </span>

        <button
          type="button"
          disabled
          aria-disabled="true"
          aria-label="Поделиться (скоро)"
          className="flex h-10 w-10 items-center justify-center rounded-[14px] border border-border/40 bg-card/40 text-muted-foreground/40 cursor-not-allowed"
        >
          <Share2 className="h-4 w-4" />
        </button>
      </div>

      {/* Hero Content (Centered) */}
      <div className="flex flex-col items-center text-center space-y-3 pt-1 pb-3">
        {/* Overlapping Avatars */}
        <div className="flex items-center justify-center -space-x-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-[18px] bg-primary text-primary-foreground font-serif font-bold text-[20px] shadow-md border-2 border-background z-10">
            {profile.name ? profile.name.slice(0, 1).toUpperCase() : "Ты"}
          </div>
          <div className="flex h-14 w-14 items-center justify-center rounded-[18px] bg-[var(--syn-ink)] text-[var(--syn-lavender)] font-serif font-bold text-[20px] shadow-md border-2 border-background z-0">
            {partnerName.slice(0, 1).toUpperCase()}
          </div>
        </div>

        {/* Eyebrow Relation */}
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#795a86]">
          {getRelationLabel(relationType)}
        </span>

        {/* H1 Title */}
        <h1 className="font-serif text-[32px] sm:text-[34px] font-normal leading-[1.05] tracking-tight text-foreground">
          Ты + {partnerName}
        </h1>

        {/* Meta Line */}
        {metaLine && (
          <p className="text-[12.5px] text-muted-foreground max-w-[40ch]">
            {metaLine}
          </p>
        )}

        {/* Precision Badge */}
        {isApproximate && (
          <div
            data-testid="synastry-precision-badge"
            className="inline-flex items-center gap-1.5 rounded-full bg-[var(--syn-mid-bg)] border border-[var(--syn-mid)]/30 px-3.5 py-1 text-[11.5px] font-medium text-[var(--syn-mid)]"
          >
            <Info className="h-3.5 w-3.5 flex-none" />
            <span>Примерный расчёт · без ASC и домов партнёра</span>
          </div>
        )}
      </div>
    </section>
  )
}
// END_BLOCK: SYNASTRY_PAIR_HERO
