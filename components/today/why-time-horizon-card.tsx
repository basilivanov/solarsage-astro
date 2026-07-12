// ############################################################################
// AI_HEADER: MODULE_WHY_TIME_HORIZON_CARD — human-first Why time horizon card.
// ROLE: Presents one preselected long, medium, or fast personal storyline.
// ############################################################################

// START_MODULE_CONTRACT: M-WHY-TIME-HORIZON-CARD
// purpose: Render either backend-owned TodayV2 horizon cards or the legacy selector-derived fallback card.
// owns:
//   - components/today/why-time-horizon-card.tsx
// inputs: backend horizon wire model or presentation-selected legacy horizon, optional concrete-advice navigator rows, optional sphere-select callback.
// outputs: why-horizon, why-horizon-index, why-horizon-tone, why-horizon-meaning, why-horizon-timing + range/peak/state, why-horizon-manifestations, why-horizon-patterns + strength/risk, why-horizon-guidance, why-horizon-spheres + sphere, why-horizon-technical-toggle/content, legacy why-time-horizon.
// dependencies: lib/contracts/today, lib/presentation/today-v2 types and stage formatter, horizon-actions, horizon-technique-disclosure.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - backend tone presentation is selected only from horizon.tone enum; root keeps data-status.
//   - technical vocabulary and raw evidence never render in human copy.
//   - legacy path only derives localized date range, peak, and stage from evidence timing.
//   - backend human copy and backend array order are preserved exactly; frontend does not rewrite, sort, or infer them.
//   - DOM order: meaning -> timing -> manifestations -> patterns -> actions -> spheres -> tech.
//   - sphere chips: matched-row-only; >=44px touch target; missing rows produce no chip/fallback.
//   - technical disclosure last; closed content absent.
// failure_policy: uses a neutral structural fallback when safe why copy is absent.
// END_MODULE_CONTRACT: M-WHY-TIME-HORIZON-CARD

// START_MODULE_MAP: M-WHY-TIME-HORIZON-CARD
// public_entrypoints:
//   - WhyTimeHorizonCard
//   - LegacyWhyTimeHorizonCard
// semantic_blocks:
//   - BACKEND_TONE_PRESENTATION: enum-owned style/label map for backend horizon cards and badges.
//   - BACKEND_HORIZON_HEADER_AND_MEANING: index, eyebrow, title, tone badge, summary, plainExplanation.
//   - BACKEND_TIMING: range/peak/state labels with data-testid children.
//   - BACKEND_MANIFESTATIONS_AND_PATTERNS: condition body grid and optional strength/risk.
//   - BACKEND_GUIDANCE_AND_SPHERES: validity, do/avoid, matched sphere chips.
//   - BACKEND_TECHNICAL_DISCLOSURE: accessible per-horizon technique explanation.
//   - LEGACY_HORIZON_CARD: selector-derived fallback card with localized timing.
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP: M-WHY-TIME-HORIZON-CARD

import type { ConcreteAdviceBlock, TodayV2Horizon } from "@/lib/contracts/today"
import { getEvidenceStageLabel, getEvidenceTimingPreview, type WhyTimeHorizon } from "@/lib/presentation/today-v2"
import { HorizonActions } from "./horizon-actions"
import { HorizonTechniqueDisclosure } from "./horizon-technique-disclosure"

const HORIZON_INDEX = { long: "01", medium: "02", fast: "03" } as const

const RU_MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]

function formatTimingDate(value: string, includeTime = false): string {
  const date = new Date(value)
  const dateText = `${date.getUTCDate()} ${RU_MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}`
  if (!includeTime) return dateText
  return `${dateText}, ${String(date.getUTCHours()).padStart(2, "0")}:${String(date.getUTCMinutes()).padStart(2, "0")}`
}

const HORIZON_META = {
  long: { number: "01", label: "Большой сюжет", tone: "border-violet-300/80 bg-violet-100/35 dark:border-violet-400/35 dark:bg-violet-500/10" },
  medium: { number: "02", label: "Активная волна", tone: "border-violet-300 bg-violet-50/75 dark:border-violet-400/45 dark:bg-violet-500/15" },
  fast: { number: "03", label: "Триггер сегодня", tone: "border-violet-200 bg-violet-50/40 dark:border-violet-400/25 dark:bg-violet-500/5" },
} as const

const BACKEND_TONE_LABELS = {
  supportive: "Поддерживает",
  neutral: "Ровный фон",
  tense: "Требует внимания",
  mixed: "Смешанный сигнал",
} as const

