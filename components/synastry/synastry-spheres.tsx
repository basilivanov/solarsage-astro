// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_SPHERES
// ROLE: Life spheres breakdown accordion section for synastry report screen
// DEPENDENCIES: react, lucide-react, components/synastry/synastry-tone, lib/api/synastry
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-SPHERES
// purpose: Render life spheres breakdown accordion with large serif scores, tone dots, and initial open first sphere state.
// owns:
//   - components/synastry/synastry-spheres.tsx
// inputs: spheres
// outputs: SynastrySpheres TSX render
// dependencies: components/synastry/synastry-tone, lib/api/synastry
// side_effects: none
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-SYNASTRY-SPHERES

// START_MODULE_MAP: M-SYNASTRY-SPHERES
// public_entrypoints:
//   - SynastrySpheres
// semantic_blocks: none
// owned_tests: none
// END_MODULE_MAP: M-SYNASTRY-SPHERES

"use client"

import { useState } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"
import type { SynastrySphereItem } from "@/lib/api/synastry"
import { normalizeSynastryTone } from "./synastry-tone"

type Props = {
  spheres: SynastrySphereItem[]
}

// START_BLOCK: SYNASTRY_SPHERES
export function SynastrySpheres({ spheres }: Props) {
  const [openMap, setOpenMap] = useState<Record<string, boolean>>(() => {
    if (spheres && spheres.length > 0) {
      return { [spheres[0].id]: true }
    }
    return {}
  })

  if (!spheres || spheres.length === 0) return null

  function toggleSphere(id: string) {
    setOpenMap((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  return (
    <section className="space-y-3 mx-4" data-testid="synastry-spheres">
      <div className="space-y-0.5">
        <span className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#795a86]">
          ПО ЖИЗНИ
        </span>
        <h2 className="syn-serif text-[22px] font-semibold text-[#3e3347] dark:text-[#f1e9f4]">
          Где легко, где придётся работать
        </h2>
      </div>

      <div className="space-y-2.5">
        {spheres.map((sphere) => {
          const isOpen = !!openMap[sphere.id]
          const tone = normalizeSynastryTone(
            sphere.score >= 75 ? "good" : sphere.score < 45 ? "bad" : "mid"
          )

          return (
            <div
              key={sphere.id}
              className="rounded-[18px] border border-[#e8e0e8] bg-white dark:bg-[#2d2233] overflow-hidden transition shadow-sm"
            >
              <button
                type="button"
                aria-expanded={isOpen}
                aria-controls={`synastry-sphere-content-${sphere.id}`}
                onClick={() => toggleSphere(sphere.id)}
                className="flex w-full items-center justify-between p-[14px] text-left transition hover:bg-muted/30"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span
                    className={`h-2.5 w-2.5 rounded-full flex-none ${
                      tone === "good"
                        ? "bg-[#43806d]"
                        : tone === "bad"
                        ? "bg-[#a64d59]"
                        : "bg-[#b07b36]"
                    }`}
                  />
                  <span className="font-sans text-[14px] font-[820] text-[#3e3347] dark:text-[#f1e9f4] truncate">
                    {sphere.title}
                  </span>
                </div>

                <div className="flex items-center gap-3 flex-none">
                  <span className="syn-serif text-[22px] font-normal leading-none text-[#3e3347] dark:text-[#f1e9f4]">
                    {sphere.score}
                  </span>
                  {isOpen ? (
                    <ChevronUp className="h-4 w-4 text-[#7d7284]" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-[#7d7284]" />
                  )}
                </div>
              </button>

              {isOpen && (
                <div
                  id={`synastry-sphere-content-${sphere.id}`}
                  className="px-[14px] pb-[14px] pt-1 text-[13px] leading-[1.48] text-[#5e5262] dark:text-muted-foreground border-t border-[#e8e0e8]/50"
                >
                  <p className="m-0">{sphere.description}</p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
// END_BLOCK: SYNASTRY_SPHERES
