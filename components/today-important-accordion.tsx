"use client"

import type { TodayImportantEvent } from "@/packages/contracts"
import { Moon, AlertTriangle, RotateCcw, Zap, Star, Sparkles } from "lucide-react"
import type { LucideIcon } from "lucide-react"

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
  if (!items || items.length === 0) return null

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

        <div className="divide-y divide-border/50">
          {items.map((item) => {
            const Icon = KIND_ICONS[item.kind] || Star
            const colors = toneColors(item.tone)

            return (
              <div key={item.id} className="flex items-start gap-3 px-5 py-4" data-testid={`important-item-${item.id}`}>
                <div className={`flex h-8 w-8 flex-none items-center justify-center rounded-full ${colors.bg}`}>
                  <Icon className="h-4 w-4" strokeWidth={1.75} />
                </div>
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="font-sans text-[13.5px] font-semibold text-foreground">
                      {item.title}
                    </span>
                    {item.localTimeLabel && (
                      <span className="text-[12px] font-medium text-muted-foreground/85">
                        · {item.localTimeLabel}
                      </span>
                    )}
                  </div>
                  <p className="font-sans text-[12.5px] leading-relaxed text-muted-foreground">
                    {item.summary}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