const BACKEND_TONE_STYLES = {
  supportive: {
    card: "border-emerald-200/80 bg-emerald-50/45 dark:border-emerald-400/25 dark:bg-emerald-500/10",
    badge: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-100",
    timing: "border-emerald-200/80 bg-emerald-50/50 dark:border-emerald-400/20 dark:bg-emerald-500/10",
    eyebrow: "text-emerald-700 dark:text-emerald-200",
  },
  neutral: {
    card: "border-slate-200/90 bg-slate-50/55 dark:border-zinc-400/25 dark:bg-zinc-500/10",
    badge: "bg-slate-200/80 text-slate-800 dark:bg-zinc-500/20 dark:text-zinc-100",
    timing: "border-slate-200/80 bg-slate-100/70 dark:border-zinc-400/20 dark:bg-zinc-500/10",
    eyebrow: "text-slate-700 dark:text-zinc-200",
  },
  tense: {
    card: "border-rose-200/85 bg-rose-50/50 dark:border-rose-400/25 dark:bg-rose-500/10",
    badge: "bg-rose-100 text-rose-800 dark:bg-rose-500/20 dark:text-rose-100",
    timing: "border-rose-200/80 bg-rose-50/60 dark:border-rose-400/20 dark:bg-rose-500/10",
    eyebrow: "text-rose-700 dark:text-rose-200",
  },
  mixed: {
    card: "border-violet-200/80 bg-violet-50/45 dark:border-violet-400/25 dark:bg-violet-500/10",
    badge: "bg-violet-100 text-violet-800 dark:bg-violet-500/15 dark:text-violet-100",
    timing: "border-violet-200/80 bg-violet-50/45 dark:border-violet-400/20 dark:bg-violet-500/10",
    eyebrow: "text-violet-700 dark:text-violet-200",
  },
} as const

