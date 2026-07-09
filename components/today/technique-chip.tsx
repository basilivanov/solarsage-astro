import React from "react"

const TECHNIQUE_LABELS: Record<string, string> = {
  transit_to_natal: "Транзит",
  transit_to_angle: "Транзит",
  transit_to_lot: "Транзит",
  transit_planet_in_house: "Транзит",
  annual_profection: "Профекция",
  monthly_profection: "Профекция",
  firdar_major: "Фирдар",
  firdar_minor: "Фирдар",
  solar_return: "Возвращение",
  lunar_return: "Возвращение",
  secondary_progression: "Прогрессия",
  solar_arc: "Solar Arc",
  eclipse_window: "Затмение",
}

interface TechniqueChipProps {
  technique: string
}

export function TechniqueChip({ technique }: TechniqueChipProps) {
  const label = TECHNIQUE_LABELS[technique] || technique
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
