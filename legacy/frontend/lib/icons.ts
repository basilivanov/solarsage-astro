import {
  Briefcase,
  Compass,
  Grid3x3,
  Hourglass,
  Layers,
  Leaf,
  ListChecks,
  Moon,
  Orbit,
  Target,
  Telescope,
  TrendingUp,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"

/**
 * Символические имена иконок, которые могут прийти из payload/API.
 *
 * В сам payload кладём строку — она сериализуема, её можно хранить в JSON,
 * отдавать из бэкенда и из CMS. А на слое UI мы резолвим её до компонента
 * Lucide через getIcon(). Если имя незнакомое — вернём дефолт, чтобы
 * приложение не падало из-за опечатки в данных.
 *
 * Набор специально «не погодный»: никаких sun / cloud / wind / snowflake.
 * Мы не раздаём прогноз — мы раздаём астрологический контекст, поэтому
 * каждая иконка привязана к смыслу, а не к природному явлению:
 *
 *   moon        — лунные аспекты (Луна без курса, фазы, транзиты Луны)
 *   orbit       — планетарное движение (ретроградность, транзиты)
 *   briefcase   — карьера, 10 дом, рабочие темы
 *   compass     — главная тема дня, направление
 *   hourglass   — быстрый слой дня, окна по часам
 *   target      — личная чувствительная точка, триггер
 *   layers      — фон периода, длинные циклы
 *   trending-up — что усиливает день
 *   leaf        — что смягчает, поддерживающий аспект
 *   grid        — сферы жизни, распределение по домам
 *   telescope   — астрологический смысл, «взгляд в небо»
 *   list-checks — практические выводы, список действий
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
}

export function getIcon(name: string): LucideIcon {
  return map[name as IconName] ?? Compass
}
