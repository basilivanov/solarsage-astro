
// ############################################################################
// AI_HEADER: MODULE_ONBOARDING_PRIMARY_CTA
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: primary-cta.tsx
// owns:
//   - components/onboarding/primary-cta.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import type { ButtonHTMLAttributes } from "react"

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string
}

export function PrimaryCta({ label, disabled, className, ...rest }: Props) {
  return (
    <button
      type="button"
      disabled={disabled}
      className={`flex h-14 w-full items-center justify-center rounded-2xl bg-accent font-sans text-[15px] font-medium tracking-[-0.005em] text-accent-foreground transition active:scale-[0.99] disabled:bg-foreground/10 disabled:text-foreground/40 ${className ?? ""}`}
      {...rest}
    >
      {label}
    </button>
  )
}
