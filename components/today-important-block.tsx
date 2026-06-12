
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_TODAY_IMPORTANT_BLOCK
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: today-important-block.tsx
// owns:
//   - components/today-important-block.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { AlertTriangle, Moon, Star, RotateCcw, Home, Zap, ArrowRight } from "lucide-react"
import type { LucideIcon } from "lucide-react"

type ImportantItem = {
  id: string
  type: string
  title: string
  subtitle: string
  severity: string
  planet?: string | null
  house?: number | null
}

type Props = {
  items: ImportantItem[]
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
}

const SEVERITY_COLORS: Record<string, string> = {
  info: "text-muted-foreground/70",
  soft_warning: "text-amber-600/80",
  warning: "text-orange-600/80",
  high_attention: "text-red-500/80",
}

function severityIconClass(severity: string): string {
  if (severity === "high_attention" || severity === "warning") return "bg-red-500/10 text-red-500"
  if (severity === "soft_warning") return "bg-amber-500/10 text-amber-500"
  return "bg-secondary/60 text-muted-foreground"
}

export function TodayImportantBlock({ items }: Props) {
  if (!items || items.length === 0) return null

  return (
    <section className="px-5" aria-label="Сегодня важно учесть">
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
            const isLast = i === items.length - 1
            return (
              <div
                key={item.id}
                className={!isLast ? "border-b border-border/50" : ""}
              >
                <div className="flex items-start gap-3 px-5 py-3">
                  <div className={`mt-0.5 flex h-7 w-7 flex-none items-center justify-center rounded-full ${severityIconClass(item.severity)}`}>
                    <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-sans text-[13.5px] font-medium leading-snug text-foreground">
                      {item.title}
                    </p>
                    <p className={`mt-0.5 font-sans text-[12px] leading-snug ${SEVERITY_COLORS[item.severity] || SEVERITY_COLORS.info}`}>
                      {item.subtitle}
                    </p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
