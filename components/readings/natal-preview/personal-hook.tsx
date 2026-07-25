
// ############################################################################
// AI_HEADER: MODULE_NATAL-PREVIEW_PERSONAL_HOOK
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: personal-hook.tsx
// owns:
//   - components/readings/natal-preview/personal-hook.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// public_entrypoints:
//   - PersonalHook
// semantic_blocks:
//   - PERSONAL_HOOK: Natal preview personal hook callout component
// owned_tests:
//   - __tests__/natal/natal-component-states.test.tsx
// END_MODULE_MAP

"use client"

type Props = {
  text: string
}

// START_BLOCK: PERSONAL_HOOK
export function PersonalHook({ text }: Props) {
  if (!text) return null

  return (
    <blockquote className="rounded-2xl border border-primary/12 bg-gradient-to-br from-primary/[0.04] to-primary/[0.01] px-5 py-4">
      <p className="font-serif text-[17px] leading-relaxed text-foreground/90">
        {text}
      </p>
    </blockquote>
  )
}
// END_BLOCK: PERSONAL_HOOK
