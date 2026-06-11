"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Sun, CalendarDays, BookOpen, User, MessageCircle } from "lucide-react"
import type { LucideIcon } from "lucide-react"

import { TODAY } from "@/lib/today"
import { toDateParam } from "@/lib/date"

export type TabKey = "today" | "calendar" | "readings" | "chat" | "profile"

type Tab = {
  key: TabKey
  icon: LucideIcon
  label: string
  href: string
  /** Префиксы путей, при которых эта вкладка считается активной. */
  match: (_pathname: string) => boolean
}

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

export function TabBar() {
  const pathname = usePathname() ?? "/"
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
                aria-current={isActive ? "page" : undefined}
                className={`flex w-full flex-col items-center gap-1 rounded-xl px-1 py-2 text-[10.5px] transition ${
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground active:text-foreground"
                }`}
              >
                <Icon className="h-[22px] w-[22px] text-current" strokeWidth={1.6} />
                <span
                  className={`truncate ${isActive ? "font-medium" : ""}`}
                >
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

