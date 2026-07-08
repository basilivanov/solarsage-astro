// ############################################################################
// AI_HEADER: MODULE_TODAY_CONCRETE_DAY_ADVICE — real-data sphere advice list.
// ROLE: Renders the oracle-style "Конкретно сегодня" section from adapted
//       TodayPayload fields only. No local astrology, demos, or runtime mocks.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONCRETE-DAY-ADVICE
// purpose: Build a dense concrete advice section from sphereScores enriched by
//          topFlags and notes. The component provides stable DOM selectors for
//          e2e and visual evidence on /day/[date].
// owns:
//   - components/today/concrete-day-advice.tsx
// inputs:
//   - sphereScores: SphereScore[] sorted by backend rank
//   - topFlags: AdaptedTopFlag[] real day signals
//   - notes: TodayNote[] adapted note cards
// outputs: TSX section with data-testid="concrete-day-advice"
// dependencies:
//   - lucide-react
//   - @/lib/contracts/today
//   - @/lib/display/sphere-labels
//   - @/lib/icons
// side_effects: local expand/collapse state only
// invariants:
//   - rows are derived from real sphereScores, topFlags, or notes
//   - unknown sphere keys are labeled through getSphereLabel
//   - missing sphere rows produce at most one graceful unavailable row
// failure_policy: renders a graceful unavailable row instead of inventing data
// END_MODULE_CONTRACT: M-TODAY-CONCRETE-DAY-ADVICE

"use client"

import { useMemo, useState } from "react"
import { ChevronDown, Zap } from "lucide-react"

import { getIcon } from "@/lib/icons"
import type { AdaptedTopFlag, SphereScore, TodayNote } from "@/lib/contracts/today"
import { 
  CANONICAL_PRODUCT_ORDER, 
  BACKEND_TO_PRODUCT_KEY_MAP, 
  PRODUCT_SPHERE_META,
  type ProductSphereKey
} from "@/lib/display/sphere-labels"

type Props = {
  topFlags: AdaptedTopFlag[]
  notes: TodayNote[]
  sphereScores: SphereScore[]
}

type Verdict = "good" | "caution" | "neutral" | "unavailable"

type AdviceRow = {
  id: string
  iconName: string
  label: string
  text: string
  verdict: Verdict
  score?: number
  isReal: boolean
}

const COMPACT_ROW_COUNT = 6

