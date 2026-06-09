"use client"

import { useEffect, useState, use } from "react"
import Link from "next/link"
import { AlertOctagon, ChevronLeft } from "lucide-react"
import { HoraryAnswerView } from "@/components/readings/horary/horary-answer-view"
import { HoraryProgress } from "@/components/readings/horary/horary-progress"
import { getHoraryQuestion } from "@/lib/api/horary"
import type { HoraryQuestionRead } from "@/packages/contracts"

type Props = {
  params: Promise<{ id: string }>
}

export default function HoraryAnswerPage({ params }: Props) {
  const { id } = use(params)
  const [question, setQuestion] = useState<HoraryQuestionRead | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    getHoraryQuestion(id)
      .then((q) => {
        setQuestion(q)
        setLoading(false)
      })
      .catch((err) => {
        console.error("[HoraryAnswerPage] Error loading question:", err)
        setLoading(false)
      })
  }, [id])

  if (loading) {
    return <HoraryProgress />
  }

  if (!question) {
    return (
      <div className="flex h-[80dvh] flex-col items-center justify-center p-6 text-center space-y-4">
        <h3 className="font-serif text-[20px] font-bold text-foreground">
          Вопрос не найден
        </h3>
        <p className="text-[14px] text-muted-foreground max-w-[280px]">
          Возможно, ссылка устарела или вопрос был удалён.
        </p>
        <Link
          href="/readings/horary"
          className="inline-flex items-center gap-1.5 text-[14px] text-primary"
        >
          <ChevronLeft className="h-4 w-4" />
          К списку вопросов
        </Link>
      </div>
    )
  }

  if (question.status === "failed" || question.status === "expired") {
    return (
      <div className="flex h-full w-full flex-col bg-background">
        <header
          className="flex-none px-4 pb-4 border-b border-border/40"
          style={{ paddingTop: "max(env(safe-area-inset-top), 1rem)" }}
        >
          <Link
            href="/readings/horary"
            className="inline-flex items-center gap-1.5 text-[14px] text-muted-foreground hover:text-foreground active:scale-95 transition"
          >
            <ChevronLeft className="h-4 w-4" />
            <span>Хорарные вопросы</span>
          </Link>
        </header>
        <div
          className="flex-1 px-5 py-8 max-w-md mx-auto w-full space-y-5"
          data-testid="horary-error-state"
        >
          <div className="flex flex-col items-center text-center space-y-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <AlertOctagon className="h-6 w-6" strokeWidth={1.7} />
            </div>
            <h3 className="font-serif text-[20px] font-bold text-foreground">
              Не удалось построить ответ
            </h3>
            <p className="text-[14px] leading-relaxed text-foreground/80 max-w-[320px]">
              Не удалось построить ответ. Мы не будем показывать общий текст
              вместо реального разбора. Попробуй задать вопрос ещё раз.
            </p>
          </div>
          {question.creditRefunded ? (
            <div
              className="rounded-2xl border border-emerald-500/30 bg-emerald-500/[0.06] px-4 py-3 text-center text-[13.5px] text-emerald-700 dark:text-emerald-300"
              data-testid="horary-refund-notice"
            >
              Списание возвращено.
            </div>
          ) : null}
          <Link
            href="/readings/horary"
            className="block rounded-2xl bg-primary text-primary-foreground text-center py-3 text-[14px] font-medium active:scale-[0.99] transition"
          >
            Задать вопрос заново
          </Link>
        </div>
      </div>
    )
  }

  if (!question.answer) {
    return <HoraryProgress />
  }

  return <HoraryAnswerView question={question} />
}
