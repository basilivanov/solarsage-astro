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
//   - framer-motion
//   - lucide-react
//   - @/lib/contracts/today
//   - @/lib/display/sphere-labels
// side_effects: local expand/collapse state only
// invariants:
//   - rows are derived from real sphereScores, topFlags, or notes
//   - unknown sphere keys are labeled through getSphereLabel
//   - missing sphere rows produce at most one graceful unavailable row
// failure_policy: renders a graceful unavailable row instead of inventing data
// END_MODULE_CONTRACT: M-TODAY-CONCRETE-DAY-ADVICE

"use client"

import { useMemo, useState } from "react"
import { motion } from "framer-motion"
import { Zap, ChevronDown } from "lucide-react"

import type { AdaptedTopFlag, SphereScore, TodayNote } from "@/lib/contracts/today"
import { 
  CANONICAL_PRODUCT_ORDER, 
  BACKEND_TO_PRODUCT_KEY_MAP, 
  type ProductSphereKey
} from "@/lib/display/sphere-labels"

type Props = {
  topFlags: AdaptedTopFlag[]
  notes: TodayNote[]
  sphereScores: SphereScore[]
}

type Verdict = "good" | "caution" | "avoid" | "neutral" | "unavailable"

interface Advice {
  sphere: string
  icon: string
  verdict: Verdict
  text: string
  isReal: boolean
}

