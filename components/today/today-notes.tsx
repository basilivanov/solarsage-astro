
// ############################################################################
// AI_HEADER: MODULE_TODAY_TODAY_NOTES
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TODAY-CALENDAR
// #########################################// START_MODULE_CONTRACT
// purpose: UI today-notes — component
// owns:
//   - components/today/today-notes.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { useState } from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"
import { getIcon } from "@/lib/icons"
import type { TodayNote } from "@/lib/today"

type Props = {
  notes: TodayNote[]
  /** Показать только первые N флагов (для teaser-состояния paywall). */
  limit?: number
  heading?: string
}

export function TodayNotes({
  notes,
  limit,
  heading = "Сегодня важно учесть",
}: Props) {
  const list = typeof limit === "number" ? notes.slice(0, limit) : notes
  const [openId, setOpenId] = useState<string | null>(null)

  if (list.length === 0) return null

  return (
    <section className="px-5" aria-labelledby="today-notes-heading">
      <h2
        id="today-notes-heading"
        className="mb-3 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground"
      >
        {heading}
      </h2>

      <div className="overflow-hidden rounded-2xl border border-border/70 bg-card">
        {list.map((note, i) => {
          const Icon = getIcon(note.iconName)
          const isOpen = openId === note.id
          const isLast = i === list.length - 1

          return (
            <div
              key={note.id}
              className={!isLast ? "border-b border-border/60" : ""}
            >
              <button
                type="button"
                onClick={() => setOpenId(isOpen ? null : note.id)}
                aria-expanded={isOpen}
                aria-controls={`note-hint-${note.id}`}
                className="flex w-full items-center gap-4 px-4 py-4 text-left transition active:bg-muted/60"
              >
                <div className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-accent">
                  <Icon
                    className="h-[18px] w-[18px] text-accent-foreground"
                    strokeWidth={1.6}
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[15px] font-medium leading-snug text-foreground">
                    {note.title}
                  </div>
                  <div className="mt-0.5 text-[13px] leading-snug text-muted-foreground">
                    {note.description}
                  </div>
                </div>
                <ChevronDown
                  className={cn(
                    "h-4 w-4 flex-none text-muted-foreground/70 transition-transform",
                    isOpen && "rotate-180",
                  )}
                  strokeWidth={1.75}
                />
              </button>

              {isOpen ? (
                <div
                  id={`note-hint-${note.id}`}
                  className="border-t border-border/60 bg-secondary/40 px-4 py-4"
                >
                  <HintRow label="Что это значит" text={note.hint.meaning} />
                  <HintRow
                    label="Почему это важно"
                    text={note.hint.whyImportant}
                  />
                  <HintRow
                    label="Как это у меня"
                    text={note.hint.howForMe}
                    last
                  />
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    </section>
  )
}

function HintRow({
  label,
  text,
  last,
}: {
  label: string
  text: string
  last?: boolean
}) {
  return (
    <div className={last ? "" : "mb-3"}>
      <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </div>
      <p className="mt-1 font-serif text-[14px] leading-[1.5] text-foreground/85">
        {text}
      </p>
    </div>
  )
}
