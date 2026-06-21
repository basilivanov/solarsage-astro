// ############################################################################
// AI_HEADER: tab-bar — Bottom navigation bar for SolarSage Today
// ROLE: Renders a sticky bottom navigation bar with 5 icon+label tabs (today,
//   calendar, readings, chat, profile). Consumed by the Today layout to provide
//   primary navigation. Highlights active tab via aria-current based on pathname.
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Provides responsive bottom tab navigation with active-state tracking.
//   The Today layout renders this component once at the page shell level.
// inputs: None (reads usePathname from next/navigation internally).
// returns: TSX <nav> element with 5 <Link> tabs, each with title, data-testid, aria-current.
// side_effects: None.
// emitted_logs: tab_bar_render.
// error_behavior: Falls back pathname to "/" if usePathname returns null.
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - function: TabBar
//   - type: Tab
//   - type: TabKey
// END_MODULE_MAP

"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Sun, CalendarDays, BookOpen, User, MessageCircle } from "lucide-react"
import type { LucideIcon } from "lucide-react"

import { TODAY } from "@/lib/today"
import { toDateParam } from "@/lib/date"
import { logger } from "@/lib/log"

// START_BLOCK_TYPES
// START_FUNCTION_CONTRACT
// name: TabKey
// purpose: Union of valid tab identifiers matching route segments.
// inputs: None (type definition).
// returns: "today" | "calendar" | "readings" | "chat" | "profile".
// side_effects: None.
// END_FUNCTION_CONTRACT

export type TabKey = "today" | "calendar" | "readings" | "chat" | "profile"

type Tab = {
  key: TabKey
  icon: LucideIcon
  label: string
  href: string
  match: (p: string) => boolean
}
// END_BLOCK_TYPES

// START_BLOCK_TAB_DATA
const tabs: Tab[] = [
  {
    key: "today",
    icon: Sun,
    label: "Сегодня",
    href: `/day/${toDateParam(TODAY)}`,
    match: (p) => p === "/" || p.startsWith("/day"),
  },
  {
    key: "calendar",
    icon: CalendarDays,
    label: "Календарь",
    href: "/calendar",
    match: (p) => p.startsWith("/calendar"),
  },
  {
    key: "readings",
    icon: BookOpen,
    label: "Разборы",
    href: "/readings",
    match: (p) => p.startsWith("/readings"),
  },
  {
    key: "chat",
    icon: MessageCircle,
    label: "Спросить",
    href: "/chat",
    match: (p) => p.startsWith("/chat"),
  },
  {
    key: "profile",
    icon: User,
    label: "Профиль",
    href: "/profile",
    match: (p) => p.startsWith("/profile"),
  },
]
// END_BLOCK_TAB_DATA

// START_BLOCK_COMPONENT
// START_FUNCTION_CONTRACT
// name: TabBar
// purpose: Renders the bottom navigation bar. Reads the current pathname and
//   marks the matching tab with aria-current="page". Called by the Today layout.
// inputs: None (component with no props).
// returns: JSX nav element containing a grid of 5 tab links.
// side_effects: None.
// emitted_logs: tab_bar_render.
// error_behavior: Falls back to "/" when usePathname returns null.
// END_FUNCTION_CONTRACT
export function TabBar() {
  const pathname = usePathname() ?? "/"
  logger.debug("tab_bar_render", { extra: { pathname } })

  return (
    <nav
      data-testid="today-tab-bar"
      aria-label="Основная навигация"
      className="sticky bottom-0 border-t border-border/70 bg-background/85 backdrop-blur-md"
      style={{ paddingBottom: "max(env(safe-area-inset-bottom), 0.5rem)" }}
    >
      <ul className="mx-auto grid max-w-md grid-cols-5 px-2 pt-2">
        {tabs.map((t) => {
          const Icon = t.icon
          const isActive = t.match(pathname)
          return (
            <li key={t.key}>
              <Link
                href={t.href}
                data-testid={`today-tab-${t.key}`}
                title={t.label}
                aria-label={isActive ? `${t.label}, текущий раздел` : t.label}
                aria-current={isActive ? "page" : undefined}
                className={`relative flex w-full flex-col items-center gap-1 rounded-xl px-1 py-2 text-[10.5px] transition ${
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground active:text-foreground hover:text-foreground/70"
                }`}
              >
                {isActive && (
                  <span
                    aria-hidden
                    className="absolute -top-0.5 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-primary"
                    style={{ boxShadow: "0 0 6px oklch(0.48 0.06 305 / 0.5)" }}
                  />
                )}
                <Icon
                  className="h-[22px] w-[22px] text-current transition-transform"
                  strokeWidth={isActive ? 1.8 : 1.6}
                  style={{ transform: isActive ? "scale(1.05)" : "scale(1)" }}
                />
                <span className={`truncate ${isActive ? "font-medium" : ""}`}>
                  {t.label}
                </span>
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
// END_BLOCK_COMPONENT
