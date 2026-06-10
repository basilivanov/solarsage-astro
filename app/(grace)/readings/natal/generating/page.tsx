"use client"

import { useCallback, useMemo, useState } from "react"
import { useRouter } from "next/navigation"

import { NatalGeneratingScreen } from "@/components/readings/natal-preview/natal-generating-screen"
import { IS_DEMO_MODE } from "@/lib/demo-mode"
import { DEMO_NATAL_PREVIEW } from "@/lib/demo-data"

/**
 * /readings/natal/generating
 *
 * Экран генерации натального отчёта.
 * В демо-режиме показывает анимацию и через ~23 секунды
 * перенаправляет на полный отчёт.
 *
 * В проде — поллит статус генерации с бэкенда
 * и редиректит на /readings/natal/{id} по готовности.
 */
export default function NatalGeneratingPage() {
  const router = useRouter()
  const [isLive] = useState(!IS_DEMO_MODE)

  const name = useMemo(() => {
    return DEMO_NATAL_PREVIEW.meta.name
  }, [])

  const priceKopecks = useMemo(() => {
    return DEMO_NATAL_PREVIEW.fullReportPriceKopecks
  }, [])

  const handleComplete = useCallback(() => {
    // В демо — переходим на демо-отчёт
    // В проде — GET /api/natal/report/{id}
    router.push("/readings/natal/demo")
  }, [router])

  return (
    <NatalGeneratingScreen
      name={name}
      priceKopecks={priceKopecks}
      onComplete={handleComplete}
      isLive={isLive}
    />
  )
}
