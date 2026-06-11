
// ############################################################################
// AI_HEADER: MODULE_CHAT_CONTEXT_PILL
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/chat/context-pill.tsx
// owns:
//   - components/chat/context-pill.tsx
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

import { Sparkles } from "lucide-react"

/**
 * Маленькая плашка под заголовком чата: показывает, что агент
 * работает с конкретной картой пользователя. Это одновременно и
 * сигнал доверия («он знает мои данные»), и трансперенси — видно,
 * какой контекст подмешан в ответы.
 */
export function ContextPill({ summary }: { summary: string }) {
  return (
    <div className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-border/70 bg-secondary/60 px-2.5 py-1 text-[11px] leading-none text-muted-foreground">
      <Sparkles
        className="h-3 w-3 flex-none text-primary"
        strokeWidth={1.8}
      />
      <span className="truncate">с учётом твоей карты · {summary}</span>
    </div>
  )
}
