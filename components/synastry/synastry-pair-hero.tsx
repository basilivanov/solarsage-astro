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
import { formatBirthDate } from "@/lib/profile"
import { getRelationLabel } from "./synastry-tone"
import { useToast } from "@/hooks/use-toast"

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
  const { toast } = useToast()

  const isApproximate = precision === "approximate"

  const ownerDateStr = profile.birthDate ? formatBirthDate(profile.birthDate) : ""
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
    <section className="space-y-4 px-4" data-testid="synastry-hero">
      {/* Topbar */}
      <div className="flex h-[58px] items-center justify-between">
        <button
          type="button"
          aria-label="Назад"
          onClick={onBack}
          className="flex h-[44px] w-[44px] items-center justify-center rounded-[15px] border border-[#795a86]/16 bg-[#fffdf9]/78 dark:bg-[#2d2233]/78 text-[#3e3347] dark:text-[#f1e9f4] transition active:scale-95 shadow-sm"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>

        <span className="text-[12px] font-bold uppercase tracking-[0.13em] text-[#3e3347] dark:text-[#f1e9f4]">
          Совместимость
        </span>

        <button
          type="button"
          aria-label="Поделиться (скоро)"
          onClick={() => toast({ title: "Расшаривание заложено, но пока выключено" })}
          className="flex h-[44px] w-[44px] items-center justify-center rounded-[15px] border border-[#795a86]/16 bg-[#fffdf9]/78 dark:bg-[#2d2233]/78 text-[#7d7284] hover:text-[#3e3347] transition active:scale-95"
        >
          <Share2 className="h-4 w-4" />
        </button>
      </div>

      {/* Hero Content (Centered) */}
      <div className="flex flex-col items-center text-center space-y-3 pt-1 pb-2">
        {/* Overlapping Avatars (74x74, r25, Georgia 29px) */}
        <div className="flex h-[80px] items-center justify-center relative">
          <div
            className="flex h-[74px] w-[74px] items-center justify-center rounded-[25px] bg-[#f1e9f4] text-[#795a86] syn-serif text-[29px] font-normal shadow-[0_8px_22px_rgba(61,49,74,0.1)] border-[5px] border-[#fbf8f2] dark:border-[#2d2233]"
            style={{ transform: "translateX(-27px) rotate(-4deg)" }}
          >
            {profile.firstName ? profile.firstName.slice(0, 1).toUpperCase() : "Ты"}
          </div>
          <div
            className="flex h-[74px] w-[74px] items-center justify-center rounded-[25px] bg-[#3e3347] text-[#f1e9f4] syn-serif text-[29px] font-normal shadow-[0_8px_22px_rgba(61,49,74,0.1)] border-[5px] border-[#fbf8f2] dark:border-[#2d2233]"
            style={{ transform: "translateX(27px) rotate(4deg)" }}
          >
            {partnerName.slice(0, 1).toUpperCase()}
          </div>
        </div>

        {/* Eyebrow Relation */}
        <p className="text-[11px] font-extrabold uppercase tracking-[0.12em] text-[#795a86] mb-0">
          {getRelationLabel(relationType).toUpperCase()}
        </p>

        {/* H1 Title */}
        <h1 className="syn-serif text-[34px] font-medium leading-[1.03] tracking-tight text-[#3e3347] dark:text-[#f1e9f4]">
          Ты + {partnerName}
        </h1>

        {/* Meta Line */}
        {metaLine && (
          <p className="text-[13px] text-[#7d7284] max-w-[40ch]">
            {metaLine}
          </p>
        )}

        {/* Precision Badge */}
        {isApproximate && (
          <div
            data-testid="synastry-precision-badge"
            className="inline-flex items-center gap-1.5 rounded-full bg-[#fbf1de] dark:bg-[#2d261a] border border-[#b07b36]/30 px-3.5 py-1 text-[11.5px] font-medium text-[#b07b36] dark:text-[#d49a4f]"
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
