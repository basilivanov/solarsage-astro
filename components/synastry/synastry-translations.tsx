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
import { normalizeSynastryTone } from "./synastry-tone"

type Props = {
  translations: SynastryTranslation[]
  onOpenAspect: (aspectId: string) => void
}

// START_BLOCK: SYNASTRY_TRANSLATIONS
export function SynastryTranslations({ translations, onOpenAspect }: Props) {
  if (!translations || translations.length === 0) return null

  return (
    <section className="space-y-4" data-testid="synastry-translations">
      <div className="space-y-1">
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          ЧЕЛОВЕЧЕСКИЙ ПЕРЕВОД
        </span>
        <h2 className="font-serif text-[22px] font-semibold text-foreground">
          Что это делает с вами
        </h2>
        <p className="text-[13px] text-muted-foreground leading-relaxed">
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
              className="rounded-[22px] border border-border/70 bg-card p-5 space-y-3 shadow-sm"
            >
              {/* Header row: tone dot + H3 + tech signature drilldown */}
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span
                    className={`h-2.5 w-2.5 rounded-full flex-none ${
                      tone === "good"
                        ? "bg-[var(--syn-good)]"
                        : tone === "bad"
                        ? "bg-[var(--syn-bad)]"
                        : "bg-[var(--syn-mid)]"
                    }`}
                  />
                  <h3 className="font-sans text-[15px] font-bold text-foreground leading-snug">
                    {item.title}
                  </h3>
                </div>

                {item.tech && (
                  <div className="flex items-center gap-1.5 flex-none text-[11.5px] text-muted-foreground">
                    <span className="border-b border-dotted border-muted-foreground/50">{item.tech}</span>
                    {aspectId && (
                      <button
                        type="button"
                        onClick={() => onOpenAspect(aspectId)}
                        className="text-primary font-medium hover:underline focus:outline-none"
                      >
                        · что значит?
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Main text */}
              {item.text && (
                <p className="text-[14px] leading-relaxed text-foreground/85">
                  {item.text}
                </p>
              )}

              {/* Scene in soft separate box */}
              {item.scene && (
                <div className="rounded-[14px] bg-[#f1e9f4]/60 dark:bg-[#2d2233]/60 px-3.5 py-2.5 text-[12.5px] leading-relaxed text-muted-foreground">
                  «{item.scene}»
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
