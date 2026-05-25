import type { LucideIcon } from "lucide-react"

export type AvailableReading = {
  key: "natal" | "horary"
  title: string
  description: string
  icon: LucideIcon
  /** Короткое описание того, что внутри — для экрана разбора в будущем */
  teaser?: string
}

export type ComingReading = {
  key: "month" | "year" | "synastry" | "themes" | "history"
  title: string
  description: string
  icon: LucideIcon
}

export type ReadingsCatalog = {
  available: AvailableReading[]
  coming: ComingReading[]
}
