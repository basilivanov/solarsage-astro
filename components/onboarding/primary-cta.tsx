
// ############################################################################
// AI_HEADER: MODULE_ONBOARDING_PRIMARY_CTA
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################
// START_MODULE_CONTRACT: M-ONBOARDING-PRIMARY-CTA
// purpose: Render primary CTA button for onboarding step navigation and submission.
// owns:
//   - components/onboarding/primary-cta.tsx
// inputs: label (string), disabled, className, ButtonHTMLAttributes
// outputs: PrimaryCta React component
// dependencies: none
// side_effects: none (pure UI)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-ONBOARDING-PRIMARY-CTA

// START_MODULE_MAP: M-ONBOARDING-PRIMARY-CTA
// public_entrypoints:
//   - PrimaryCta
// semantic_blocks:
//   - PRIMARY_CTA_COMPONENT: primary CTA button component
// owned_tests:
//   - __tests__/components/OnboardingFlow.test.tsx
// END_MODULE_MAP: M-ONBOARDING-PRIMARY-CTA
"use client"

import type { ButtonHTMLAttributes } from "react"

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string
}

// START_BLOCK: PRIMARY_CTA_COMPONENT
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
// END_BLOCK: PRIMARY_CTA_COMPONENT
