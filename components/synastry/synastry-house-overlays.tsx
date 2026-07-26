// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_HOUSE_OVERLAYS
// ROLE: House overlays section component for synastry report screen
// DEPENDENCIES: react, lucide-react
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-HOUSE-OVERLAYS
// purpose: Render house overlays section with lavender mini-cards, house system badge, or approximate precision notice card.
// owns:
//   - components/synastry/synastry-house-overlays.tsx
// inputs: houseOverlays, houseSystem, isApproximate
// outputs: SynastryHouseOverlays TSX render
// dependencies: none
// side_effects: none
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-SYNASTRY-HOUSE-OVERLAYS

// START_MODULE_MAP: M-SYNASTRY-HOUSE-OVERLAYS
// public_entrypoints:
//   - SynastryHouseOverlays
// semantic_blocks: none
// owned_tests: none
// END_MODULE_MAP: M-SYNASTRY-HOUSE-OVERLAYS

"use client"

import { Info } from "lucide-react"

type Props = {
  houseOverlays: Array<{ tech?: string; text?: string }>
  houseSystem?: string
  isApproximate?: boolean
}

// START_BLOCK: SYNASTRY_HOUSE_OVERLAYS
export function SynastryHouseOverlays({ houseOverlays, houseSystem, isApproximate = false }: Props) {
  const systemLabel =
    houseSystem?.toLowerCase() === "whole_sign"
      ? "Дома: равнодомная система"
      : "Дома: Placidus"

  return (
    <section className="space-y-3 mx-4" data-testid="synastry-overlays">
      <div className="space-y-0.5">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#795a86]">
            НАЛОЖЕНИЕ ДОМОВ
          </span>
          {!isApproximate && (
            <span className="text-[10px] font-bold text-[#7d7284] uppercase tracking-wider">
              {systemLabel}
            </span>
          )}
        </div>
        <h2 className="syn-serif text-[22px] font-semibold text-[#3e3347] dark:text-[#f1e9f4]">
          Что у кого включается
        </h2>
        <p className="text-[13px] text-[#7d7284] dark:text-muted-foreground leading-relaxed">
          Не просто «планета в доме», а какую часть жизни партнёр реально задевает.
        </p>
      </div>

      {isApproximate ? (
        <div
          data-testid="synastry-overlays-approx-notice"
          className="rounded-[17px] bg-[#f7f2f7] dark:bg-[#2d2233] p-[12px] text-[12px] leading-[1.42] text-[#3e3347] dark:text-[#f1e9f4] space-y-1"
        >
          <div className="font-bold flex items-center gap-1.5 text-[#795a86]">
            <Info className="h-4 w-4 flex-none" />
            Дома партнёра не рассчитаны
          </div>
          <p className="m-0">
            Без точного времени рождения нельзя честно определить ASC и домовые наложения. Планетарные аспекты в отчёте сохранены.
          </p>
        </div>
      ) : houseOverlays.length > 0 ? (
        <div className="grid grid-cols-1 gap-2.5">
          {houseOverlays.map((item, idx) => (
            <div
              key={idx}
              className="rounded-[17px] bg-[#f7f2f7] dark:bg-[#2d2233] p-[12px] space-y-1 border-0"
            >
              {item.tech && (
                <div className="font-sans text-[11px] font-[850] text-[#795a86] dark:text-[#c8a9d6] uppercase tracking-wide">
                  {item.tech}
                </div>
              )}
              {item.text && (
                <p className="font-sans text-[12px] leading-[1.42] text-[#3e3347] dark:text-[#f1e9f4] m-0">
                  {item.text}
                </p>
              )}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  )
}
// END_BLOCK: SYNASTRY_HOUSE_OVERLAYS
