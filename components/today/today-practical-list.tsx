// ############################################################################
// AI_HEADER: MODULE_TODAY_TODAY_PRACTICAL_LIST
// ROLE: UI component — "Concretely today" practical list built from real
//       TodayPayload fields: topFlags, sphereScores, notes.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-TODAY-PRACTICAL-LIST
// purpose: Render a concise "Concretely today" list showing the most
//          actionable items derived from real API data: top signals, sphere
//          scores, and the daily note. All text comes from real contracts or
//          deterministic UI copy — no fabricated astrology.
// owns:
//   - components/today/today-practical-list.tsx
// inputs:
//   - topFlags: AdaptedTopFlag[] — day signals
//   - notes: TodayNote[] — daily notes
//   - sphereScores: SphereScore[] — area-of-life scores
// outputs:
//   - JSX section with data-testid="practical-list"
// side_effects: none
// invariants:
//   - Sphere keys are mapped via getSphereLabel (never shown raw)
//   - Items are derived from real API fields or deterministic UI labels
//   - Empty/fallback states show deterministic placeholder text
// failure_policy: renders nothing if all inputs are empty (no crash)
// END_MODULE_CONTRACT: M-TODAY-TODAY-PRACTICAL-LIST

"use client"

import { getIcon } from "@/lib/icons"
import type { AdaptedTopFlag, TodayNote, SphereScore } from "@/lib/contracts/today"
import { getSphereLabel } from "@/lib/display/sphere-labels"

type Props = {
  topFlags: AdaptedTopFlag[]
  notes: TodayNote[]
  sphereScores: SphereScore[]
}

type PracticalItem = {
  id: string
  iconName: string
  title: string
  description: string
}

const FALLBACK_ITEMS: PracticalItem[] = [
  {
    id: "fallback-tip",
    iconName: "compass",
    title: "Данные дня загружаются",
    description: "Персональные рекомендации появятся после полного расчёта.",
  },
]

function buildItems(topFlags: AdaptedTopFlag[], notes: TodayNote[], sphereScores: SphereScore[]): PracticalItem[] {
  const items: PracticalItem[] = []

  // Top signals → practical items
  for (const flag of topFlags) {
    items.push({
      id: `flag-${flag.title}`,
      iconName: flag.iconName,
      title: flag.title,
      description: flag.summary,
    })
  }

  // Top 3 sphere scores → practical items with human-readable labels
  const topSpheres = [...sphereScores]
    .sort((a, b) => a.rank - b.rank)
    .slice(0, 3)

  for (const sphere of topSpheres) {
    items.push({
      id: `sphere-${sphere.key}`,
      iconName: "trending-up",
      title: getSphereLabel(sphere.key),
      description: `Активность сферы: ${sphere.score}`,
    })
  }

  // Daily notes → practical items (exclude fallback "no data" notes)
  for (const note of notes) {
    if (note.id !== "no-data") {
      items.push({
        id: note.id,
        iconName: note.iconName,
        title: note.title,
        description: note.description,
      })
    }
  }

  return items.length > 0 ? items : FALLBACK_ITEMS
}

export function TodayPracticalList({ topFlags, notes, sphereScores }: Props) {
  const items = buildItems(topFlags, notes, sphereScores)

  return (
    <section className="px-5" aria-label="Конкретно сегодня" data-testid="practical-list">
      <h2 className="mb-3 font-serif text-[20px] leading-tight tracking-tight text-foreground">
        Конкретно сегодня
      </h2>

      <ul className="space-y-2">
        {items.map((item) => {
          const Icon = getIcon(item.iconName)
          return (
            <li key={item.id}>
              <div className="flex items-start gap-3.5 rounded-2xl border border-border/60 bg-card px-4 py-3.5">
                <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-accent text-accent-foreground">
                  <Icon className="h-[18px] w-[18px]" strokeWidth={1.6} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-[14px] font-medium leading-snug text-foreground">{item.title}</p>
                  <p className="mt-0.5 text-[13px] leading-snug text-muted-foreground">{item.description}</p>
                </div>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
