
// ############################################################################
// AI_HEADER: MODULE_HORARY_HORARY_SCREEN
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// #########################################// START_MODULE_CONTRACT
// purpose: UI horary-screen — component
// owns:
//   - components/readings/horary/horary-screen.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: Logging via v2 logging spine; React state management
// emitted_logs: v2 logging: logEvent/logStart/logSuccess/logFailure (frontend) or logger.* (backend)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { ChevronLeft, MessageSquare, AlertCircle } from "lucide-react"

import type { HoraryCategory } from "@/lib/contracts/horary"
import type { HoraryQuestionRead, HoraryQuotaRead, ProfileRead } from "@/packages/contracts"
import { getHoraryQuota, listHoraryQuestions, createHoraryQuestion, getHoraryQuestion } from "@/lib/api/horary"
import { getProfile } from "@/lib/api/profile"
import { useToast } from "@/hooks/use-toast"

import { HoraryQuotaBar } from "./horary-quota-bar"
import { HoraryForm } from "./horary-form"
import { HoraryQuestionCard } from "./horary-question-card"
import { HoraryPurchaseSheet } from "./horary-purchase-sheet"
import { HoraryProcessingCard } from "./horary-processing-card"
import { Spinner } from "@/components/ui/spinner"
import { logEvent } from "@/lib/log"

