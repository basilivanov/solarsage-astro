// ############################################################################
// AI_HEADER: MODULE_ACTIVATION_EVIDENCE_CARD
// ROLE: Personal V2 card — progressive disclosure of natal-specific day factors.
// ############################################################################

// START_MODULE_CONTRACT: M-ACTIVATION-EVIDENCE-CARD
// purpose: Present backend-owned V2 activation summary with collapsed claim and expanded evidence.
// owns:
//   - components/today/activation-evidence-card.tsx
// inputs: v2: TodayV2Block | null | undefined
// outputs: personal card TSX or null
// dependencies: TechniqueChip, lib/presentation/today-v2
// side_effects: local expand/collapse state only
// emitted_logs: none
// invariants:
//   - data-testid="activation-evidence-card"
//   - no astrology/scoring calculation
//   - at most 3 evidence items when expanded
//   - no debug/strength/activation IDs in user copy
// failure_policy: return null when no V2 or no content
// END_MODULE_CONTRACT: M-ACTIVATION-EVIDENCE-CARD

"use client"

import React, { useId, useState } from "react"
import { ChevronDown } from "lucide-react"
import type { TodayV2Block } from "@/lib/contracts/today"
import { TechniqueChip } from "./technique-chip"
import {
  dedupeTechniquesPreserveOrder,
  formatActivationEvidenceTitle,
  formatOrb,
  getPhaseLabelRu,
  getSphereLabelConcise,
  selectPrimaryEvidence,
} from "@/lib/presentation/today-v2"

interface ActivationEvidenceCardProps {
  v2: TodayV2Block | null | undefined
}

function eyebrowForFamilyCount(n: number): string {
  if (n >= 3) return `Сходимость ${n} циклов`.toUpperCase()
  if (n === 2) return "Два независимых цикла".toUpperCase()
  return "Персональный транзит дня".toUpperCase()
}

export function ActivationEvidenceCard({ v2 }: ActivationEvidenceCardProps) {
  const [open, setOpen] = useState(false)
  const detailsId = useId()

  if (!v2) return null

  const { activationSummary, activationEvidence } = v2
  const primary = activationSummary.topActivatedTargets[0] ?? null
  const activeEvidence = (activationEvidence || []).filter((e) => e.active !== false)
  if (!primary && activeEvidence.length === 0) return null

  const familyCount = primary?.familyCount ?? 1
  const techniques = dedupeTechniquesPreserveOrder(primary?.techniques || []).slice(0, 3)
  const sphereLabels = (primary?.spheres || []).slice(0, 3).map(getSphereLabelConcise)
  const selected = selectPrimaryEvidence(activationEvidence || [], primary, 3)
  const multiFamily = familyCount >= 2

  return (
    <section className="px-5" aria-label="Персональный фактор дня">
      <div
        data-testid="activation-evidence-card"
        className="relative overflow-hidden rounded-[24px] border border-violet-200/50 bg-gradient-to-br from-card via-card to-violet-50/40 p-5 shadow-[0_0_40px_-12px_rgba(109,40,217,0.18)]"
      >
        <div className="pointer-events-none absolute -right-8 -top-10 h-32 w-32 rounded-full bg-violet-300/15 blur-2xl" />

        <div className="relative flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-violet-700/80">
            {eyebrowForFamilyCount(familyCount)}
          </span>
          <span className="inline-flex items-center rounded-full border border-violet-200/70 bg-violet-50/80 px-2 py-0.5 text-[10px] font-medium text-violet-800">
            Именно для вашей карты
          </span>
        </div>

        <h3 className="relative mt-3 font-serif text-[22px] leading-[1.15] text-foreground sm:text-[24px]">
          {activationSummary.headline}
        </h3>

        <p className="relative mt-2.5 text-[14px] leading-relaxed text-foreground/80 sm:text-[15px]">
          {multiFamily
            ? "Это не общий прогноз: несколько независимых факторов затрагивают одни и те же точки вашей натальной карты"
            : "Это персональный транзит к точке вашей натальной карты, а не общий прогноз для знака"}
        </p>

        {techniques.length > 0 && (
          <div className="relative mt-3 flex flex-wrap gap-1.5">
            {techniques.map((tech) => (
              <TechniqueChip key={tech} technique={tech} />
            ))}
          </div>
        )}

        {sphereLabels.length > 0 && (
          <p className="relative mt-3 text-[13px] leading-snug text-muted-foreground">
            {sphereLabels.join(" · ")}
          </p>
        )}

        <button
          type="button"
          data-testid="activation-evidence-toggle"
          aria-expanded={open}
          aria-controls={detailsId}
          onClick={() => setOpen((v) => !v)}
          className="relative mt-4 inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-card/80 px-3 py-1.5 text-[12px] font-medium text-foreground transition-colors hover:bg-secondary/40"
        >
          {open ? "Скрыть подробности" : "Показать, откуда вывод"}
          <ChevronDown
            className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`}
            strokeWidth={2}
            aria-hidden
          />
        </button>

        {open && (
          <div id={detailsId} className="relative mt-4 space-y-3 border-t border-border/50 pt-4">
            <h4 className="text-[13px] font-semibold text-foreground">
              Что сошлось именно у вас сегодня
            </h4>
            <ul className="space-y-2.5">
              {selected.map((ev) => {
                const phase = getPhaseLabelRu(ev.phase)
                const orb = formatOrb(ev.orb)
                const title = formatActivationEvidenceTitle(ev)
                const polarity = ev.polarity || "neutral"
                return (
                  <li
                    key={ev.id}
                    data-testid="activation-evidence-item"
                    data-polarity={polarity}
                    className="rounded-xl border border-border/50 bg-secondary/20 px-3 py-2.5"
                  >
                    <div className="flex items-start gap-2">
                      <span
                        className={`mt-1.5 h-1.5 w-1.5 flex-none rounded-full ${
                          polarity === "tense"
                            ? "bg-amber-500"
                            : polarity === "supportive"
                              ? "bg-emerald-500"
                              : "bg-slate-400"
                        }`}
                        aria-hidden
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-[13px] font-medium leading-snug text-foreground">
                          {title}
                        </p>
                        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                          <TechniqueChip technique={ev.technique} />
                          {orb ? (
                            <span className="text-[11px] text-muted-foreground">орб {orb}</span>
                          ) : null}
                          {phase ? (
                            <span className="text-[11px] text-muted-foreground">{phase}</span>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </li>
                )
              })}
            </ul>
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              Основано на вашей натальной карте и положении планет на выбранную дату. Точные данные
              рождения здесь не показываются.
            </p>
          </div>
        )}
      </div>
    </section>
  )
}
