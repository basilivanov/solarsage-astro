"use client"

import { useState, useEffect, useCallback } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { ChevronLeft, MessageSquare, AlertCircle } from "lucide-react"

import type { HoraryQuestion, HoraryQuota, HoraryCategory } from "@/lib/contracts/horary"
import { getHoraryQuota, listHoraryQuestions, createHoraryQuestion, getHoraryQuestion } from "@/lib/api/horary"
import { getProfile } from "@/lib/api/profile"
import type { ProfileRead } from "@/packages/contracts"
import { useToast } from "@/hooks/use-toast"

import { HoraryQuotaBar } from "./horary-quota-bar"
import { HoraryForm } from "./horary-form"
import { HoraryQuestionCard } from "./horary-question-card"
import { HoraryProgress } from "./horary-progress"
import { HoraryPurchaseSheet } from "./horary-purchase-sheet"
import { Spinner } from "@/components/ui/spinner"

export function HoraryScreen() {
  const router = useRouter()
  const { toast } = useToast()
  
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [showPurchase, setShowPurchase] = useState(false)
  
  const [quota, setQuota] = useState<HoraryQuota | null>(null)
  const [questions, setQuestions] = useState<HoraryQuestion[]>([])
  const [profile, setProfile] = useState<ProfileRead | null>(null)

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
      console.error("[HoraryScreen] Failed to load data:", error)
      toast({
        variant: "destructive",
        description: "Не удалось загрузить данные хорара",
      })
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    loadData()
  }, [loadData])

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

      // Start polling status
      pollStatus(q.id)
    } catch (error: any) {
      console.error("[HoraryScreen] Failed to submit:", error)
      setSubmitting(false)
      toast({
        variant: "destructive",
        description: error.message || "Не удалось отправить вопрос",
      })
    }
  }

  const pollStatus = (id: string) => {
    const startTime = Date.now()
    const interval = setInterval(async () => {
      // 30 seconds timeout
      if (Date.now() - startTime > 30000) {
        clearInterval(interval)
        setSubmitting(false)
        toast({
          description: "Ответ формируется дольше обычного. Мы покажем его, когда он будет готов.",
        })
        loadData()
        return
      }

      try {
        const q = await getHoraryQuestion(id)
        if (q.status === "answered") {
          clearInterval(interval)
          router.push(`/readings/horary/${id}`)
        } else if (q.status === "failed") {
          clearInterval(interval)
          setSubmitting(false)
          toast({
            variant: "destructive",
            description: "Не удалось рассчитать хорарный ответ. Пожалуйста, попробуйте снова.",
          })
          loadData()
        }
      } catch (error) {
        console.error("[HoraryScreen] Polling error:", error)
      }
    }, 2000)
  }

  if (loading) {
    return (
      <div className="flex h-[80dvh] items-center justify-center">
        <Spinner className="h-8 w-8 text-primary" />
      </div>
    )
  }

  if (submitting) {
    return <HoraryProgress />
  }

  const hasSpendableCredit = quota
    ? (quota.weeklyFreeAvailable || quota.bonusCredits > 0 || quota.paidCredits > 0)
    : false

  return (
    <div className="flex h-full w-full flex-col bg-background overflow-y-auto">
      {/* Header */}
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
        <div className="space-y-1">
          <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Раздел
          </span>
          <h2 className="font-serif text-[28px] font-bold leading-tight tracking-tight text-foreground">
            Хорарный оракул
          </h2>
          <p className="text-[14px] leading-relaxed text-muted-foreground">
            Задай конкретный вопрос звёздам и получи мгновенный ответ «да / нет» с астрологическим обоснованием на момент вопроса.
          </p>
        </div>

        {/* Quota Bar */}
        {quota && (
          <HoraryQuotaBar quota={quota} onBuy={() => setShowPurchase(true)} />
        )}

        {/* Form to submit question if we have spendable credits */}
        {hasSpendableCredit ? (
          <div className="border-t border-border/40 pt-5">
            <HoraryForm
              hasSpendableCredit={hasSpendableCredit}
              profileCurrentCity={profile?.currentLocation?.city}
              profileCurrentLat={profile?.currentLocation?.lat}
              profileCurrentLon={profile?.currentLocation?.lon}
              profileBirthCity={profile?.birth?.birthCity}
              profileBirthLat={profile?.birth?.birthLat}
              profileBirthLon={profile?.birth?.birthLon}
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

        {/* List of past questions */}
        <div className="border-t border-border/40 pt-5 space-y-4">
          <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            История вопросов
          </h3>
          
          {questions.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border/70 p-8 text-center text-muted-foreground text-[14px] space-y-2">
              <MessageSquare className="h-8 w-8 mx-auto text-muted-foreground/45" />
              <p>Вы еще не задавали хорарных вопросов.</p>
              <p className="text-[12px]">Ваш первый вердикт появится здесь.</p>
            </div>
          ) : (
            <div className="grid gap-3.5">
              {questions.map((q) => (
                <HoraryQuestionCard key={q.id} question={q} />
              ))}
            </div>
          )}
        </div>
      </div>

      {showPurchase && (
        <HoraryPurchaseSheet onClose={() => setShowPurchase(false)} />
      )}
    </div>
  )
}
