import type { ReactNode } from "react"

import { AppShell } from "@/components/app-shell"

/**
 * Layout для всех вкладок приложения.
 *
 * Оборачивает /day, /calendar, /readings, /profile в общий AppShell,
 * в котором живут рамка Telegram Mini App, safe-area и нижний TabBar.
 */
export default function AppGroupLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>
}
