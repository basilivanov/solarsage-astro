// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_ASPECT_ROW
// ROLE: Aspect row item component for synastry wheel aspect list
// DEPENDENCIES: react, components/synastry/synastry-tone
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-ASPECT-ROW
// purpose: Render aspect row with symbol, localized Russian title, orb, description, and drilldown hint.
// owns:
//   - components/synastry/synastry-aspect-row.tsx
// inputs: aspect, onClick
// outputs: SynastryAspectRow TSX render
// dependencies: components/synastry/synastry-tone, lib/api/synastry
// side_effects: none
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-SYNASTRY-ASPECT-ROW

// START_MODULE_MAP: M-SYNASTRY-ASPECT-ROW
// public_entrypoints:
//   - SynastryAspectRow
// semantic_blocks: none
// owned_tests: none
// END_MODULE_MAP: M-SYNASTRY-ASPECT-ROW

"use client"

import type { SynastryAspectItem } from "@/lib/api/synastry"
import { normalizeSynastryTone } from "./synastry-tone"

type Props = {
  aspect: SynastryAspectItem
  onClick: (aspectId: string) => void
}

const ASPECT_SYMBOLS: Record<string, string> = {
  conjunction: "☌",
  conjunct: "☌",
  conj: "☌",
  trine: "△",
  sextile: "⚹",
  square: "□",
  opposition: "☍",
  quincunx: "⚹",
}

const GLYPHS = ["☌", "△", "⚹", "□", "☍"]

const PLANET_RU: Record<string, string> = {
  sun: "Солнце",
  moon: "Луна",
  mercury: "Меркурий",
  venus: "Венера",
  mars: "Марс",
  jupiter: "Юпитер",
  saturn: "Сатурн",
  uranus: "Уран",
  neptune: "Нептун",
  pluto: "Плутон",
  ascendant: "Асцендент",
  asc: "Асцендент",
  midheaven: "MC",
  mc: "MC",
}

const ASPECT_TYPE_RU: Record<string, string> = {
  conjunction: "соединение",
  conjunct: "соединение",
  conj: "соединение",
  trine: "тригон",
  sextile: "секстиль",
  square: "квадрат",
  opposition: "оппозиция",
  quincunx: "квиконс",
}

function formatLocalizedTitle(aspect: SynastryAspectItem): string {
  const parts = aspect.id.split("_")
  if (parts.length >= 3) {
    const op = PLANET_RU[parts[0].toLowerCase()] || parts[0]
    const asp = ASPECT_TYPE_RU[parts[1].toLowerCase()] || parts[1]
    const pp = PLANET_RU[parts[2].toLowerCase()] || parts[2]
    return `${op} ${asp} ${pp}`
  }
  if (aspect.title && !aspect.title.includes("_")) {
    return aspect.title
  }
  return aspect.title || aspect.id
}

function extractAspectSymbol(aspect: SynastryAspectItem): string {
  const sig = aspect.techSignature || ""
  const glyph = GLYPHS.find((g) => sig.includes(g))
  if (glyph) return glyph
  return ASPECT_SYMBOLS[aspect.id.split("_")[1]?.toLowerCase()] || "△"
}

function extractOrbText(aspect: SynastryAspectItem): string {
  if (aspect.orbLabel) return `орб ${aspect.orbLabel}`
  const sig = aspect.techSignature || ""
  const paren = sig.match(/\(([^)]*°[^)]*)\)/)
  if (paren) return `орб ${paren[1]}`
  if (sig.includes("·")) {
    const tail = sig.split("·").slice(-1)[0].trim()
    if (tail.includes("°") || tail.includes("′")) return tail
  }
  return ""
}

// START_BLOCK: SYNASTRY_ASPECT_ROW
export function SynastryAspectRow({ aspect, onClick }: Props) {
  const tone = normalizeSynastryTone(aspect.tone)
  const symbol = extractAspectSymbol(aspect)
  const orbText = extractOrbText(aspect)
  const localizedTitle = formatLocalizedTitle(aspect)

  return (
    <button
      type="button"
      data-testid="synastry-aspect"
      data-tone={aspect.tone}
      onClick={() => onClick(aspect.id)}
      className="flex w-full flex-col rounded-[16px] border border-[#e8e0e8] bg-white dark:bg-[#2d2233] p-[11px] text-left transition hover:border-[#795a86]/45 active:scale-[0.99] active:shadow-[0_0_0_3px_rgba(121,90,134,0.07)] space-y-1.5 group"
    >
      <div className="flex items-center justify-between gap-2 w-full">
        <div className="flex items-center gap-2.5 min-w-0">
          {/* Symbol Square 27x27 r10 font 15px/850 */}
          <div
            className={`flex h-[27px] w-[27px] flex-none items-center justify-center rounded-[10px] text-[15px] font-[850] ${
              tone === "good"
                ? "bg-[#eaf5f0] text-[#43806d] dark:bg-[#1c2b25] dark:text-[#63a893]"
                : tone === "bad"
                ? "bg-[#fae9ec] text-[#a64d59] dark:bg-[#2d1c20] dark:text-[#c96b77]"
                : "bg-[#fbf1de] text-[#b07b36] dark:bg-[#2d261a] dark:text-[#d49a4f]"
            }`}
          >
            {symbol}
          </div>

          {/* Title Inter 13px/830 (NOT serif) */}
          <h4 className="font-sans text-[13px] font-[830] text-[#3e3347] dark:text-[#f1e9f4]">
            {localizedTitle}
          </h4>
        </div>

        {orbText && (
          <span className="text-[10px] font-bold text-[#7d7284] flex-none">
            {orbText}
          </span>
        )}
      </div>

      {/* Human Description & Hint */}
      <div className="pl-[35px] space-y-1">
        {aspect.description && (
          <p className="text-[12px] leading-[1.4] text-[#7d7284] dark:text-muted-foreground line-clamp-2">
            {aspect.description}
          </p>
        )}

        <span className="block text-[11px] font-semibold text-[#795a86] dark:text-[#c8a9d6] group-hover:underline">
          Нажми — подробное значение и примеры
        </span>
      </div>
    </button>
  )
}
// END_BLOCK: SYNASTRY_ASPECT_ROW