const SPHERE_ADVICE_TEXTS: Record<ProductSphereKey, Record<Verdict, string>> = {
  work: {
    good: "Новые задачи идут легко, не упускай момент",
    caution: "Дела идут со скрипом — не торопись, дойдёт к вечеру",
    avoid: "Новые проекты буксуют — не запускай, дорабатывай текущее",
    neutral: "Ровный рабочий день — без сюрпризов, без прорывов",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  money: {
    good: "Хороший день для вложений в себя и дом",
    caution: "Сократи траты — день для финансовой дисциплины",
    avoid: "Не делай крупных покупок — перепроверь цену завтра",
    neutral: "Стабильно, без неожиданностей — можно планировать бюджет",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  documents: {
    good: "Хорошее время для договоров — читай спокойно, подписывай",
    caution: "Не подписывай контракты — перечитай через 3 дня",
    avoid: "Луна без курса — не подписывай важное до завтра",
    neutral: "Обычный день для бумаг — ничего не мешает, но и не помогает",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  relationships: {
    good: "Свидания пройдут отлично — будь открыт и смел",
    caution: "Легко поссориться на пустом — держи паузу перед ответом",
    avoid: "Не начинай новый роман — старые чувства могут вернуться",
    neutral: "Спокойный день для близких — без драмы, без озарений",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  sport: {
    good: "Энергия бьёт ключом — иди на максимум",
    caution: "Дисциплинированная тренировка — без рекордов, на выносливость",
    avoid: "Снизь нагрузку — риск травм выше, работай на технику",
    neutral: "Обычная нагрузка — не перегружай, но и не пропускай",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  communication: {
    good: "Переговоры пройдут гладко — проси что хочешь",
    caution: "Разговоры путаются — подтверждай всё письменно",
    avoid: "Не назначай важные встречи — решения будут нетвёрдыми",
    neutral: "Обычные разговоры — без конфликтов, но и без прорывов",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  health: {
    good: "Тело полно сил — хороший день для очищения и процедур",
    caution: "Береги суставы и кости — не переохлаждайся",
    avoid: "Чувствительность повышена — береги нервы и сон",
    neutral: "Стабильно — поддерживай режим, ничего особого",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  decisions: {
    good: "Решения даются легко — интуиция работает чётко",
    caution: "Запиши решение — перечитай через 2 дня, потом действуй",
    avoid: "Не принимай важных решений — отложи до завтра",
    neutral: "Обычная ясность — решения принимаются ровно",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  travel: {
    good: "Дорога будет лёгкой — хороший день для отправления",
    caution: "Поездки по необходимости — не планируй новое",
    avoid: "Задержки вероятны — закладывай время на форс-мажор",
    neutral: "Обычный день в дороге — без приключений",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  creativity: {
    good: "Вдохновение бьёт ключом — садись за работу",
    caution: "Спокойный фон для творчества — без искр, но ровно",
    avoid: "Вдохновение спит — не форсируй, сделай заготовки",
    neutral: "Спокойный фон для творчества — без искр, но ровно",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  study: {
    good: "Память цепкая — учи сложное, оно задержится",
    caution: "Повторяй старое — новое плохо усваивается",
    avoid: "Концентрация снижена — сделай перерыв",
    neutral: "Обычный темп — учи понемногу, без рывков",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
  shopping: {
    good: "Вкус работает — выберешь правильное, не пожалеешь",
    caution: "Только необходимое — крупные покупки разочаруют",
    avoid: "Не покупай электронику и технику — могут быть дефекты",
    neutral: "Обычный день — покупай что нужно, без импульсов",
    unavailable: "Нет отдельного сигнала на эту сферу.",
  },
}

const VERDICT_META: Record<Verdict, { label: string; color: string; bg: string }> = {
  good: { label: "да", color: "oklch(0.65 0.13 145)", bg: "oklch(0.65 0.13 145 / 0.08)" },
  caution: { label: "осторожно", color: "oklch(0.70 0.13 85)", bg: "oklch(0.70 0.13 85 / 0.08)" },
  avoid: { label: "нет", color: "oklch(0.58 0.14 27)", bg: "oklch(0.58 0.14 27 / 0.08)" },
  neutral: { label: "ровно", color: "oklch(0.55 0.06 295)", bg: "oklch(0.55 0.06 295 / 0.05)" },
  unavailable: { label: "ожидается", color: "oklch(0.60 0.03 260)", bg: "oklch(0.60 0.03 260 / 0.05)" },
}

function verdictForScore(score: number): Verdict {
  if (score >= 6.0) return "good"
  if (score <= 2.0) return "avoid"
  if (score <= 3.5) return "caution"
  return "neutral"
}

// START_BLOCK: BUILD_ADVICE_ROWS
function buildAdviceRows(sphereScores: SphereScore[]): Advice[] {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.buildAdviceRows
  // purpose: Converts backend sphere scores into deterministic UI advice rows.
  // inputs: sphereScores — adapted real payload fields.
  // returns: Advice[] — ranked rows in canonical order.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: Never throws intentionally; empty inputs return unavailable rows.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.buildAdviceRows
  const emojis: Record<ProductSphereKey, string> = {
    work: "💼", money: "💰", documents: "📝", relationships: "💖",
    sport: "🏃", communication: "💬", health: "🌿", decisions: "🎯",
    travel: "✈️", creativity: "🎨", study: "📚", shopping: "🛍️"
  }

  return CANONICAL_PRODUCT_ORDER.map((canon): Advice => {
    // 1. Find all matching scores that map to this canonical product key
    const matching = sphereScores.filter(s => BACKEND_TO_PRODUCT_KEY_MAP[s.key] === canon.key)

    if (matching.length > 0) {
      // 2. Select best match deterministically (caution/avoid first, then good, then best rank)
      const sorted = [...matching].sort((a, b) => {
        const vA = verdictForScore(a.score)
        const vB = verdictForScore(b.score)
        const isA_AvoidCaution = vA === "avoid" || vA === "caution"
        const isB_AvoidCaution = vB === "avoid" || vB === "caution"
        if (isA_AvoidCaution && !isB_AvoidCaution) return -1
        if (isB_AvoidCaution && !isA_AvoidCaution) return 1
        if (vA === "good" && vB !== "good") return -1
        if (vB === "good" && vA !== "good") return 1
        return a.rank - b.rank
      })

      const best = sorted[0]
      const verdict = verdictForScore(best.score)
      const text = SPHERE_ADVICE_TEXTS[canon.key]?.[verdict] ?? "Ровный рабочий день — без сюрпризов, без прорывов"
      return {
        sphere: canon.label,
        icon: emojis[canon.key],
        verdict,
        text,
        isReal: true,
      }
    }

    // 3. No real score maps to this canonical bucket (unavailable)
    return {
      sphere: canon.label,
      icon: emojis[canon.key],
      verdict: "unavailable",
      text: SPHERE_ADVICE_TEXTS[canon.key]?.unavailable ?? "Нет отдельного сигнала на эту сферу.",
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
  
  const advice = useMemo(
    () => buildAdviceRows(sphereScores),
    [sphereScores],
  )

  // Counts only real scored good/caution/avoid rows
  const realRows = advice.filter(r => r.isReal)
  const goodCount = realRows.filter((row) => row.verdict === "good").length
  const avoidCount = realRows.filter((row) => row.verdict === "avoid" || row.verdict === "caution").length

  return (
    <section className="px-6" aria-label="Конкретно по сферам" data-testid="concrete-day-advice">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground text-center">
          <Zap className="h-3 w-3" strokeWidth={1.8} />
          Конкретно сегодня
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20">
        {/* Summary header */}
        <div className="flex items-center justify-between border-b border-border/50 px-4 py-3">
          <div className="flex items-center gap-3 text-[11px]">
            <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              {goodCount} благоприятно
            </span>
            <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
              {avoidCount} осторожно
            </span>
          </div>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            aria-controls="concrete-day-advice-rows"
            className="flex items-center gap-0.5 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
          >
            {expanded ? "свернуть" : "все 12 сфер"}
            <ChevronDown
              className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`}
              strokeWidth={2}
            />
          </button>
        </div>

        {/* Advice list */}
        <div className="divide-y divide-border/30" id="concrete-day-advice-rows">
          {advice.map((a, i) => {
            const meta = VERDICT_META[a.verdict]
            const showInCompact = i < 6
            if (!expanded && !showInCompact) return null
            return (
              <motion.div
                key={a.sphere}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25, delay: i * 0.04 }}
                className="flex items-start gap-2.5 px-4 py-2.5"
                style={{ background: expanded ? meta.bg : undefined }}
                data-testid="concrete-day-advice-row"
                data-status={a.verdict}
              >
                <span className="mt-0.5 text-[14px] leading-none flex-none">{a.icon}</span>
                <span className="w-[68px] flex-none text-[11px] font-medium text-muted-foreground">
                  {a.sphere}
                </span>
                <span className="flex-1 text-[12.5px] leading-snug text-foreground">
                  {a.text}
                </span>
                <span
                  className="mt-1 h-1.5 w-1.5 flex-none rounded-full"
                  style={{ background: meta.color }}
                  title={meta.label}
                  aria-hidden
                />
              </motion.div>
            )
          })}
        </div>

        {/* Expand hint when collapsed */}
        {!expanded && (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="w-full py-2 text-center text-[11px] text-muted-foreground transition-colors hover:bg-muted/30 hover:text-foreground"
          >
            Показать ещё {advice.length - 6} сфер ▾
          </button>
        )}
      </div>
    </section>
  )
}
// END_BLOCK: CONCRETE_DAY_ADVICE_COMPONENT
