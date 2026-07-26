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
  // Engine ids look like "sun_trine_moon_0" — always prefer the localized form
  // over the raw technical title (which may be an English tech signature).
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
  // Engine tech signature e.g. "Sun trine Moon (1.0°)" or "Луна △ Венера · орб 1°12′".
  const sig = aspect.techSignature || ""
  const glyph = GLYPHS.find((g) => sig.includes(g))
  if (glyph) return glyph
  return ASPECT_SYMBOLS[aspect.id.split("_")[1]?.toLowerCase()] || "△"
}

function extractOrbText(aspect: SynastryAspectItem): string {
  // API provides ready orbLabel ("1°12′") since P3a — prefer it.
  if (aspect.orbLabel) return `орб ${aspect.orbLabel}`
  const sig = aspect.techSignature || ""
  // Engine format: "Sun trine Moon (1.0°)"; макет format: "Луна △ Венера · орб 1°12′".
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
      className="flex w-full items-start justify-between rounded-[18px] border border-border/60 bg-card p-4 text-left transition hover:border-primary/50 active:scale-[0.99] shadow-sm space-x-3 group"
    >
      <div className="flex items-start gap-3 min-w-0 flex-1">
        {/* Aspect Symbol Square */}
        <div
          className={`flex h-9 w-9 flex-none items-center justify-center rounded-[12px] text-[18px] font-bold ${
            tone === "good"
              ? "bg-[var(--syn-good-bg)] text-[var(--syn-good)]"
              : tone === "bad"
              ? "bg-[var(--syn-bad-bg)] text-[var(--syn-bad)]"
              : "bg-[var(--syn-mid-bg)] text-[var(--syn-mid)]"
          }`}
        >
          {symbol}
        </div>

        <div className="space-y-1 min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <h4 className="font-serif text-[15.5px] font-semibold text-foreground truncate">
              {localizedTitle}
            </h4>
            {orbText && (
              <span className="text-[11px] font-medium text-muted-foreground/70 flex-none">
                {orbText}
              </span>
            )}
          </div>

          {aspect.description && (
            <p className="text-[13px] text-foreground/80 leading-relaxed line-clamp-1">
              {aspect.description}
            </p>
          )}

          <span className="block text-[11px] text-primary/80 font-medium pt-0.5 group-hover:underline">
            Нажми — подробное значение и примеры →
          </span>
        </div>
      </div>
    </button>
  )
}
// END_BLOCK: SYNASTRY_ASPECT_ROW