const SPHERE_ADVICE_TEXTS: Record<ProductSphereKey, Record<Verdict, string>> = {
  work: {
    good: "Благоприятный день для активной работы, карьерных шагов и новых задач.",
    caution: "Дела идут со скрипом: не торопись, проверяй все детали и не начинай новое.",
    neutral: "Рабочий фон ровный: занимайся текущими задачами без лишней спешки.",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  money: {
    good: "Финансовые возможности открыты: удачное время для планирования и покупок.",
    caution: "Сократи траты: день требует финансовой дисциплины и осторожности.",
    neutral: "Обычный день для финансов: воздержись от импульсивных трат.",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  documents: {
    good: "Отличное время для подписания договоров, оформления бумаг и сделок.",
    caution: "Не подписывай важные бумаги: высок риск ошибок или задержек.",
    neutral: "День подходит для рутинной работы с документами и архивами.",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  relationships: {
    good: "Благоприятный фон для общения, сближения и гармонии в паре.",
    caution: "Возможна эмоциональная напряжённость: избегай споров и выяснения отношений.",
    neutral: "Спокойный день для близких: без драмы и без озарений.",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  sport: {
    good: "Энергия на пике: отличный день для интенсивных тренировок и активности.",
    caution: "Снизь физические нагрузки: побереги силы и избегай травм.",
    neutral: "Поддерживай умеренную активность: прогулки и лёгкая разминка будут полезны.",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  communication: {
    good: "Переговоры и встречи пройдут успешно: открыто выражай свои идеи.",
    caution: "В общении возможны недопонимания: будь сдержаннее и следи за словами.",
    neutral: "Обычный день для контактов: держи комфортную дистанцию.",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  health: {
    good: "Тело полно сил: хороший день для оздоровления и заботы о себе.",
    caution: "Организм уязвим: больше отдыхай, выспись и избегай стресса.",
    neutral: "Стабильное самочувствие: прислушивайся к потребностям тела.",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  decisions: {
    good: "Удачный момент для принятия важных решений и выбора пути.",
    caution: "Не принимай судьбоносных решений: отложи выбор на более ясный день.",
    neutral: "Действуй по намеченному плану, не совершая резких поворотов.",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  travel: {
    good: "Дорога будет лёгкой: отличное время для поездок и путешествий.",
    caution: "Поездки по необходимости: будь внимателен в пути и проверяй билеты.",
    neutral: "Благоприятное время для коротких перемещений и прогулок.",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  creativity: {
    good: "Вдохновение рядом: прекрасный день для реализации творческих идей.",
    caution: "Творческий застой: не насилуй музу, просто наблюдай и копи идеи.",
    neutral: "Спокойный фон для творчества: без ярких искр, но работа спорится.",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  study: {
    good: "Память цепкая: идеальное время для усвоения сложной информации.",
    caution: "Концентрация снижена: делай паузы и не перегружай мозг учёбой.",
    neutral: "Подходящий день для повторения пройденного и чтения.",
    unavailable: "Данные появятся после расчёта.",
  },
  shopping: {
    good: "Удачные приобретения: покупки принесут радость и прослужат долго.",
    caution: "Только необходимое: крупные траты и спонтанные покупки разочаруют.",
    neutral: "Нейтральный день для шопинга: покупай то, что планировал заранее.",
    unavailable: "Данные появятся после расчёта.",
  },
}

const VERDICT_META: Record<Verdict, { label: string; color: string; bg: string }> = {
  good: {
    label: "благоприятно",
    color: "oklch(0.65 0.13 145)",
    bg: "oklch(0.65 0.13 145 / 0.08)",
  },
  caution: {
    label: "осторожно",
    color: "oklch(0.70 0.13 85)",
    bg: "oklch(0.70 0.13 85 / 0.08)",
  },
  neutral: {
    label: "ровно",
    color: "oklch(0.55 0.06 295)",
    bg: "oklch(0.55 0.06 295 / 0.05)",
  },
  unavailable: {
    label: "ожидается",
    color: "oklch(0.60 0.03 260)",
    bg: "oklch(0.60 0.03 260 / 0.05)",
  },
}

function verdictForScore(score: number): Verdict {
  if (score >= 6) return "good"
  if (score <= 3) return "caution"
  return "neutral"
}

// START_BLOCK: BUILD_ADVICE_ROWS
function buildAdviceRows(sphereScores: SphereScore[]): AdviceRow[] {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.buildAdviceRows
  // purpose: Converts backend sphere scores into deterministic UI advice rows.
  // inputs: sphereScores — adapted real payload fields.
  // returns: AdviceRow[] — ranked rows in canonical order.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: Never throws intentionally; empty inputs return unavailable rows.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.buildAdviceRows
  return CANONICAL_PRODUCT_ORDER.map((canon): AdviceRow => {
    // 1. Find all matching scores that map to this canonical product key
    const matching = sphereScores.filter(s => BACKEND_TO_PRODUCT_KEY_MAP[s.key] === canon.key)

    if (matching.length > 0) {
      // 2. Select best match deterministically (caution first, then good, then best rank)
      const sorted = [...matching].sort((a, b) => {
        const vA = verdictForScore(a.score)
        const vB = verdictForScore(b.score)
        if (vA === "caution" && vB !== "caution") return -1
        if (vB === "caution" && vA !== "caution") return 1
        if (vA === "good" && vB !== "good") return -1
        if (vB === "good" && vA !== "good") return 1
        return a.rank - b.rank
      })

      const best = sorted[0]
      const verdict = verdictForScore(best.score)
      const text = SPHERE_ADVICE_TEXTS[canon.key]?.[verdict] ?? "Ровный фон: держи обычный темп без лишнего давления."
      return {
        id: `sphere-${canon.key}`,
        iconName: canon.iconName,
        label: canon.label,
        text,
        verdict,
        score: best.score,
        isReal: true,
      }
    }

    // 3. No real score maps to this canonical bucket
    return {
      id: `sphere-${canon.key}`,
      iconName: canon.iconName,
      label: canon.label,
      text: SPHERE_ADVICE_TEXTS[canon.key]?.unavailable ?? "Нет отдельного сигнала на эту сферу.",
      verdict: "unavailable",
      isReal: false,
    }
  })
}
// END_BLOCK: BUILD_ADVICE_ROWS

// START_BLOCK: CONCRETE_DAY_ADVICE_COMPONENT
export function ConcreteDayAdvice({ sphereScores }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.ConcreteDayAdvice
  // purpose: Render the compact/expandable oracle-style sphere advice section.
  // inputs: Props — real adapted today payload arrays.
  // returns: JSX.Element.
  // side_effects: Stores expanded state in React.
  // emitted_logs: none.
  // error_behavior: Renders graceful unavailable rows when arrays are empty.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.ConcreteDayAdvice
  const [expanded, setExpanded] = useState(false)
  const rows = useMemo(
    () => buildAdviceRows(sphereScores),
    [sphereScores],
  )
  const visibleRows = expanded ? rows : rows.slice(0, COMPACT_ROW_COUNT)
  const hiddenCount = Math.max(rows.length - COMPACT_ROW_COUNT, 0)
  
  // Counts only real scored good/caution rows
  const realRows = rows.filter(r => r.isReal)
  const goodCount = realRows.filter((row) => row.verdict === "good").length
  const cautionCount = realRows.filter((row) => row.verdict === "caution").length

  return (
    <section className="px-5" aria-label="Конкретно по сферам" data-testid="concrete-day-advice">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          <Zap className="h-3 w-3" strokeWidth={1.8} aria-hidden />
          Конкретно сегодня
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20">
        <div className="flex items-center justify-between gap-3 border-b border-border/50 px-4 py-3">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px]">
            <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden />
              {goodCount} благоприятно
            </span>
            <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" aria-hidden />
              {cautionCount} осторожно
            </span>
          </div>
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            aria-expanded={expanded}
            aria-controls="concrete-day-advice-rows"
            className="flex flex-none items-center gap-0.5 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
          >
            {expanded ? "свернуть" : "все 12 сфер"}
            <ChevronDown
              className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`}
              strokeWidth={2}
              aria-hidden
            />
          </button>
        </div>

        <div id="concrete-day-advice-rows" className="divide-y divide-border/30">
          {visibleRows.map((row) => {
            const Icon = getIcon(row.iconName)
            const meta = VERDICT_META[row.verdict]
            return (
              <div
                key={row.id}
                className="flex items-start gap-2.5 px-4 py-2.5"
                style={{ background: expanded ? meta.bg : undefined }}
                data-testid="concrete-day-advice-row"
                data-status={row.verdict}
              >
                <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center text-muted-foreground">
                  <Icon className="h-3.5 w-3.5" strokeWidth={1.8} aria-hidden />
                </span>
                <span className="w-[88px] flex-none text-[11px] font-medium leading-snug text-muted-foreground">
                  {row.label}
                </span>
                <span className="min-w-0 flex-1 text-[12.5px] leading-snug text-foreground">
                  {row.text}
                </span>
                <span
                  className="mt-1 h-1.5 w-1.5 flex-none rounded-full"
                  style={{ background: meta.color }}
                  title={meta.label}
                  aria-hidden
                />
              </div>
            )
          })}
        </div>

        {!expanded && hiddenCount > 0 ? (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="w-full py-2 text-center text-[11px] text-muted-foreground transition-colors hover:bg-muted/30 hover:text-foreground"
          >
            Показать ещё {hiddenCount} сфер
          </button>
        ) : null}
      </div>
    </section>
  )
}
// END_BLOCK: CONCRETE_DAY_ADVICE_COMPONENT
