// AI_HEADER
// module: M-LIB-ICONS
// wave: W-2.7
// purpose: Icon mapping utilities (migrated from legacy)

import {
  Briefcase,
  Building2,
  Check,
  Compass,
  Grid3x3,
  Hourglass,
  Layers,
  Leaf,
  ListChecks,
  Moon,
  Orbit,
  Sparkles,
  Target,
  Telescope,
  TrendingUp,
  Zap,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"

/**
 * Символические имена иконок, которые могут прийти из payload/API.
 *
 * В сам payload кладём строку — она сериализуема, её можно хранить в JSON,
 * отдавать из бэкенда и из CMS. А на слое UI мы резолвим её до компонента
 * Lucide через getIcon(). Если имя незнакомое — вернём дефолт, чтобы
 * приложение не падало из-за опечатки в данных.
 */
export type IconName =
  | "moon"
  | "orbit"
  | "briefcase"
  | "compass"
  | "hourglass"
  | "target"
  | "layers"
  | "trending-up"
  | "leaf"
  | "grid"
  | "telescope"
  | "list-checks"
  | "zap"
  | "sparkle"
  | "check"
  | "building"

const map: Record<IconName, LucideIcon> = {
  moon: Moon,
  orbit: Orbit,
  briefcase: Briefcase,
  compass: Compass,
  hourglass: Hourglass,
  target: Target,
  layers: Layers,
  "trending-up": TrendingUp,
  leaf: Leaf,
  grid: Grid3x3,
  telescope: Telescope,
  "list-checks": ListChecks,
  zap: Zap,
  sparkle: Sparkles,
  check: Check,
  building: Building2,
}

export function getIcon(name: string): LucideIcon {
  return map[name as IconName] ?? Compass
}
