import React from "react"
import { TodayV2Block } from "@/lib/contracts/today"
import { TechniqueChip } from "./technique-chip"

interface ActivationEvidenceCardProps {
  v2: TodayV2Block | null | undefined
}

export function ActivationEvidenceCard({ v2 }: ActivationEvidenceCardProps) {
  if (!v2) return null

  const { activationSummary, activationEvidence } = v2

  return (
    <div
      data-testid="activation-evidence-card"
      className="p-4 bg-white rounded-2xl border border-slate-100 shadow-sm space-y-4"
    >
      <h3 className="text-base font-semibold text-slate-900">
        Астрологический контекст дня
      </h3>
      <p className="text-sm text-slate-600 font-medium">
        {activationSummary.headline}
      </p>

      {activationSummary.topActivatedTargets.length > 0 && (
        <div className="space-y-3 pt-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Главные фокусы сегодня
          </h4>
          <div className="space-y-2">
            {activationSummary.topActivatedTargets.map((target, idx) => (
              <div
                key={`${target.targetType}-${target.targetKey}-${idx}`}
                className="flex flex-col gap-1 p-2.5 rounded-lg bg-slate-50 border border-slate-100"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-800">
                    {target.label}
                  </span>
                  <span className="text-xs text-slate-500 font-medium">
                    {target.familyCount} техн.
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {target.techniques.map((tech) => (
                    <TechniqueChip key={tech} technique={tech} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activationEvidence.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-slate-100">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Детальные факторы
          </h4>
          <ul className="space-y-1.5">
            {activationEvidence.map((evidence, idx) => (
              <li
                key={evidence.id || idx}
                className="text-xs text-slate-600 flex items-start gap-2"
              >
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 shrink-0" />
                <span>{evidence.evidence}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
