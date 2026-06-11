
// ############################################################################
// AI_HEADER: MODULE_ONBOARDING_STEP_DONE
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/onboarding/step-done.tsx
// owns:
//   - components/onboarding/step-done.tsx
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

"use client"

import { useEffect, useState } from "react"
import { PrimaryCta } from "./primary-cta"

type Props = {
  onFinish: () => void
}

const PREPARE_STAGES = [
  "Считаем положение планет",
  "Строим твои дома и аспекты",
  "Собираем первый разбор дня",
]

export function StepDone({ onFinish }: Props) {
  const [stage, setStage] = useState(0)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const t1 = window.setTimeout(() => setStage(1), 500)
    const t2 = window.setTimeout(() => setStage(2), 1000)
    const t3 = window.setTimeout(() => setReady(true), 1500)
    return () => {
      window.clearTimeout(t1)
      window.clearTimeout(t2)
      window.clearTimeout(t3)
    }
  }, [])

  return (
    <div
      className="flex h-full w-full flex-col bg-background"
      style={{
        paddingTop: "max(env(safe-area-inset-top), 1rem)",
        paddingBottom: "max(env(safe-area-inset-bottom), 1rem)",
      }}
    >
      <div className="flex flex-1 flex-col justify-center px-5">
        <div
          className="mb-8 flex h-12 w-12 items-center justify-center rounded-full border border-accent/40 bg-accent/10"
          aria-hidden="true"
        >
          <span className="h-2 w-2 rounded-full bg-accent" />
        </div>

        <p className="font-sans text-[11px] uppercase tracking-[0.18em] text-accent">
          Готово
        </p>
        <h1 className="mt-3 font-serif text-[40px] leading-[1.05] tracking-[-0.01em] text-foreground text-balance">
          Твоя карта собрана.
          <br />
          <span className="italic text-foreground/80">
            Готовим первый день.
          </span>
        </h1>

        <ul className="mt-10 space-y-3">
          {PREPARE_STAGES.map((label, i) => {
            const done = i < stage || ready
            const active = i === stage && !ready
            return (
              <li
                key={label}
                className={`flex items-center gap-3 font-sans text-[14px] transition ${
                  done
                    ? "text-foreground/75"
                    : active
                      ? "text-foreground"
                      : "text-foreground/30"
                }`}
              >
                <span
                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition ${
                    done
                      ? "border-accent bg-accent"
                      : active
                        ? "border-accent bg-background"
                        : "border-border bg-background"
                  }`}
                  aria-hidden="true"
                >
                  {done ? (
                    <svg
                      className="h-3 w-3 text-accent-foreground"
                      viewBox="0 0 12 12"
                      fill="none"
                    >
                      <path
                        d="M2.5 6.5L5 9L10 3.5"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  ) : active ? (
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
                  ) : null}
                </span>
                {label}
              </li>
            )
          })}
        </ul>
      </div>

      <div className="px-5">
        <PrimaryCta
          label={ready ? "Открыть мой день" : "Ещё секунду…"}
          onClick={onFinish}
          disabled={!ready}
        />
      </div>
    </div>
  )
}
