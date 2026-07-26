// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_HOUSE_OVERLAYS
// ROLE: House overlays section component for synastry report screen
// DEPENDENCIES: react, lucide-react
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-HOUSE-OVERLAYS
// purpose: Render house overlays section with lavender mini-cards or approximate precision notice card.
// owns:
//   - components/synastry/synastry-house-overlays.tsx
// inputs: houseOverlays, isApproximate
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
  isApproximate?: boolean
}

// START_BLOCK: SYNASTRY_HOUSE_OVERLAYS
export function SynastryHouseOverlays({ houseOverlays, isApproximate = false }: Props) {
  return (
    <section className="space-y-4" data-testid="synastry-overlays">
      <div className="space-y-1">
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          НАЛОЖЕНИЕ ДОМОВ
        </span>
        <h2 className="font-serif text-[22px] font-semibold text-foreground">
          Что у кого включается
        </h2>
        <p className="text-[13px] text-muted-foreground leading-relaxed">
          Не просто «планета в доме», а какую часть жизни партнёр реально задевает.
        </p>
      </div>

      {isApproximate ? (
        <div
          data-testid="synastry-overlays-approx-notice"
          className="rounded-[17px] bg-[#f1e9f4] dark:bg-[#2d2233] p-4 text-[13px] leading-relaxed text-[#3e3347] dark:text-[#f1e9f4] space-y-1"
        >
          <div className="font-semibold flex items-center gap-1.5 text-primary">
            <Info className="h-4 w-4 flex-none" />
            Дома партнёра не рассчитаны
          </div>
          <p className="opacity-90">
            Без точного времени рождения нельзя честно определить ASC и домовые наложения. Планетарные аспекты в отчёте сохранены.
          </p>
        </div>
      ) : houseOverlays.length > 0 ? (
        <div className="grid grid-cols-1 gap-3">
          {houseOverlays.map((item, idx) => (
            <div
              key={idx}
              className="rounded-[17px] bg-[#f1e9f4]/70 dark:bg-[#2d2233]/70 p-4 space-y-1"
            >
              {item.tech && (
                <div className="text-[11px] font-semibold text-primary uppercase tracking-wider">
                  {item.tech}
                </div>
              )}
              <div className="text-[13px] text-foreground leading-relaxed">
                {item.text}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-[17px] bg-card p-4 text-[13px] text-muted-foreground border border-border/60">
          Наложения домов рассчитываются.
        </div>
      )}
    </section>
  )
}
// END_BLOCK: SYNASTRY_HOUSE_OVERLAYS
