"use client"

import { useCallback, useEffect, useMemo, useState, use } from "react"
import Link from "next/link"
import { AlertOctagon, ChevronLeft, Sparkles } from "lucide-react"
import { HoraryAnswerView } from "@/components/readings/horary/horary-answer-view"
import { HoraryProgress } from "@/components/readings/horary/horary-progress"
import { getHoraryQuestion } from "@/lib/api/horary"
import type { HoraryQuestionRead } from "@/packages/contracts"
import { logEvent } from "@/lib/log"

type Props = {
  params: Promise<{ id: string }>
}

export default function HoraryAnswerPage({ params }: Props) {
  const { id } = use(params)
  const [question, setQuestion] = useState<HoraryQuestionRead | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | false>(false)
  const [pollingTimedOut, setPollingTimedOut] = useState(false)

  useEffect(() => {
    if (!id) return

    setLoading(true)
    setLoadError(false)
    getHoraryQuestion(id)
      .then((q) => {
        if (!q) {
          setLoadError("not_found")
          setLoading(false)
          return
        }
        setQuestion(q)
        setPollingTimedOut(false)
        setLoading(false)
      })
      .catch((err) => {
        logEvent("system.error", { error: String(err) }, { msg: "[HoraryAnswerPage] Error loading question", slice: "W-HORARY", module: "M-HORARY-ANSWER-PAGE", block: "LOAD_QUESTION" })
        if ((err as Error)?.name === "HoraryApiError") {
          const apiErr = err as Error & { status: number }
          if (apiErr.status === 401 || apiErr.status === 403) {
            setLoadError("auth")
          } else if (apiErr.status >= 500) {
            setLoadError("server")
          } else {
            setLoadError("unknown")
          }
        } else {
          setLoadError("network")
        }
        setLoading(false)
      })
  }, [id])

  useEffect(() => {
    if (
      !question ||
      question.status === "answered" ||
      question.status === "failed" ||
      question.status === "expired"
    ) {
      return
    }

    setPollingTimedOut(false)
    const startTime = Date.now()
    const interval = setInterval(async () => {
      if (Date.now() - startTime > 30000) {
        clearInterval(interval)
        setPollingTimedOut(true)
        return
      }

      try {
        const updated = await getHoraryQuestion(id)
        if (!updated) {
          return
        }

        setQuestion(updated)
        if (
          updated.status === "answered" ||
          updated.status === "failed" ||
          updated.status === "expired"
        ) {
          clearInterval(interval)
        }
      } catch (err) {
        logEvent("system.error", { error: String(err) }, { msg: "[HoraryAnswerPage] Poll error", slice: "W-HORARY", module: "M-HORARY-ANSWER-PAGE", block: "POLL" })
        if ((err as Error)?.name === "HoraryApiError") {
          const pollStatus = (err as Error & { status: number }).status
          if (pollStatus === 401 || pollStatus === 403) {
            clearInterval(interval)
            setLoadError("auth")
          } else if (pollStatus >= 500) {
            clearInterval(interval)
            setLoadError("server")
          }
        } else if ((err as Error)?.name === "TypeError") {
          clearInterval(interval)
          setLoadError("network")
        }
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [id, question?.status])

  const isLongRunning = useMemo(() => {
    if (!question?.createdAt) return pollingTimedOut

    return pollingTimedOut || Date.now() - new Date(question.createdAt).getTime() > 30000
  }, [pollingTimedOut, question?.createdAt])

  const retry = useCallback(() => {
    if (!id) return
    setLoading(true)
    setLoadError(false)
    getHoraryQuestion(id)
      .then((q) => {
        if (!q) {
          setLoadError("not_found")
          setLoading(false)
          return
        }
        setQuestion(q)
        setPollingTimedOut(false)
        setLoading(false)
      })
      .catch((err) => {
        logEvent("system.error", { error: String(err) }, { msg: "[HoraryAnswerPage] Retry error", slice: "W-HORARY", module: "M-HORARY-ANSWER-PAGE", block: "RETRY" })
        if ((err as Error)?.name === "HoraryApiError") {
          const apiErr = err as Error & { status: number }
          if (apiErr.status === 401 || apiErr.status === 403) {
            setLoadError("auth")
          } else if (apiErr.status >= 500) {
            setLoadError("server")
          } else {
            setLoadError("unknown")
          }
        } else {
          setLoadError("network")
        }
        setLoading(false)
      })
  }, [id])

  if (loading) {
    return <HoraryProgress />
  }

  if (loadError || !question) {
    const isRetryable = loadError === "server" || loadError === "network"
    const errorConfig =
      loadError === "auth"
        ? { title: "Нужно авторизоваться", message: "Сессия истекла. Войди в приложение заново." }
        : loadError === "server"
          ? { title: "Сервер временно недоступен", message: "Не удалось загрузить вопрос. Попробуй снова." }
          : loadError === "network"
            ? { title: "Нет соединения", message: "Проверь интернет и попробуй снова." }
            : { title: "Вопрос не найден", message: "Возможно, ссылка устарела или вопрос был удалён." }

    return (
      <div className="flex h-[80dvh] flex-col items-center justify-center p-6 text-center space-y-4">
        <h3 className="font-serif text-[20px] font-bold text-foreground">
          {errorConfig.title}
        </h3>
        <p className="text-[14px] text-muted-foreground max-w-[280px]">
          {errorConfig.message}
        </p>
        <div className="flex flex-col items-center gap-2">
          {isRetryable ? (
            <button
              onClick={retry}
              className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-5 py-2.5 text-[14px] font-medium text-primary-foreground active:scale-[0.99] transition"
            >
              Попробовать снова
            </button>
          ) : null}
          <Link
            href="/readings/horary"
            className="inline-flex items-center gap-1.5 text-[14px] text-muted-foreground hover:text-foreground transition"
          >
            <ChevronLeft className="h-4 w-4" />
            К списку вопросов
          </Link>
        </div>
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
    if (!isLongRunning) {
      return <HoraryProgress />
    }

    return (
      <div className="flex flex-col items-center justify-center min-h-[50dvh] px-6 py-12 text-center max-w-md mx-auto space-y-6">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted text-muted-foreground animate-pulse">
          <Sparkles className="h-6 w-6" />
        </div>
        <div className="space-y-2">
          <h3 className="font-serif text-[22px] font-bold text-foreground">
            Карта рассчитывается
          </h3>
          <p className="text-[14px] leading-relaxed text-muted-foreground">
            Ответ формируется дольше обычного. Вопрос сохранён — можно вернуться к истории и открыть его позже.
          </p>
        </div>
        <Link
          href="/readings/horary"
          className="inline-flex items-center gap-1.5 text-[14px] text-primary"
        >
          <ChevronLeft className="h-4 w-4" />
          Вернуться к истории
        </Link>
      </div>
    )
  }

  return <HoraryAnswerView question={question} />
}
