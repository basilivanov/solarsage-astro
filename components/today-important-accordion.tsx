
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_TODAY_IMPORTANT_ACCORDION
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI today-important-accordion — component
// owns:
//   - components/today-important-accordion.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { useState } from "react"
import type { TodayImportantEvent } from "@/packages/contracts"
import { Moon, AlertTriangle, RotateCcw, Zap, Star, Sparkles, ChevronDown } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"

type Props = {
  items: TodayImportantEvent[]
}

const KIND_ICONS: Record<string, LucideIcon> = {
  void_moon: Moon,
  new_moon: Moon,
  full_moon: Moon,
  solar_eclipse: AlertTriangle,
  lunar_eclipse: AlertTriangle,
  mercury_retrograde: RotateCcw,
  mercury_station: Zap,
  moon_quarter: Moon,
  sun_ingress: Sparkles,
  fast_planet_aspect: Star,
}

function toneColors(tone: string) {
  if (tone === "caution") {
    return {
      bg: "bg-red-500/10 text-red-500",
    }
  }
  if (tone === "supportive") {
    return {
      bg: "bg-emerald-500/10 text-emerald-500",
    }
  }
  return {
    bg: "bg-secondary/70 text-muted-foreground",
  }
}

export function TodayImportantAccordion({ items }: Props) {
  const [openIds, setOpenIds] = useState<Set<string>>(new Set())

  if (!items || items.length === 0) return null

  function toggle(id: string) {
    setOpenIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        // Keep only one open
        next.clear()
        next.add(id)
      }
      return next
    })
  }

  return (
    <section className="px-5" aria-label="Сегодня важно" data-testid="today-important-accordion">
      <div className="overflow-hidden rounded-2xl border border-border/70 bg-card">
        <div className="border-b border-border/60 px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <Star className="h-4 w-4 text-accent-foreground/70" strokeWidth={1.75} />
            <h3 className="font-sans text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Сегодня важно
            </h3>
          </div>
        </div>

        <div>
          {items.map((item, i) => {
            const Icon = KIND_ICONS[item.kind] || Star
            const colors = toneColors(item.tone)
            const isOpen = openIds.has(item.id)
            const isLast = i === items.length - 1

            return (
              <div key={item.id} className={!isLast ? "border-b border-border/50" : ""}>
                {/* Header row (always visible) */}
                <button
                  type="button"
                  onClick={() => toggle(item.id)}
                  className="flex w-full items-center gap-3 px-5 py-4 text-left transition-colors hover:bg-secondary/30"
                  aria-expanded={isOpen}
                  data-testid={`important-item-${item.id}`}
                >
                  <div className={`flex h-8 w-8 flex-none items-center justify-center rounded-full ${colors.bg}`}>
                    <Icon className="h-4 w-4" strokeWidth={1.75} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <span className="font-sans text-[13.5px] font-semibold text-foreground">
                      {item.title}
                    </span>
                    {item.localTimeLabel && (
                      <span className="text-[12px] font-medium text-muted-foreground/85 ml-1.5">
                        · {item.localTimeLabel}
                      </span>
                    )}
                  </div>
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 flex-none text-muted-foreground/50 transition-transform duration-200",
                      isOpen && "rotate-180"
                    )}
                    strokeWidth={1.75}
                  />
                </button>

                {/* Expanded description (fixes user-reported bug) */}
                {isOpen && (
                  <div className="px-5 pb-4 animate-in fade-in slide-in-from-top-1 duration-200">
                    <div className="rounded-xl bg-secondary/30 px-4 py-3.5">
                      <p className="font-sans text-[13px] leading-relaxed text-foreground/85">
                        {item.summary}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