// START_BLOCK: HORIZON_CARD
export function WhyTimeHorizonCard({
  horizon,
  concreteAdvice,
  onSphereSelect,
}: {
  horizon: TodayV2Horizon
  concreteAdvice?: ConcreteAdviceBlock | null
  onSphereSelect?: (key: string) => void
}) {
  // START_FUNCTION_CONTRACT: F-M-WHY-TIME-HORIZON-CARD.WhyTimeHorizonCard
  // purpose: Render one backend-owned TodayV2 horizon card using backend labels and copy only.
  // inputs: horizon - TodayV2Horizon wire model; concreteAdvice - optional sphere navigator rows; onSphereSelect - optional navigator callback.
  // returns: Backend horizon article JSX.
  // side_effects: invokes optional onSphereSelect callback.
  // emitted_logs: none.
  // error_behavior: omits optional subsections when data is absent.
  // END_FUNCTION_CONTRACT: F-M-WHY-TIME-HORIZON-CARD.WhyTimeHorizonCard
  const index = HORIZON_INDEX[horizon.horizon]
  const adviceRows = concreteAdvice?.rows ?? []
  const toneStyle = BACKEND_TONE_STYLES[horizon.tone]
  const sphereRows = horizon.likelySpheres
    .map((key) => adviceRows.find((row) => row.key === key))
    .filter((row): row is NonNullable<typeof row> => Boolean(row))

  return (
    <article
      data-testid="why-horizon"
      data-horizon={horizon.horizon}
      data-status={horizon.tone}
      data-timing-state={horizon.timing.state}
      className={`overflow-hidden rounded-2xl border p-4 shadow-sm ${toneStyle.card}`}
    >
      {/* 1. Header: index + eyebrow + title + tone */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <span data-testid="why-horizon-index" className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-violet-100 text-[11px] font-semibold text-violet-700 dark:bg-violet-500/15 dark:text-violet-100">{index}</span>
          <p className={`mt-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${toneStyle.eyebrow}`}>{horizon.eyebrow}</p>
          <h3 className="mt-1 font-serif text-[23px] leading-[1.22] text-foreground">{horizon.title}</h3>
        </div>
        <span
          data-testid="why-horizon-tone"
          data-status={horizon.tone}
          className={`max-w-full whitespace-normal text-center flex-none rounded-full px-2.5 py-1 text-[11px] font-medium ${toneStyle.badge}`}
        >
          {BACKEND_TONE_LABELS[horizon.tone]}
        </span>
      </div>

      {/* 2. Human meaning: summary + plainExplanation */}
      <div data-testid="why-horizon-meaning" className="mt-4 space-y-2">
        <p className="text-[15px] font-semibold leading-relaxed text-foreground/90">{horizon.summary}</p>
        <p className="text-[15px] leading-relaxed text-muted-foreground">{horizon.plainExplanation}</p>
      </div>

      {/* 3. Timing */}
      <div data-testid="why-horizon-timing" className={`mt-4 rounded-2xl border px-3 py-2.5 text-[13px] leading-relaxed text-foreground/85 ${toneStyle.timing}`}>
        {horizon.timing.rangeLabel ? <p data-testid="why-horizon-timing-range"><span className="font-semibold text-foreground">Период:</span> {horizon.timing.rangeLabel}</p> : null}
        {horizon.timing.peakLabel ? <p data-testid="why-horizon-timing-peak"><span className="font-semibold text-foreground">Пик:</span> {horizon.timing.peakLabel}</p> : null}
        <p data-testid="why-horizon-timing-state"><span className="font-semibold text-foreground">Сейчас:</span> {horizon.timing.stateLabel}</p>
      </div>

      {/* 4. Manifestations */}
      <div data-testid="why-horizon-manifestations" className="mt-4 space-y-2">
        <p className="text-[12px] font-semibold text-foreground">Где это вероятнее проявится</p>
        <div className="space-y-2">
          {horizon.manifestations.map((item) => (
            <div key={item.id} className="rounded-2xl border border-border/60 bg-background/70 p-3">
              <p className="text-[13px] font-semibold text-foreground">{item.title}</p>
              {item.condition ? <p className="mt-1 text-[13px] leading-relaxed text-foreground/85">{item.condition}</p> : null}
              <p className="mt-1 text-[14px] leading-relaxed text-muted-foreground">{item.body}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 5. Patterns (strength/risk) */}
      <div data-testid="why-horizon-patterns" className="mt-4 grid gap-3 sm:grid-cols-2">
        {horizon.strength ? (
          <div data-testid="why-horizon-strength" className="rounded-2xl border border-emerald-200/80 bg-emerald-50/50 p-3 dark:border-emerald-400/20 dark:bg-emerald-500/10">
            <p className="text-[12px] font-semibold text-foreground">На что можно опереться</p>
            <p className="mt-1 text-[14px] leading-relaxed text-foreground/85">{horizon.strength.text}</p>
          </div>
        ) : null}
        {horizon.risk ? (
          <div data-testid="why-horizon-risk" className="rounded-2xl border border-rose-200/80 bg-rose-50/55 p-3 dark:border-rose-400/20 dark:bg-rose-500/10">
            <p className="text-[12px] font-semibold text-foreground">Что может мешать</p>
            <p className="mt-1 text-[14px] leading-relaxed text-foreground/85">{horizon.risk.text}</p>
          </div>
        ) : null}
      </div>

      {/* 6. Actions before spheres */}
      <HorizonActions actions={horizon.actions} />

      {/* 7. Sphere links */}
      {sphereRows.length ? (
        <div data-testid="why-horizon-spheres" className="mt-4">
          <p className="text-[12px] font-semibold text-foreground">Открыть в навигаторе по 12 сферам</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {sphereRows.map((row) => (
              <button
                key={row.key}
                type="button"
                data-testid="why-horizon-sphere"
                data-sphere-key={row.key}
                onClick={() => onSphereSelect?.(row.key)}
                aria-label={`Открыть сферу «${row.label}» в навигаторе`}
                className="min-h-11 rounded-full border border-violet-200 bg-violet-50 px-3 py-1.5 text-[13px] font-medium text-violet-800 transition hover:bg-violet-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 dark:border-violet-400/25 dark:bg-violet-500/10 dark:text-violet-100"
              >
                {row.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {/* 8. Technique disclosure last */}
      <HorizonTechniqueDisclosure explanations={horizon.techniqueExplanations} horizon={horizon.horizon} />
    </article>
  )
}

export function LegacyWhyTimeHorizonCard({ horizon }: { horizon: WhyTimeHorizon }) {
  // START_FUNCTION_CONTRACT: F-M-WHY-TIME-HORIZON-CARD.LegacyWhyTimeHorizonCard
  // purpose: Render a selected horizon's human copy and visible duration range.
  // inputs: horizon — pure presentation model selected by the parent.
  // returns: Human-first horizon article JSX.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: falls back to neutral copy when backend why copy is missing.
  // END_FUNCTION_CONTRACT: F-M-WHY-TIME-HORIZON-CARD.LegacyWhyTimeHorizonCard
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
