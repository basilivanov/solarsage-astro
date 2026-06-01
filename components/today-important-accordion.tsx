"use client"

import { useState } from "react"
import { ChevronDown, Moon, AlertTriangle, Home, RotateCcw, Zap, ArrowRight, Star } from "lucide-react"
import type { LucideIcon } from "lucide-react"

export type ImportantTodayItem = {
  id: string
  type: string
  title: string
  subtitle: string
  severity: string
  icon_name?: string | null
  planet?: string | null
  sign?: string | null
  house?: number | null
  priority: number
  details?: {
    meaning?: string | null
    why_important?: string | null
    personal_context?: string | null
  } | null
  source: string
}

type Props = {
  items: ImportantTodayItem[]
}

const TYPE_ICONS: Record<string, LucideIcon> = {
  moon_void: Moon,
  retrograde: RotateCcw,
  new_moon: Moon,
  full_moon: Moon,
  eclipse: AlertTriangle,
  active_house: Home,
  station: Zap,
  ingress: ArrowRight,
  daily_note: Star,
}

function severityBg(severity: string): string {
  if (severity === "high_attention") return "bg-red-500/10 text-red-500"
  if (severity === "warning") return "bg-orange-500/10 text-orange-500"
  if (severity === "soft_warning") return "bg-amber-500/10 text-amber-500"
  return "bg-secondary/70 text-muted-foreground"
}

function subtitleColor(severity: string): string {
  if (severity === "high_attention" || severity === "warning") return "text-red-600/70"
  if (severity === "soft_warning") return "text-amber-600/70"
  return "text-muted-foreground/70"
}

export function TodayImportantAccordion({ items }: Props) {
  if (!items || items.length === 0) return null

  const [openIds, setOpenIds] = useState<Set<string>>(new Set(items.length > 0 ? [items[0].id] : []))

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
    <section className="px-5" aria-label="Сегодня важно учесть" data-testid="today-important-accordion">
      <div className="overflow-hidden rounded-2xl border border-border/70 bg-card">
        <div className="border-b border-border/60 px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <Star className="h-4 w-4 text-accent-foreground/70" strokeWidth={1.75} />
            <h3 className="font-sans text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Сегодня важно учесть
            </h3>
          </div>
        </div>

        <div>
          {items.map((item, i) => {
            const Icon = TYPE_ICONS[item.type] || Star
            const isOpen = openIds.has(item.id)
            const isLast = i === items.length - 1

            return (
              <div key={item.id} className={!isLast ? "border-b border-border/50" : ""}>
                {/* Header row (always visible) */}
                <button
                  type="button"
                  onClick={() => toggle(item.id)}
                  className="flex w-full items-start gap-3 px-5 py-3 text-left transition-colors hover:bg-secondary/30"
                  aria-expanded={isOpen}
                  data-testid={`important-item-${item.id}`}
                >
                  <div className={`mt-0.5 flex h-7 w-7 flex-none items-center justify-center rounded-full ${severityBg(item.severity)}`}>
                    <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-sans text-[13.5px] font-medium leading-snug text-foreground">
                      {item.title}
                    </p>
                    <p className={`mt-0.5 font-sans text-[12px] leading-snug ${subtitleColor(item.severity)}`}>
                      {item.subtitle}
                    </p>
                  </div>
                  <ChevronDown
                    className={`mt-1 h-4 w-4 flex-none text-muted-foreground/50 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
                    strokeWidth={1.5}
                  />
                </button>

                {/* Expanded details */}
                {isOpen && item.details && (
                  <div className="px-5 pb-4 animate-in fade-in slide-in-from-top-1 duration-200">
                    <div className="space-y-3 rounded-xl bg-secondary/30 px-4 py-3.5">
                      {item.details.meaning && (
                        <div>
                          <p className="font-sans text-[10.5px] font-semibold uppercase tracking-[0.12em] text-muted-foreground/70 mb-1">
                            Что это значит
                          </p>
                          <p className="font-sans text-[13px] leading-relaxed text-foreground/85">
                            {item.details.meaning}
                          </p>
                        </div>
                      )}
                      {item.details.why_important && (
                        <div>
                          <p className="font-sans text-[10.5px] font-semibold uppercase tracking-[0.12em] text-muted-foreground/70 mb-1">
                            Почему это важно
                          </p>
                          <p className="font-sans text-[13px] leading-relaxed text-foreground/85">
                            {item.details.why_important}
                          </p>
                        </div>
                      )}
                      {item.details.personal_context && (
                        <div>
                          <p className="font-sans text-[10.5px] font-semibold uppercase tracking-[0.12em] text-muted-foreground/70 mb-1">
                            Как это у меня
                          </p>
                          <p className="font-sans text-[13px] leading-relaxed text-foreground/85">
                            {item.details.personal_context}
                          </p>
                        </div>
                      )}
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
