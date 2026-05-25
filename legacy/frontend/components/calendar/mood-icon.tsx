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
