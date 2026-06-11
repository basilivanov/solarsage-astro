
// ############################################################################
// AI_HEADER: MODULE_CHAT_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Next.js page — app/(grace)/chat/page.tsx
// owns:
//   - app/(grace)/chat/page.tsx
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

import { LockedFeatureCard } from "@/components/locked-feature-card"

export default function ChatPage() {
  return (
    <LockedFeatureCard
      title="Спросить"
      description="Скоро здесь появится личный астрологический ассистент. Он будет отвечать с учётом твоей натальной карты и текущих транзитов."
      badge="Скоро"
    />
  )
}
