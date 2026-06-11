
// ############################################################################
// AI_HEADER: MODULE_NATAL-PREVIEW_PERSONAL_HOOK
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/readings/natal-preview/personal-hook.tsx
// owns:
//   - components/readings/natal-preview/personal-hook.tsx
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

type Props = {
  text: string
}

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
