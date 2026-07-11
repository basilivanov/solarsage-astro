// ############################################################################
// AI_HEADER: MODULE_WHY_TIME_HORIZON_CARD — human-first Why time horizon card.
// ROLE: Presents one preselected long, medium, or fast personal storyline.
// ############################################################################

// START_MODULE_CONTRACT: M-WHY-TIME-HORIZON-CARD
// purpose: Render one human-first time horizon with optional readable timing from selected evidence.
// owns:
//   - components/today/why-time-horizon-card.tsx
// inputs: horizon — presentation-selected horizon with safe why copy, range, and optional timing evidence.
// outputs: Stable why-time-horizon article with visible metadata/title/body and optional timing container.
// dependencies: lib/presentation/today-v2 types and stage formatter.
// side_effects: none.
// emitted_logs: none.
// invariants: technical vocabulary and raw evidence never render; only localized date range, peak, and stage may derive from evidence timing.
// failure_policy: uses a neutral structural fallback when safe why copy is absent.
// END_MODULE_CONTRACT: M-WHY-TIME-HORIZON-CARD

// START_MODULE_MAP: M-WHY-TIME-HORIZON-CARD
// public_entrypoints:
//   - WhyTimeHorizonCard
// semantic_blocks:
//   - HORIZON_CARD: visual long/medium/fast presentation with optional readable timing.
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP: M-WHY-TIME-HORIZON-CARD

import { getEvidenceStageLabel, getEvidenceTimingPreview, type WhyTimeHorizon } from "@/lib/presentation/today-v2"

const HORIZON_META = {
  long: { number: "01", label: "Большой сюжет", tone: "border-violet-300/80 bg-violet-100/35 dark:border-violet-400/35 dark:bg-violet-500/10" },
  medium: { number: "02", label: "Активная волна", tone: "border-violet-300 bg-violet-50/75 dark:border-violet-400/45 dark:bg-violet-500/15" },
  fast: { number: "03", label: "Триггер сегодня", tone: "border-violet-200 bg-violet-50/40 dark:border-violet-400/25 dark:bg-violet-500/5" },
} as const

const RU_MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]

function formatTimingDate(value: string, includeTime = false): string {
  const date = new Date(value)
  const dateText = `${date.getUTCDate()} ${RU_MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}`
  if (!includeTime) return dateText
  return `${dateText}, ${String(date.getUTCHours()).padStart(2, "0")}:${String(date.getUTCMinutes()).padStart(2, "0")}`
}

// START_BLOCK: HORIZON_CARD
export function WhyTimeHorizonCard({ horizon }: { horizon: WhyTimeHorizon }) {
  // START_FUNCTION_CONTRACT: F-M-WHY-TIME-HORIZON-CARD.WhyTimeHorizonCard
  // purpose: Render a selected horizon's human copy and visible duration range.
  // inputs: horizon — pure presentation model selected by the parent.
  // returns: Human-first horizon article JSX.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: falls back to neutral copy when backend why copy is missing.
  // END_FUNCTION_CONTRACT: F-M-WHY-TIME-HORIZON-CARD.WhyTimeHorizonCard
  const meta = HORIZON_META[horizon.id]
  const primary = horizon.whyItems[0]
  const timingEvidence = horizon.evidence[0]
  const timing = getEvidenceTimingPreview(timingEvidence)
  const hasTiming = Boolean(timing.activeFrom || timing.exactAt || timing.activeUntil)
  const stage = getEvidenceStageLabel(timingEvidence?.phase)
  return (
    <article
      data-testid="why-time-horizon"
      data-horizon={horizon.id}
      data-state="ready"
      className={`relative overflow-hidden rounded-2xl border p-4 ${meta.tone}`}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-violet-700 dark:text-violet-200">
          {meta.number} · {meta.label}
        </p>
        <span data-testid="why-time-horizon-range" className="rounded-full bg-card/85 px-2.5 py-1 text-[11px] font-medium text-muted-foreground shadow-sm">
          {horizon.rangeLabel}
        </span>
      </div>
      <h3 data-testid="why-time-horizon-title" className="mt-4 font-serif text-[23px] leading-[1.22] text-foreground">
        {primary?.title || "Личный сюжет периода"}
      </h3>
      <p data-testid="why-time-horizon-body" className="mt-3 text-[15px] leading-relaxed text-foreground/80">
        {primary?.body || "Эта тема может ощущаться в своём темпе и помогает заметить, на что сейчас стоит опереться."}
      </p>
      {hasTiming ? (
        <div data-testid="why-time-horizon-timing" className="mt-4 space-y-1.5 rounded-xl border border-violet-200/80 bg-card/70 px-3 py-2.5 text-[13px] leading-snug text-foreground/80 dark:border-violet-400/25">
          {timing.activeFrom && timing.activeUntil ? (
            <p><span className="font-semibold text-foreground">{horizon.id === "long" ? "Действует" : "Активно"}:</span> {formatTimingDate(timing.activeFrom)} — {formatTimingDate(timing.activeUntil)}</p>
          ) : null}
          {timing.exactAt ? (
            <p><span className="font-semibold text-foreground">Пик:</span> {formatTimingDate(timing.exactAt, timing.exactAt.includes("T"))}</p>
          ) : null}
          {stage ? <p><span className="font-semibold text-foreground">Сейчас:</span> {stage}</p> : null}
        </div>
      ) : null}
    </article>
  )
}
// END_BLOCK: HORIZON_CARD
