
// ############################################################################
// AI_HEADER: MODULE_CHAT_CONTEXT_PILL
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT: M-CHAT-CONTEXT-PILL
// purpose: Render chat context status pill showing birth data summary indicator.
// owns:
//   - components/chat/context-pill.tsx
// inputs: summary (string)
// outputs: ContextPill React component
// dependencies: lucide-react
// side_effects: none (pure UI)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-CHAT-CONTEXT-PILL

// START_MODULE_MAP: M-CHAT-CONTEXT-PILL
// public_entrypoints:
//   - ContextPill
// semantic_blocks:
//   - CONTEXT_PILL_COMPONENT: context pill component
// owned_tests:
//   - __tests__/components/ContextPill.test.tsx
// END_MODULE_MAP: M-CHAT-CONTEXT-PILL
import { Sparkles } from "lucide-react"

/**
 * Маленькая плашка под заголовком чата: показывает, что агент
 * работает с конкретной картой пользователя. Это одновременно и
 * сигнал доверия («он знает мои данные»), и трансперенси — видно,
 * какой контекст подмешан в ответы.
 */
// START_BLOCK: CONTEXT_PILL_COMPONENT
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
// END_BLOCK: CONTEXT_PILL_COMPONENT
