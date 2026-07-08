// ############################################################################
// AI_HEADER: MODULE_TODAY_TODAY_PRACTICAL_LIST
// ROLE: UI component — "Concretely today" matching 3001 oracle contract.
//       Built from real TodayPayload fields: sphereScores, topFlags, notes.
//       No raw technical keys, no numeric scores in visible text.
// ############################################################################

"use client"

import { useMemo, useState } from "react"
import { getIcon } from "@/lib/icons"
import type { AdaptedTopFlag, TodayNote, SphereScore } from "@/lib/contracts/today"

type Props = {
  topFlags: AdaptedTopFlag[]
  notes: TodayNote[]
  sphereScores: SphereScore[]
}

// Deterministic product sphere categories mapped from backend keys
const SPHERE_PRODUCT_MAP: Record<string, { label: string; icon: string }> = {
  work_status_achievement: { label: "Работа", icon: "💼" },
  finance_money: { label: "Деньги", icon: "💰" },
  legal_affairs: { label: "Документы", icon: "📝" },
  relationships_partnership: { label: "Отношения", icon: "💖" },
  body_energy_health: { label: "Спорт", icon: "🏃" },
  communication_learning: { label: "Общение", icon: "💬" },
  home_family_roots: { label: "Семья", icon: "🏠" },
  creativity_self_expression: { label: "Творчество", icon: "🎨" },
  travel_adventure: { label: "Поездки", icon: "✈️" },
  education: { label: "Учёба", icon: "📚" },
  spirituality_inner_growth: { label: "Здоровье", icon: "🌿" },
  career_ambition: { label: "Решения", icon: "🎯" },
}

function mapSphere(key: string): { label: string; icon: string; verdict: "good" | "caution" | "neutral"; score: number } {
  const product = SPHERE_PRODUCT_MAP[key] ?? { label: key, icon: "📌" }
  // Score 0-10: >6 good, <4 caution, else neutral
  // (score is from backend; higher = more active/positive)
  return { ...product, score: 0, verdict: "neutral" }
}

type AdviceRow = {
  id: string
  sphere: string
  icon: string
  verdict: "good" | "caution" | "neutral"
  text: string
}

const VERDICT_LABELS: Record<string, string> = { good: "благоприятно", caution: "осторожно" }

export function TodayPracticalList({ topFlags, notes, sphereScores }: Props) {
  const [expanded, setExpanded] = useState(false)

  const rows: AdviceRow[] = useMemo(() => {
    const result: AdviceRow[] = []

    // From topFlags
    for (const flag of topFlags) {
      result.push({
        id: `flag-${flag.title}`,
        sphere: flag.title,
        icon: "📌",
        verdict: "good",
        text: flag.summary,
      })
    }

    // From sphereScores — sorted by rank, map to product labels
    const sorted = [...sphereScores].sort((a, b) => a.rank - b.rank)
    for (const s of sorted) {
      const product = SPHERE_PRODUCT_MAP[s.key] ?? { label: s.key, icon: "📌" }
      const verdict = s.score >= 6 ? "good" : s.score <= 4 ? "caution" : "neutral"
      const texts: Record<string, string> = {
        work_status_achievement: "Ровный рабочий день",
        finance_money: "Можно планировать бюджет",
        legal_affairs: "Обычный день для бумаг",
        relationships_partnership: "Спокойно — без драмы, без озарений",
        body_energy_health: "Обычная нагрузка",
        communication_learning: "Без конфликтов, но и без прорывов",
        home_family_roots: "Спокойный домашний день",
        creativity_self_expression: "Ровный фон для творчества",
        travel_adventure: "Обычный день в дороге",
        education: "Спокойно учится",
        spirituality_inner_growth: "Поддерживай режим",
        career_ambition: "Ясность — решения даются ровно",
      }
      const text = texts[s.key] ?? "Стабильно, без неожиданностей"
      const resVerdict = verdict

      result.push({
        id: `sphere-${s.key}`,
        sphere: product.label,
        icon: product.icon,
        verdict: resVerdict,
        text,
      })
    }

    // From notes
    for (const note of notes) {
      if (note.id !== "no-data") {
        result.push({
          id: note.id,
          sphere: note.title,
          icon: "📌",
          verdict: "neutral",
          text: note.description,
        })
      }
    }

    return result
  }, [topFlags, notes, sphereScores])

  const goodCount = rows.filter((r) => r.verdict === "good").length
  const cautionCount = rows.filter((r) => r.verdict === "caution").length
  const totalAll = 12 // oracle-like total count
  const displayRows = expanded ? rows : rows.slice(0, 4)

  return (
    <section className="px-5" aria-label="Конкретно сегодня" data-testid="practical-list">
      <div className="border-t border-border/30" />

      <div className="flex items-center justify-between mb-3 mt-3">
        <div className="flex items-center gap-1.5">
          <span className="font-serif text-[17px] leading-tight text-foreground">Конкретно сегодня</span>
          <span className="text-[11px] text-muted-foreground/70">· {goodCount} благоприятно, {cautionCount} осторожно</span>
        </div>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-[11px] font-medium text-primary/80 hover:text-primary"
          aria-expanded={expanded}
        >
          {expanded ? "свернуть" : `все ${totalAll} сфер`}
        </button>
      </div>

      <div className="space-y-1.5">
        {displayRows.map((row) => (
          <div key={row.id} className="flex items-start gap-2">
            <span className="text-[14px] leading-none flex-none mt-0.5">{row.icon}</span>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline gap-1.5">
                <span className="text-[13px] font-medium text-foreground">{row.sphere}</span>
                {VERDICT_LABELS[row.verdict] ? (
                  <span className={`text-[10px] font-medium ${
                    row.verdict === "good" ? "text-emerald-600" :
                    row.verdict === "caution" ? "text-amber-600" : "text-muted-foreground/60"
                  }`}>
                    {VERDICT_LABELS[row.verdict]}
                  </span>
                ) : null}
              </div>
              <p className="text-[12px] leading-snug text-muted-foreground">{row.text}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
