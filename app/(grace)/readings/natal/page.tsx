'use client'

import { useEffect, useState } from "react"
import { NatalToc } from "@/components/readings/natal/natal-toc"
import { getNatalReport } from "@/lib/api/natal"
import type { NatalReport } from "@/lib/api/natal"

/**
 * /readings/natal — оглавление глубокого разбора натальной карты.
 *
 * Client-side render: данные приходят через API /api/natal/overview.
 */
export default function NatalReadingPage() {
  const [report, setReport] = useState<NatalReport | null>(null)

  useEffect(() => {
    getNatalReport().then(setReport).catch(() => setReport(null))
  }, [])

  if (!report) return null

  return <NatalToc report={report} />
}
