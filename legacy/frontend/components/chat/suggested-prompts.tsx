"use client"

import { ArrowUpRight } from "lucide-react"

type Props = {
  prompts: string[]
  onPick: (text: string) => void
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
