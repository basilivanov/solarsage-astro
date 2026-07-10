import React from "react"
import { getTechniqueLabel } from "@/lib/presentation/today-v2"

interface TechniqueChipProps {
  technique: string
}

export function TechniqueChip({ technique }: TechniqueChipProps) {
  const label = getTechniqueLabel(technique)
  return (
    <span
      data-testid="technique-chip"
      title={technique}
      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200"
    >
      {label}
    </span>
  )
}
