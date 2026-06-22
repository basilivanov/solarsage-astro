// ############################################################################
// AI_HEADER: MODULE_CHECKIN_SCREEN
// ROLE: UI component — full checkin screen (mood → accuracy → details)
// DEPENDENCIES: react, @/lib/api/checkin, @/lib/contracts/checkin
// GRACE_ANCHORS: []
// SLICE: SLICE-CHECKIN
// WAVE: W-8.1
// ############################################################################

"use client"

import { useState } from "react"
import { MoodSelector } from "./mood-selector"
import { EnergySelector } from "./energy-selector"
import { AccuracySelector } from "./accuracy-selector"
import { CheckinTags } from "./checkin-tags"
import { createCheckin, type CheckinResult } from "@/lib/api/checkin"
import { useToast } from "@/hooks/use-toast"

type Props = {
  targetDate: string
  dayStatusHint?: string
  onComplete?: (_result: CheckinResult) => void
}

export function CheckinScreen({ targetDate, dayStatusHint, onComplete }: Props) {
  const [step, setStep] = useState<"mood" | "energy" | "accuracy" | "details">("mood")
  const [mood, setMood] = useState<number | null>(null)
  const [energy, setEnergy] = useState<number | null>(null)
  const [accuracy, setAccuracy] = useState<string | null>(null)
  const [tags, setTags] = useState<string[]>([])
  const [note, setNote] = useState("")
  const [showDetails, setShowDetails] = useState(false)
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  const handleMoodSelect = (m: number) => {
    setMood(m)
    setStep("energy")
  }

  const handleEnergySelect = (en: number) => {
    setEnergy(en)
    setStep("accuracy")
  }

  const handleAccuracySelect = (a: string) => {
    setAccuracy(a)
    // Submit immediately after accuracy (3-tap minimum)
    handleSubmit(mood!, energy ?? null, a)
  }

  const handleSubmit = async (m: number, en: number | null, a: string | null) => {
    setLoading(true)
    try {
      const result = await createCheckin({
        targetDate,
        mood: m,
        energy: en,
        accuracy: a,
        tags: tags.length > 0 ? tags : null,
        note: note || null,
      })
      toast({
        description: `Спасибо! Streak: ${result.streak} ${result.streak >= 7 ? "🔥" : ""} дней подряд`,
      })
      onComplete?.(result)
    } catch (err) {
      toast({
        description: err instanceof Error ? err.message : "Ошибка",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitWithDetails = async () => {
    if (!mood) return
    setLoading(true)
    try {
      const result = await createCheckin({
        targetDate,
        mood,
        energy,
        accuracy,
        tags: tags.length > 0 ? tags : null,
        note: note || null,
      })
      toast({ description: `Готово! 🔥 ${result.streak} дней подряд` })
      onComplete?.(result)
    } catch (err) {
      toast({
        description: err instanceof Error ? err.message : "Ошибка",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-md px-5 py-8" data-testid="checkin-screen">
      {/* Mood step */}
      {step === "mood" && (
        <div>
          <h2 className="font-serif text-[22px] leading-tight text-foreground">
            🌙 Как прошёл день?
          </h2>
          {dayStatusHint && (
            <p className="mt-1.5 text-[13px] text-muted-foreground">
              Мы говорили: {dayStatusHint}
            </p>
          )}
          <div className="mt-6">
            <MoodSelector value={mood} onChange={handleMoodSelect} />
          </div>
        </div>
      )}

      {/* Energy step */}
      {step === "energy" && (
        <div>
          <h2 className="font-serif text-[22px] leading-tight text-foreground">
            🔋 Сколько энергии осталось?
          </h2>
          <p className="mt-1.5 text-[13px] text-muted-foreground">
            Оцени свой ресурс на конец дня
          </p>
          <div className="mt-6">
            <EnergySelector value={energy} onChange={handleEnergySelect} />
          </div>
          <button
            type="button"
            onClick={() => setStep("accuracy")}
            className="mt-4 text-[13px] text-muted-foreground underline"
          >
            Пропустить ▸
          </button>
        </div>
      )}

      {/* Accuracy step */}
      {step === "accuracy" && (
        <div>
          <h2 className="font-serif text-[22px] leading-tight text-foreground">
            Прогноз попал?
          </h2>
          <div className="mt-6">
            <AccuracySelector value={accuracy} onChange={handleAccuracySelect} />
          </div>
          <button
            type="button"
            onClick={() => setShowDetails(true)}
            className="mt-4 text-[13px] text-muted-foreground underline"
          >
            Добавить детали ▾
          </button>
        </div>
      )}

      {/* Details (optional, expands) */}
      {showDetails && (
        <div className="mt-6 space-y-4">
          <div>
            <div className="text-[12px] font-medium uppercase tracking-wide text-muted-foreground">
              Что подтвердилось?
            </div>
            <div className="mt-2">
              <CheckinTags selected={tags} onChange={setTags} />
            </div>
          </div>
          <div>
            <div className="text-[12px] font-medium uppercase tracking-wide text-muted-foreground">
              Заметка (опционально)
            </div>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={500}
              className="mt-2 w-full rounded-xl border border-border/60 bg-card p-3 text-[14px] text-foreground outline-none focus:border-primary"
              rows={3}
              placeholder="Что-то важное..."
            />
          </div>
          <button
            type="button"
            onClick={handleSubmitWithDetails}
            disabled={loading}
            className="flex h-11 w-full items-center justify-center rounded-full bg-foreground px-5 text-[14px] font-medium text-background disabled:opacity-50"
          >
            {loading ? "Сохраняем..." : "Сохранить"}
          </button>
        </div>
      )}

      {loading && step !== "details" && (
        <div className="mt-4 text-center text-[13px] text-muted-foreground">
          Сохраняем...
        </div>
      )}
    </div>
  )
}
