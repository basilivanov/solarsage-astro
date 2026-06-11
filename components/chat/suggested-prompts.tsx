
// ############################################################################
// AI_HEADER: MODULE_CHAT_SUGGESTED_PROMPTS
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/chat/suggested-prompts.tsx
// owns:
//   - components/chat/suggested-prompts.tsx
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

