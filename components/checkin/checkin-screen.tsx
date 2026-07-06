"use client"

import { useState } from "react"

import { useToast } from "@/hooks/use-toast"
import { createCheckin } from "@/lib/api/checkin"
import type { CheckinResponse } from "@/packages/contracts"
import type {
  CheckinAccuracy,
  CheckinEnergy,
  CheckinMood,
} from "@/lib/contracts/checkin"

import { AccuracySelector } from "./accuracy-selector"
import { CheckinTags } from "./checkin-tags"
import { EnergySelector } from "./energy-selector"
import { MoodSelector } from "./mood-selector"

type Step = "mood" | "energy" | "accuracy"

type Props = {
  targetDate: string
  dayStatusHint?: string
  onComplete?: (result: CheckinResponse) => void
}

export function CheckinScreen({
  targetDate,
  dayStatusHint,
  onComplete,
}: Props) {
  const [step, setStep] = useState<Step>("mood")
  const [mood, setMood] = useState<CheckinMood | null>(null)
  const [energy, setEnergy] = useState<CheckinEnergy | null>(null)
  const [accuracy, setAccuracy] = useState<CheckinAccuracy | null>(null)
  const [tags, setTags] = useState<string[]>([])
  const [note, setNote] = useState("")
  const [showDetails, setShowDetails] = useState(false)
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  const submit = async (selectedAccuracy: CheckinAccuracy | null) => {
    if (mood === null) return
    setLoading(true)
    try {
      const result = await createCheckin({
        targetDate,
        mood,
        accuracy: selectedAccuracy,
        energy,
        tags,
        note: note.trim() || null,
      })
      toast({
        description: `Сохранено. Серия: ${result.streak}`,
      })
      onComplete?.(result)
    } catch (reason) {
      toast({
        description:
          reason instanceof Error ? reason.message : "Не удалось сохранить оценку",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const selectAccuracy = (value: CheckinAccuracy) => {
    setAccuracy(value)
    if (!showDetails) {
      void submit(value)
    }
  }

  return (
    <div
      className="mx-auto w-full max-w-md px-5 pb-10 pt-8"
      data-testid="checkin-screen"
    >
      {step === "mood" ? (
        <section>
          <h2 className="font-serif text-[24px] leading-tight text-foreground">
            Как прошёл день?
          </h2>
          {dayStatusHint ? (
            <p className="mt-2 text-[13px] text-muted-foreground">
              Прогноз: {dayStatusHint}
            </p>
          ) : null}
          <div className="mt-6">
            <MoodSelector
              value={mood}
              onChange={(value) => {
                setMood(value)
                setStep("energy")
              }}
            />
          </div>
        </section>
      ) : null}

      {step === "energy" ? (
        <section>
          <h2 className="font-serif text-[24px] leading-tight text-foreground">
            Сколько энергии осталось?
          </h2>
          <p className="mt-2 text-[13px] text-muted-foreground">
            Оцени ресурс к концу дня
          </p>
          <div className="mt-6">
            <EnergySelector
              value={energy}
              onChange={(value) => {
                setEnergy(value)
                setStep("accuracy")
              }}
            />
          </div>
          <button
            type="button"
            onClick={() => setStep("accuracy")}
            className="mt-5 text-[13px] text-muted-foreground underline underline-offset-4"
          >
            Пропустить
          </button>
        </section>
      ) : null}

      {step === "accuracy" ? (
        <section>
          <h2 className="font-serif text-[24px] leading-tight text-foreground">
            Прогноз совпал?
          </h2>
          <div className="mt-6">
            <AccuracySelector value={accuracy} onChange={selectAccuracy} />
          </div>
          {!showDetails ? (
            <button
              type="button"
              onClick={() => setShowDetails(true)}
              className="mt-5 text-[13px] text-muted-foreground underline underline-offset-4"
            >
              Добавить детали
            </button>
          ) : (
            <div className="mt-7 space-y-5">
              <div>
                <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                  Что особенно запомнилось
                </div>
                <div className="mt-3">
                  <CheckinTags selected={tags} onChange={setTags} />
                </div>
              </div>
              <div>
                <label
                  htmlFor="checkin-note"
                  className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground"
                >
                  Заметка
                </label>
                <textarea
                  id="checkin-note"
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  maxLength={500}
                  rows={3}
                  placeholder="Что было важным?"
                  className="mt-3 w-full resize-none rounded-xl border border-border/70 bg-card p-3 text-[14px] text-foreground outline-none focus:border-foreground"
                />
              </div>
              <button
                type="button"
                onClick={() => void submit(accuracy)}
                disabled={loading || accuracy === null}
                className="flex h-11 w-full items-center justify-center rounded-full bg-foreground px-5 text-[14px] font-medium text-background disabled:opacity-50"
              >
                {loading ? "Сохраняем..." : "Сохранить"}
              </button>
            </div>
          )}
          {loading && !showDetails ? (
            <p className="mt-5 text-center text-[13px] text-muted-foreground">
              Сохраняем...
            </p>
          ) : null}
        </section>
      ) : null}
    </div>
  )
}
