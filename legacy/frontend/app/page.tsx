"use client"

import { useCallback, useEffect } from "react"
import { useRouter } from "next/navigation"

import { OnboardingFlow } from "@/components/onboarding/onboarding-flow"
import { TODAY } from "@/lib/today"
import { toDateParam } from "@/lib/date"
import { useOnboarded } from "@/hooks/use-onboarded"

/**
 * Корневой роут `/`.
 *
 * Отвечает только за одну вещь — за переход в приложение:
 * - если онбординг не пройден → показываем OnboardingFlow
 * - если пройден → редиректим на сегодняшний день (`/day/YYYY-MM-DD`)
 *
 * Сами вкладки (today / calendar / readings / profile) живут как
 * отдельные роуты в группе `(app)` и получают общий AppShell из её layout.
 */
export default function Page() {
  const router = useRouter()
  const { onboarded, setOnboarded } = useOnboarded()

  // Уже прошёл онбординг — уводим сразу на сегодняшний день
  useEffect(() => {
    if (onboarded === true) {
      router.replace(`/day/${toDateParam(TODAY)}`)
    }
  }, [onboarded, router])

  const completeOnboarding = useCallback(() => {
    setOnboarded(true)
    router.replace(`/day/${toDateParam(TODAY)}`)
  }, [router, setOnboarded])

  // Пока неизвестно состояние онбординга или уже редиректим — пустой фон (анти-мигание)
  if (onboarded === null || onboarded === true) {
    return <main className="h-dvh bg-background" />
  }

  return <OnboardingFlow onComplete={completeOnboarding} />
}
