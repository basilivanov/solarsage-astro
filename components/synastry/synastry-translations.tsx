// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_TRANSLATIONS
// ROLE: Human translations section component for synastry report screen
// DEPENDENCIES: react, components/synastry/synastry-tone, lib/api/synastry
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-TRANSLATIONS
// purpose: Render human translation cards with tone dot, title, tech signature drilldown link, text, and scene box.
// owns:
//   - components/synastry/synastry-translations.tsx
// inputs: translations, onOpenAspect
// outputs: SynastryTranslations TSX render
// dependencies: components/synastry/synastry-tone, lib/api/synastry
// side_effects: none
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-SYNASTRY-TRANSLATIONS

// START_MODULE_MAP: M-SYNASTRY-TRANSLATIONS
// public_entrypoints:
//   - SynastryTranslations
// semantic_blocks: none
// owned_tests: none
// END_MODULE_MAP: M-SYNASTRY-TRANSLATIONS

"use client"

import type { SynastryTranslation } from "@/lib/api/synastry"
import { localizeTechSignature, normalizeSynastryTone } from "./synastry-tone"

type Props = {
  translations: SynastryTranslation[]
  onOpenAspect: (aspectId: string) => void
}

// START_BLOCK: SYNASTRY_TRANSLATIONS
export function SynastryTranslations({ translations, onOpenAspect }: Props) {
  if (!translations || translations.length === 0) return null

  return (
    <section className="space-y-3 mx-4" data-testid="synastry-translations">
      <div className="space-y-0.5">
        <span className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#795a86]">
          ЧЕЛОВЕЧЕСКИЙ ПЕРЕВОД
        </span>
        <h2 className="syn-serif text-[22px] font-semibold text-[#3e3347] dark:text-[#f1e9f4]">
          Что это делает с вами
        </h2>
        <p className="text-[13px] text-[#7d7284] dark:text-muted-foreground leading-relaxed">
          Астрологическая причина → узнаваемое поведение → конкретная сцена. Никакой простыни.
        </p>
      </div>

      <div className="space-y-3">
        {translations.map((item, idx) => {
          const tone = normalizeSynastryTone(item.tone)
          const aspectId = item.aspectId

          return (
            <div
              key={idx}
              className="rounded-[18px] border border-[#e8e0e8] bg-white dark:bg-[#2d2233] p-[14px] space-y-2.5 shadow-sm"
            >
              {/* Header row: tone dot + H3 + tech signature drilldown link */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className={`h-2.5 w-2.5 rounded-full flex-none ${
                      tone === "good"
                        ? "bg-[#43806d]"
                        : tone === "bad"
                        ? "bg-[#a64d59]"
                        : "bg-[#b07b36]"
                    }`}
                  />
                  <h3 className="font-sans text-[15px] font-bold text-[#3e3347] dark:text-[#f1e9f4] leading-snug">
                    {item.title}
                  </h3>
                </div>

                {item.tech && aspectId ? (
                  <button
                    type="button"
                    onClick={() => onOpenAspect(aspectId)}
                    className="text-[10px] font-bold text-[#7d7284] underline decoration-dotted hover:text-[#795a86] transition flex-none"
                  >
                    {localizeTechSignature(item.tech)} · что значит?
                  </button>
                ) : item.tech ? (
                  <span className="text-[10px] font-bold text-[#7d7284] flex-none">
                    {localizeTechSignature(item.tech)}
                  </span>
                ) : null}
              </div>

              {/* Main translation text */}
              {item.text && (
                <p className="text-[13px] leading-[1.46] text-[#3e3347] dark:text-foreground/90 m-0">
                  {item.text}
                </p>
              )}

              {/* Life Scene box */}
              {item.scene && (
                <div className="rounded-[12px] bg-[#f8f5f8] dark:bg-[#251b2b] px-[10px] py-[9px] text-[12px] leading-[1.42] text-[#65596a] dark:text-[#d4c8db] font-sans">
                  <strong>Сцена:</strong> {item.scene}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
// END_BLOCK: SYNASTRY_TRANSLATIONS
