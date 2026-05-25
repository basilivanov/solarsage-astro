"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"

import { TabBar } from "@/components/today/tab-bar"
import { useOnboarded } from "@/hooks/use-onboarded"

/**
 * Общий контейнер приложения:
 * - ограничивает ширину (max-w-md) и центрирует
 * - содержит TabBar в футере
 * - проверяет флаг онбординга и редиректит на `/`, если он не пройден
 *
 * ВАЖНО про скролл:
 *   - внешний <main> фиксирует высоту (h-dvh) и гасит свой overflow,
 *     чтобы TabBar стоял на месте и не скроллился;
 *   - внутренний контейнер — flex-col на всю высоту (h-full), а
 *     overflow-y-auto висит ровно на одном элементе — области контента.
 *   Это единственный скролл-контейнер в приложении. Никакого nested scroll.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { onboarded } = useOnboarded()

  useEffect(() => {
    if (onboarded === false) router.replace("/")
  }, [onboarded, router])

  // Пока не знаем флаг — ничего не показываем (анти-мигание)
  if (onboarded !== true) {
    return <main className="h-dvh bg-background" />
  }

  return (
    <main className="h-dvh overflow-hidden bg-background">
      <div className="mx-auto flex h-full max-w-md flex-col border-x border-border/50 bg-background">
        <div className="flex-1 overflow-y-auto overscroll-contain">
          {children}
        </div>
        <TabBar />
      </div>
    </main>
  )
}
