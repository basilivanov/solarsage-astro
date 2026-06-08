"use client"

import { useEffect, useState, use } from "react"
import { HoraryAnswerView } from "@/components/readings/horary/horary-answer-view"
import { HoraryProgress } from "@/components/readings/horary/horary-progress"
import { getHoraryQuestion, type HoraryQuestion } from "@/lib/api/horary"

type Props = {
  params: Promise<{ id: string }>
}

export default function HoraryAnswerPage({ params }: Props) {
  const { id } = use(params)
  const [question, setQuestion] = useState<HoraryQuestion | null>(null)
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

  if (!question || !question.answer) {
    return (
      <div className="flex h-[80dvh] flex-col items-center justify-center p-6 text-center space-y-4">
        <h3 className="font-serif text-[20px] font-bold text-foreground">
          Вопрос не найден
        </h3>
        <p className="text-[14px] text-muted-foreground max-w-[280px]">
          Возможно, расчет еще не завершен или произошла ошибка при генерации ответа.
        </p>
      </div>
    )
  }

  return <HoraryAnswerView question={question} />
}
