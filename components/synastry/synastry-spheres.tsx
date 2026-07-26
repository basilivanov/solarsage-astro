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
  // First sphere is open by default (§11.4)
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
    <section className="space-y-4" data-testid="synastry-spheres">
      <div className="space-y-1">
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          ПО ЖИЗНИ
        </span>
        <h2 className="font-serif text-[22px] font-semibold text-foreground">
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
              className="rounded-[20px] border border-border/70 bg-card overflow-hidden transition shadow-sm"
            >
              <button
                type="button"
                aria-expanded={isOpen}
                aria-controls={`synastry-sphere-content-${sphere.id}`}
                onClick={() => toggleSphere(sphere.id)}
                className="w-full flex items-center justify-between p-4 text-left focus:outline-none"
              >
                <div className="flex items-center gap-2.5">
                  <span
                    className={`h-2.5 w-2.5 rounded-full flex-none ${
                      tone === "good"
                        ? "bg-[var(--syn-good)]"
                        : tone === "bad"
                        ? "bg-[var(--syn-bad)]"
                        : "bg-[var(--syn-mid)]"
                    }`}
                  />
                  <span className="font-serif text-[18px] font-medium text-foreground">
                    {sphere.title}
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <span className="font-serif text-[24px] font-normal text-foreground">
                    {sphere.score}
                  </span>
                  {isOpen ? (
                    <ChevronUp className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
              </button>

              {isOpen && sphere.description && (
                <div
                  id={`synastry-sphere-content-${sphere.id}`}
                  className="px-4 pb-4 pt-1 text-[13.5px] leading-relaxed text-muted-foreground border-t border-border/30"
                >
                  {sphere.description}
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
