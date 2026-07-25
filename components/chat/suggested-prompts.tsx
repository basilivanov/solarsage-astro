
// ############################################################################
// AI_HEADER: MODULE_CHAT_SUGGESTED_PROMPTS
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT: M-CHAT-SUGGESTED-PROMPTS
// purpose: Render quick-start suggested prompt question buttons for empty chat state.
// owns:
//   - components/chat/suggested-prompts.tsx
// inputs: prompts (string[]), onPick
// outputs: SuggestedPrompts React component
// dependencies: lucide-react
// side_effects: none (pure UI)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-CHAT-SUGGESTED-PROMPTS

// START_MODULE_MAP: M-CHAT-SUGGESTED-PROMPTS
// public_entrypoints:
//   - SuggestedPrompts
// semantic_blocks:
//   - SUGGESTED_PROMPTS_COMPONENT: suggested prompts list component
// owned_tests:
//   - __tests__/components/SuggestedPrompts.test.tsx
// END_MODULE_MAP: M-CHAT-SUGGESTED-PROMPTS
"use client"

import { ArrowUpRight } from "lucide-react"

type Props = {
  prompts: string[]
  onPick: (_text: string) => void
}

/**
 * Стартовые подсказки в пустом состоянии чата.
 * Клик мгновенно отправляет вопрос — это короткая дорожка к первому
 * ответу, такая же как в большинстве consumer ИИ-приложений.
 */
// START_BLOCK: SUGGESTED_PROMPTS_COMPONENT
export function SuggestedPrompts({ prompts, onPick }: Props) {
  return (
    <ul className="flex flex-col gap-2">
      {prompts.map((p) => (
        <li key={p}>
          <button
            type="button"
            onClick={() => onPick(p)}
            className="flex w-full items-center justify-between gap-3 rounded-2xl border border-border/70 bg-card px-3.5 py-3 text-left text-[14px] leading-snug text-foreground transition active:bg-accent"
          >
            <span className="text-pretty">{p}</span>
            <ArrowUpRight
              className="h-4 w-4 flex-none text-muted-foreground"
              strokeWidth={1.6}
            />
          </button>
        </li>
      ))}
    </ul>
  )
}
// END_BLOCK: SUGGESTED_PROMPTS_COMPONENT

