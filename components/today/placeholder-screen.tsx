
// ############################################################################
// AI_HEADER: MODULE_TODAY_PLACEHOLDER_SCREEN
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TODAY-CALENDAR
// #########################################// START_MODULE_CONTRACT
// purpose: Module: placeholder-screen.tsx
// owns:
//   - components/today/placeholder-screen.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import type { LucideIcon } from "lucide-react"

export function PlaceholderScreen({
  icon: Icon,
  title,
  subtitle,
}: {
  icon: LucideIcon
  title: string
  subtitle: string
}) {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center px-10 text-center">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-full border border-border/70 bg-card text-muted-foreground">
        <Icon className="h-6 w-6" strokeWidth={1.5} />
      </div>
      <h2 className="font-serif text-[26px] leading-tight tracking-tight text-foreground">
        {title}
      </h2>
      <p className="mt-2 max-w-[20ch] text-[13px] leading-relaxed text-muted-foreground">
        {subtitle}
      </p>
      <span className="mt-5 rounded-full border border-border/70 bg-card px-3 py-1 text-[10px] uppercase tracking-[0.14em] text-muted-foreground/80">
        скоро
      </span>
    </div>
  )
}
