
// ############################################################################
// AI_HEADER: MODULE_CALENDAR_MOOD_ICON
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TODAY-CALENDAR
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: mood-icon.tsx
// owns:
//   - components/calendar/mood-icon.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-COMPONENTS-CALENDAR-MOOD-ICON
// wave: W-2.7
// purpose: MoodIcon component (migrated from legacy)

import { Flame, Minus, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"
import type { DayStatus } from "@/lib/calendar"

/**
 * Иконка «тона дня». Не погодные: Flame / Minus / Sparkles —
 * это градация «интенсивности» (напряжённый / ровный / поддерживающий),
 * а не реальная атмосфера. Используется в календаре и недельной полосе.
 */
type Props = {
  status: DayStatus
  className?: string
  strokeWidth?: number
}

export function MoodIcon({ status, className, strokeWidth = 1.75 }: Props) {
  const Icon =
    status === "tense" ? Flame : status === "supportive" ? Sparkles : Minus
  return <Icon aria-hidden className={cn(className)} strokeWidth={strokeWidth} />
}
