"use client"

import Link from "next/link"
import { CheckCircle2, XCircle, HelpCircle, ChevronRight } from "lucide-react"
import type { HoraryQuestionRead } from "@/packages/contracts"
import { HORARY_CATEGORIES } from "@/lib/contracts/horary"

type Props = {
  question: HoraryQuestionRead
}

export function HoraryQuestionCard({ question }: Props) {
  const { id, text, category, status, createdAt, answer } = question

  // Resolve verdict icon and style
  let StatusIcon = HelpCircle
  let iconClass = "text-muted-foreground"
  let bgClass = "bg-muted/10 border-border/60"
  let verdictText = "Ожидание"

  if (status === "processing") {
    verdictText = "Расчёт..."
    iconClass = "text-primary animate-pulse"
  } else if (status === "expired" || status === "failed") {
    verdictText = "Ошибка"
    iconClass = "text-destructive"
    StatusIcon = XCircle
  } else if (status === "refunded") {
    verdictText = "Возвращен"
    iconClass = "text-muted-foreground"
    StatusIcon = HelpCircle
  } else if (status === "answered" && answer) {
    if (answer.verdict === "yes") {
      StatusIcon = CheckCircle2
      iconClass = "text-emerald-500"
      bgClass = "border-emerald-500/10 bg-emerald-500/[0.02]"
      verdictText = "Да"
    } else if (answer.verdict === "no") {
      StatusIcon = XCircle
      iconClass = "text-rose-500"
      bgClass = "border-rose-500/10 bg-rose-500/[0.02]"
      verdictText = "Нет"
    } else {
      StatusIcon = HelpCircle
      iconClass = "text-purple-500"
      bgClass = "border-purple-500/10 bg-purple-500/[0.02]"
      verdictText = "Возможно"
    }
  }

  const catMeta = HORARY_CATEGORIES.find((c) => c.key === category)

  const formatDisplayDate = (iso: string) => {
    try {
      const d = new Date(iso)
      return d.toLocaleString("ru-RU", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch {
      return iso
    }
  }

  return (
    <Link
      href={`/readings/horary/${id}`}
      className={`block rounded-2xl border p-4 hover:bg-foreground/[0.01] active:scale-[0.99] transition ${bgClass}`}
    >
      <div className="flex items-start gap-3.5">
        <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-card border border-border/50">
          <StatusIcon className={`h-5 w-5 ${iconClass}`} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            {catMeta && (
              <span className="inline-flex items-center gap-1 rounded-full border border-border/60 bg-card px-2.5 py-0.5 text-[11px] text-foreground/75">
                <span>{catMeta.emoji}</span>
                <span>{catMeta.label}</span>
              </span>
            )}
            <span className="text-[12px] text-muted-foreground">
              {formatDisplayDate(createdAt)}
            </span>
          </div>

          <p className="mt-2 font-serif text-[15px] leading-snug text-foreground/90 line-clamp-2">
            {text}
          </p>

          <div className="mt-2 flex items-center justify-between text-[13px] text-muted-foreground">
            <span>Ответ: <strong className="text-foreground">{verdictText}</strong></span>
            <span className="flex items-center gap-0.5 text-[12px] text-primary/80 font-medium">
              Подробнее
              <ChevronRight className="h-3 w-3" />
            </span>
          </div>
        </div>
      </div>
    </Link>
  )
}