export function HoraryScreen() {
  const { toast } = useToast()
  const router = useRouter()

  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [showPurchase, setShowPurchase] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [activeQuestionId, setActiveQuestionId] = useState<string | null>(null)
  const [activeQuestionStartedAt, setActiveQuestionStartedAt] = useState<number | null>(null)
  const [pendingScrollId, setPendingScrollId] = useState<string | null>(null)

  const [quota, setQuota] = useState<HoraryQuotaRead | null>(null)
  const [questions, setQuestions] = useState<HoraryQuestionRead[]>([])
  const [profile, setProfile] = useState<ProfileRead | null>(null)

  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pollStartedAtRef = useRef<number | null>(null)
  const activeQuestionIdRef = useRef<string | null>(null)
  const seenAnsweredIdsRef = useRef<Set<string>>(new Set())
  const seenFailedIdsRef = useRef<Set<string>>(new Set())
  const autoNavTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const upsertQuestion = useCallback((question: HoraryQuestionRead) => {
    setQuestions((prev) => {
      const existingIndex = prev.findIndex((item) => item.id === question.id)
      if (existingIndex === 0) {
        return [question, ...prev.slice(1)]
      }
      if (existingIndex > 0) {
        return [question, ...prev.slice(0, existingIndex), ...prev.slice(existingIndex + 1)]
      }
      return [question, ...prev]
    })
  }, [])

  const loadData = useCallback(async () => {
    try {
      const [qQuota, qQuestions, qProfile] = await Promise.all([
        getHoraryQuota(),
        listHoraryQuestions(20, 0),
        getProfile(),
      ])
      setQuota(qQuota)
      setQuestions(qQuestions)
      setProfile(qProfile)
    } catch (error) {
      logEvent("system.error", { error: String(error) }, { msg: "[HoraryScreen] Failed to load data", slice: "W-HORARY", module: "M-HORARY-SCREEN", block: "INIT_LOAD" })
      toast({
        variant: "destructive",
        description: "Не удалось загрузить данные хорара",
      })
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    activeQuestionIdRef.current = activeQuestionId
  }, [activeQuestionId])

  const stopPolling = useCallback(() => {
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current)
      pollTimeoutRef.current = null
    }
    pollStartedAtRef.current = null
  }, [])

  const pollAllProcessing = useCallback(async (processingQuestions?: HoraryQuestionRead[]) => {
    const currentProcessingQuestions = processingQuestions ?? questions.filter(
      (q) => q.status === "processing" || q.status === "pending"
    )

    if (currentProcessingQuestions.length === 0) {
      stopPolling()
      return
    }

    if (!pollStartedAtRef.current) {
      pollStartedAtRef.current = Date.now()
    }

    if (Date.now() - pollStartedAtRef.current > 60000) {
      stopPolling()
      setSubmitting(false)
      toast({
        description: "Ответ формируется дольше обычного. Мы сохраним вопрос и покажем ответ, когда карта будет готова.",
      })
      return
    }

    try {
      const updates = await Promise.all(currentProcessingQuestions.map((q) => getHoraryQuestion(q.id)))
      let hasProcessingLeft = false

      updates.forEach((updatedQuestion) => {
        if (!updatedQuestion) {
          return
        }

        upsertQuestion(updatedQuestion)

        if (updatedQuestion.status === "processing" || updatedQuestion.status === "pending") {
          hasProcessingLeft = true
        }

        if (updatedQuestion.status === "answered" && !seenAnsweredIdsRef.current.has(updatedQuestion.id)) {
          seenAnsweredIdsRef.current.add(updatedQuestion.id)

          // If this is the question user just submitted, auto-scroll + auto-navigate
          const isJustSubmitted = activeQuestionIdRef.current === updatedQuestion.id
          setActiveQuestionId((current) => (current === updatedQuestion.id ? null : current))
          setActiveQuestionStartedAt((current) =>
            activeQuestionIdRef.current === updatedQuestion.id ? null : current
          )

          if (isJustSubmitted) {
            // Trigger scroll: wait for the card to render, then scroll + navigate
            setPendingScrollId(updatedQuestion.id)
          } else {
            toast({ description: "Ответ готов" })
          }
        }

        if (
          (updatedQuestion.status === "failed" || updatedQuestion.status === "expired") &&
          !seenFailedIdsRef.current.has(updatedQuestion.id)
        ) {
          seenFailedIdsRef.current.add(updatedQuestion.id)
          setActiveQuestionId((current) => (current === updatedQuestion.id ? null : current))
          setActiveQuestionStartedAt((current) =>
            activeQuestionIdRef.current === updatedQuestion.id ? null : current
          )
          toast({
            variant: "destructive",
            description:
              updatedQuestion.publicErrorMessage ||
              (updatedQuestion.status === "expired"
                ? "Время ожидания ответа истекло. Попробуйте задать вопрос снова."
                : "Не удалось рассчитать хорарный ответ. Пожалуйста, попробуйте снова."),
          })
        }
      })

      if (hasProcessingLeft) {
        pollTimeoutRef.current = setTimeout(() => {
          void pollAllProcessing()
        }, 2000)
      } else {
        stopPolling()
        setSubmitting(false)
      }
    } catch (error) {
      logEvent("system.error", { error: String(error) }, { msg: "[HoraryScreen] Polling error", slice: "W-HORARY", module: "M-HORARY-SCREEN", block: "POLLING" })
      pollTimeoutRef.current = setTimeout(() => {
        void pollAllProcessing()
      }, 2000)
    }
  }, [questions, stopPolling, toast, upsertQuestion])

  // Auto-scroll to answered card + auto-navigate to answer page
  useEffect(() => {
    if (!pendingScrollId) return

    // Wait for the card to render in the DOM after activeQuestionId is cleared
    const scrollTimer = setTimeout(() => {
      const cardEl = document.getElementById(`horary-question-${pendingScrollId}`)
      if (cardEl) {
        cardEl.scrollIntoView({ behavior: "smooth", block: "center" })

        // After the user briefly sees the card, navigate to the answer page
        if (autoNavTimeoutRef.current) clearTimeout(autoNavTimeoutRef.current)
        autoNavTimeoutRef.current = setTimeout(() => {
          router.push(`/readings/horary/${pendingScrollId}`)
          setPendingScrollId(null)
        }, 800)
      } else {
        // Card not found in DOM yet — fallback: navigate directly
        router.push(`/readings/horary/${pendingScrollId}`)
        setPendingScrollId(null)
      }
    }, 150)

    return () => {
      clearTimeout(scrollTimer)
      if (autoNavTimeoutRef.current) {
        clearTimeout(autoNavTimeoutRef.current)
        autoNavTimeoutRef.current = null
      }
    }
  }, [pendingScrollId, router])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    const hasProcessing = questions.some((q) => q.status === "processing" || q.status === "pending")

    if (!hasProcessing) {
      stopPolling()
      return
    }

    if (!pollTimeoutRef.current) {
      void pollAllProcessing()
    }

    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current)
        pollTimeoutRef.current = null
      }
    }
  }, [questions, pollAllProcessing, stopPolling])

  const handleSubmit = async (
    text: string,
    category: HoraryCategory | undefined,
    localTime: string,
    timezone: string,
    lat?: number,
    lon?: number,
    locationName?: string
  ) => {
    setSubmitting(true)
    setSubmitError(null)

    try {
      const idempotencyKey = crypto.randomUUID()
      const q = await createHoraryQuestion({
        text,
        category,
        clientTimezone: timezone,
        clientLocalTime: localTime,
        questionLat: lat,
        questionLon: lon,
        questionLocationName: locationName,
        idempotencyKey,
      })

      upsertQuestion(q)
      setActiveQuestionId(q.id)
      setActiveQuestionStartedAt(Date.now())
      pollStartedAtRef.current = Date.now()
      void pollAllProcessing([q])
    } catch (error: any) {
      logEvent("system.error", { error: String(error?.message ?? error) }, { msg: "[HoraryScreen] Failed to submit", slice: "W-HORARY", module: "M-HORARY-SCREEN", block: "SUBMIT" })
      setSubmitting(false)
      setActiveQuestionId(null)
      setActiveQuestionStartedAt(null)
      const msg = error.message || "Не удалось отправить вопрос"
      setSubmitError(msg)
      toast({
        variant: "destructive",
        description: msg,
      })
    }
  }

  // Cleanup auto-nav timeout on unmount
  useEffect(() => {
    return () => {
      if (autoNavTimeoutRef.current) {
        clearTimeout(autoNavTimeoutRef.current)
      }
    }
  }, [])

  // const pollStatus = useCallback((id: string) => {
  //   setActiveQuestionId(id)
  //   setActiveQuestionStartedAt(Date.now())
  //   if (!pollStartedAtRef.current) {
  //     pollStartedAtRef.current = Date.now()
  //   }
  //   void pollAllProcessing()
  // }, [pollAllProcessing])

  if (loading) {
    return (
      <div className="flex h-[80dvh] items-center justify-center">
        <Spinner className="h-8 w-8 text-primary" />
      </div>
    )
  }

  const hasSpendableCredit = quota
    ? (quota.weeklyFreeAvailable || quota.bonusCredits > 0 || quota.paidCredits > 0)
    : false

  const activeQuestion = activeQuestionId
    ? questions.find((q) => q.id === activeQuestionId && (q.status === "processing" || q.status === "pending"))
    : null

  const regularQuestions = activeQuestionId
    ? questions.filter((q) => q.id !== activeQuestionId)
    : questions

  return (
    <div className="flex h-full w-full flex-col bg-background overflow-y-auto">
      <header
        className="flex-none px-4 pb-4 border-b border-border/40"
        style={{ paddingTop: "max(env(safe-area-inset-top), 1rem)" }}
      >
        <Link
          href="/readings"
          className="inline-flex items-center gap-1.5 text-[14px] text-muted-foreground hover:text-foreground active:scale-95 transition"
        >
          <ChevronLeft className="h-4 w-4" />
          <span>Разборы</span>
        </Link>
      </header>

      <div className="flex-1 px-5 py-6 space-y-6 max-w-md mx-auto w-full">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="space-y-1">
          <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Раздел
          </span>
          <h2 className="font-serif text-[28px] font-bold leading-tight tracking-tight text-foreground">
            Хорарный оракул
          </h2>
          <p className="text-[14px] leading-relaxed text-muted-foreground">
            Задай конкретный вопрос и получи ответ карты на момент вопроса — с пояснением, сроками и практическим выводом.
          </p>
        </motion.div>

        {quota && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.35 }}>
            <HoraryQuotaBar quota={quota} onBuy={() => setShowPurchase(true)} />
          </motion.div>
        )}

        {hasSpendableCredit ? (
          <div className="border-t border-border/40 pt-5">
            <HoraryForm
              hasSpendableCredit={hasSpendableCredit}
              submitting={submitting}
              submitError={submitError}
              profileCurrentCity={profile?.currentLocation?.city}
              profileCurrentLat={profile?.currentLocation?.lat}
              profileCurrentLon={profile?.currentLocation?.lon}
              profileCurrentTz={profile?.currentLocation?.tz}
              profileBirthCity={profile?.birth?.birthCity}
              profileBirthLat={profile?.birth?.birthLat}
              profileBirthLon={profile?.birth?.birthLon}
              profileBirthTz={profile?.birth?.birthTz}
              onSubmit={handleSubmit}
            />
          </div>
        ) : (
          <div className="rounded-xl border border-border/60 bg-muted/20 p-4 flex gap-3 text-muted-foreground text-[13.5px]">
            <AlertCircle className="h-5 w-5 flex-none" />
            <span>
              Пожалуйста, докупите вопросы, чтобы задать новый хорарный вопрос.
            </span>
          </div>
        )}

        <div className="border-t border-border/40 pt-5 space-y-4">
          <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            История вопросов
          </h3>

          {questions.length === 0 && !activeQuestion ? (
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3, duration: 0.3 }} className="rounded-2xl border border-dashed border-border/70 p-8 text-center text-muted-foreground text-[14px] space-y-2">
              <MessageSquare className="h-8 w-8 mx-auto text-muted-foreground/45" />
              <p>Вы еще не задавали хорарных вопросов.</p>
              <p className="text-[12px]">Ваш первый вердикт появится здесь.</p>
            </motion.div>
          ) : (
            <div className="grid gap-3.5">
              {activeQuestion && (
                <HoraryProcessingCard
                  questionText={activeQuestion.text}
                  createdAt={activeQuestion.createdAt}
                  category={activeQuestion.category}
                  startedAt={activeQuestionStartedAt ?? undefined}
                />
              )}

              {regularQuestions.map((q, index) => (
                <motion.div key={q.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 * index, duration: 0.3 }}>
                  <HoraryQuestionCard question={q} />
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>

      <AnimatePresence>
        {showPurchase && (
          <HoraryPurchaseSheet onClose={() => setShowPurchase(false)} />
        )}
      </AnimatePresence>
    </div>
  )
}

