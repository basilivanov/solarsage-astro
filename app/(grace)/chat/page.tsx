
// ############################################################################
// AI_HEADER: APP_CHAT_PAGE — locked placeholder route for the future assistant.
// ROLE: Client Next.js page called by /chat; exposes only a non-interactive coming-soon card.
// ############################################################################

// START_MODULE_CONTRACT: M-APP-CHAT-PAGE
// purpose: Render the locked chat placeholder without starting chat API or agent flows.
// owns:
//   - app/(grace)/chat/page.tsx
// inputs: none.
// outputs: LockedFeatureCard with stable title, description and badge.
// dependencies: LockedFeatureCard.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - Route never calls chat APIs while the feature is locked.
//   - Coming-soon copy and locked presentation are delegated to LockedFeatureCard.
// failure_policy: Rendering errors bubble to the route boundary.
// END_MODULE_CONTRACT: M-APP-CHAT-PAGE

// START_MODULE_MAP: M-APP-CHAT-PAGE
// public_entrypoints:
//   - ChatPage (default).
// semantic_blocks:
//   - LOCKED_PLACEHOLDER: render the unavailable assistant state.
// owned_tests:
//   - none direct.
// END_MODULE_MAP: M-APP-CHAT-PAGE
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
