
// ############################################################################
// AI_HEADER: MODULE_CHAT_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI page — component
// owns:
//   - app/(grace)/chat/page.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
