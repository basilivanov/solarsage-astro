/**
 * API-фасад для разбора натальной карты.
 *
 * Контракт фиксирован в `lib/contracts/natal.ts` (`schemaVersion: "natal/v1"`).
 */

import { type NatalReport, type ReportSection } from "@/lib/contracts/natal"

export type { NatalReport, ReportSection }

export async function getNatalReport(): Promise<NatalReport> {
  const res = await fetch("/api/natal/overview", {
    credentials: "include",
    headers: { "Accept": "application/json" },
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}`)
  }
  return res.json()
}

export async function getNatalSection(id: string) {
  const res = await fetch(`/api/natal/section/${encodeURIComponent(id)}`, {
    credentials: "include",
    headers: { "Accept": "application/json" },
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}`)
  }
  return res.json()
}

export const getNatalReportAsync = getNatalReport
export const getNatalSectionAsync = getNatalSection
