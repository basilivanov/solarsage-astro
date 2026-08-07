// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_CHECKIN_SCREEN
// ROLE: Main evening checkin screen component
// DEPENDENCIES: react, lucide-react, lib/api/checkin, lib/contracts/checkin
// GRACE_ANCHORS: [CHECKIN_SCREEN_COMPONENT]
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################

// START_MODULE_CONTRACT: M-COMPONENTS-CHECKIN-SCREEN
// purpose: Render multi-step evening checkin form (mood, energy, accuracy, tags, observed spheres, notes) and snapshot recap.
// owns:
//   - components/checkin/checkin-screen.tsx
// inputs: targetDate and onComplete
// outputs: CheckinScreen React component
// dependencies: createCheckin, getYesterdayCheckin, lib/contracts/checkin, generated YesterdayCheckinResponse.
// side_effects: calls checkin API
// emitted_logs: none
// failure_policy: displays error alert and allows retry
// END_MODULE_CONTRACT: M-COMPONENTS-CHECKIN-SCREEN

// START_MODULE_MAP: M-COMPONENTS-CHECKIN-SCREEN
// public_entrypoints:
//   - CheckinScreen
// semantic_blocks:
//   - CHECKIN_SCREEN_COMPONENT: main checkin screen component
// owned_tests:
//   - __tests__/components/CheckinScreen.test.tsx
// END_MODULE_MAP: M-COMPONENTS-CHECKIN-SCREEN

"use client"

import { useEffect, useState } from "react"
import { Check } from "lucide-react"

import { useToast } from "@/hooks/use-toast"
import { createCheckin, getYesterdayCheckin } from "@/lib/api/checkin"
import type { CheckinResponse, YesterdayCheckinResponse } from "@/packages/contracts"
import type {
  CheckinAccuracy,
  CheckinEnergy,
  CheckinMood,
} from "@/lib/contracts/checkin"
import { CANONICAL_PRODUCT_ORDER, type ProductSphereKey } from "@/lib/display/sphere-labels"
import { getTodaySphereLabel } from "@/components/today-convergence/today-formatters"

import { AccuracySelector } from "./accuracy-selector"
import { CheckinTags } from "./checkin-tags"
import { EnergySelector } from "./energy-selector"
import { MoodSelector } from "./mood-selector"

type Step = "mood" | "energy" | "accuracy"

type Props = {
  targetDate: string
  onComplete?: (result: CheckinResponse) => void
}

const MILESTONES = [3, 7, 14, 30]

function pluralDays(n: number): string {
  const abs = Math.abs(n) % 100
  const last = abs % 10
  if (abs >= 11 && abs <= 19) return "дней"
  if (last === 1) return "день"
  if (last >= 2 && last <= 4) return "дня"
  return "дней"
}

const TONE_LABELS: Record<"steady" | "supportive" | "mixed" | "tense", string> = {
  steady: "ровный",
  supportive: "поддерживающий",
  mixed: "смешанный",
  tense: "напряжённый",
}

function ForecastRecap({ recap }: { recap: YesterdayCheckinResponse["forecastRecap"] }) {
  if (!recap) return null

  return (
    <section
      data-testid="yesterday-forecast-recap"
      className="rounded-2xl border border-border/60 bg-card/70 p-4 text-left shadow-sm"
    >
      <h3 className="text-[13px] font-medium text-foreground">Что было в прогнозе</h3>
      <p className="mt-2 text-[13px] text-muted-foreground">
        {recap.sphereKeys.map((key) => getTodaySphereLabel(key)).join(" · ") || "Без выделенной сферы"}
      </p>
      <p className="mt-1 text-[13px] text-muted-foreground">Тон: {TONE_LABELS[recap.dayTone]}</p>
    </section>
  )
}

// START_BLOCK: OBSERVED_SPHERES
function ObservedSpheresField({
  selected,
  onChange,
}: {
  selected: ProductSphereKey[]
  onChange: (next: ProductSphereKey[]) => void
}) {
  return (
    <fieldset data-testid="observed-spheres" className="space-y-3">
      <legend className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Какие сферы были заметны? <span className="normal-case tracking-normal">необязательно</span>
      </legend>
      <div className="grid grid-cols-2 gap-2">
        {CANONICAL_PRODUCT_ORDER.map((sphere) => {
          const isSelected = selected.includes(sphere.key)
          return (
            <label
              key={sphere.key}
              className="flex min-h-[44px] cursor-pointer items-center gap-2 rounded-xl border border-border/70 bg-card px-3 text-[12px] text-foreground transition hover:border-primary/50 focus-within:border-primary/60 focus-within:ring-2 focus-within:ring-primary/15 motion-reduce:transition-none"
            >
              <input
                type="checkbox"
                data-testid={`observed-sphere-${sphere.key}`}
                checked={isSelected}
                onChange={() => {
                  onChange(
                    isSelected
                      ? selected.filter((key) => key !== sphere.key)
                      : [...selected, sphere.key],
                  )
                }}
              />
              <span>{sphere.label}</span>
            </label>
          )
        })}
      </div>
    </fieldset>
  )
}
// END_BLOCK: OBSERVED_SPHERES

// START_BLOCK: CHECKIN_SCREEN_COMPONENT
export function CheckinScreen({
  targetDate,
  onComplete,
}: Props) {
  const [step, setStep] = useState<Step>("mood")
  const [mood, setMood] = useState<CheckinMood | null>(null)
  const [energy, setEnergy] = useState<CheckinEnergy | null>(null)
  const [accuracy, setAccuracy] = useState<CheckinAccuracy | null>(null)
  const [tags, setTags] = useState<string[]>([])
  const [note, setNote] = useState("")
  const [showDetails, setShowDetails] = useState(false)
  const [existing, setExisting] = useState<CheckinResponse | null>(null)
  const [yesterday, setYesterday] = useState<YesterdayCheckinResponse | null>(null)
  const [observedSpheres, setObservedSpheres] = useState<ProductSphereKey[]>([])
  const [submittedResult, setSubmittedResult] = useState<CheckinResponse | null>(null)
  const [loadingExisting, setLoadingExisting] = useState(true)
  const [readError, setReadError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    let active = true
    setLoadingExisting(true)
    setReadError(null)
    setExisting(null)
    setSubmittedResult(null)
    setEditing(false)

    getYesterdayCheckin()
      .then((yesterdayResponse) => {
        if (!active) return
        setYesterday(yesterdayResponse)
        const value = yesterdayResponse.checkin
        setExisting(value)
        if (value) {
          setMood(value.mood as CheckinMood)
          setEnergy((value.energy ?? null) as CheckinEnergy | null)
          setAccuracy((value.accuracy ?? null) as CheckinAccuracy | null)
          setTags(value.tags)
          setNote(value.note ?? "")
          setObservedSpheres(value.observedSpheres ?? [])
        } else {
          setMood(null)
          setEnergy(null)
          setAccuracy(null)
          setTags([])
          setNote("")
          setObservedSpheres([])
        }
      })
      .catch((reason: unknown) => {
        if (!active) return
        setReadError(
          reason instanceof Error ? reason.message : "Не удалось загрузить оценку",
        )
      })
      .finally(() => {
        if (active) setLoadingExisting(false)
      })

    return () => {
      active = false
    }
  }, [targetDate])

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
        ...(observedSpheres.length
          ? {
              observedSpheres,
            }
          : {}),
      })
      setExisting(result)
      setSubmittedResult(result)
      setEditing(false)
      try {
        const refreshed = await getYesterdayCheckin()
        setYesterday(refreshed)
        if (refreshed.checkin) {
          setExisting(refreshed.checkin)
          setSubmittedResult(refreshed.checkin)
        }
      } catch {
        // The saved check-in remains visible if the recap refresh is unavailable.
      }
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

  const streak = submittedResult?.streak || 1
  const hitMilestone = MILESTONES.includes(streak)
  const nextMilestone = MILESTONES.find((m) => m > streak)

  return (
    <div
      className="mx-auto w-full max-w-[640px] px-5 pb-10 pt-8"
      data-testid="checkin-screen"
      data-state={loadingExisting ? "loading" : readError ? "error" : "ready"}
      aria-busy={loadingExisting || loading ? true : undefined}
    >
      {loadingExisting ? (
        <p role="status" className="text-[13px] text-muted-foreground">
          Загружаем оценку...
        </p>
      ) : null}

      {!loadingExisting && readError ? (
        <section role="alert">
          <h2 className="font-serif text-[22px] leading-tight text-foreground">
            Не удалось загрузить оценку
          </h2>
          <p className="mt-3 text-[13px] text-muted-foreground">{readError}</p>
        </section>
      ) : null}

      {/* Post-submit confirmation screen */}
      {!loadingExisting && !readError && submittedResult ? (
        <section className="space-y-6 py-4 text-center" data-testid="checkin-post-submit" data-state="submitted">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[#eaf5f0] text-[#43806d] dark:bg-[#1c2b25] dark:text-[#63a893]">
            <Check className="h-8 w-8" />
          </div>

          <div className="space-y-1">
            <span className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-[#795a86]">
              ОТВЕТ ЗАСЧИТАН
            </span>
            <h2 className="syn-serif text-[26px] font-medium text-[#3e3347] dark:text-[#f1e9f4]">
              Спасибо за отклик!
            </h2>
          </div>

          <div className="space-y-2 rounded-[22px] border border-border/60 bg-card p-5 shadow-sm">
            <div className="flex items-center justify-center gap-2 text-[32px] font-bold text-foreground">
              <span>🔥</span>
              <span>{streak} {pluralDays(streak)} подряд</span>
            </div>
            <p className="m-0 text-[13px] text-muted-foreground">
              {hitMilestone
                ? `Рубеж в ${streak} ${pluralDays(streak)} достигнут! 🎉`
                : nextMilestone
                ? `До рубежа в ${nextMilestone} ${pluralDays(nextMilestone)} — ещё ${nextMilestone - streak} ${pluralDays(nextMilestone - streak)}`
                : "Отличная регулярность!"}
            </p>
          </div>

          <ForecastRecap recap={yesterday?.forecastRecap ?? null} />

          <button
            type="button"
            data-testid="checkin-done-btn"
            onClick={() => {
              onComplete?.(submittedResult)
            }}
            className="flex h-[50px] w-full items-center justify-center rounded-[17px] bg-foreground text-[16px] font-[760] text-background transition active:scale-[0.99] motion-reduce:transition-none motion-reduce:active:scale-100"
          >
            Понятно
          </button>
        </section>
      ) : null}

      {!loadingExisting && !readError && !submittedResult && existing && !editing ? (
        <section className="rounded-2xl border border-border/70 bg-card p-4">
          <h2 className="font-serif text-[22px] leading-tight text-foreground">
            Оценка уже сохранена
          </h2>
          <div className="mt-3 space-y-1 text-[13px] text-muted-foreground">
            <p>Настроение: {existing.mood} / 5</p>
            {existing.energy ? <p>Энергия: {existing.energy} / 5</p> : null}
            {existing.accuracy ? <p>Точность: {existing.accuracy} / 3</p> : null}
            {existing.note ? <p className="text-foreground">{existing.note}</p> : null}
          </div>
          <div className="mt-4">
            <ForecastRecap recap={yesterday?.forecastRecap ?? null} />
          </div>
          <button
            type="button"
            onClick={() => {
              setEditing(true)
              setStep("mood")
            }}
            className="mt-4 rounded-full bg-foreground px-4 py-2 text-[12px] font-medium text-background"
          >
            Изменить
          </button>
        </section>
      ) : null}

      {!loadingExisting && !readError && !submittedResult && (!existing || editing) ? (
        <>
          <ObservedSpheresField selected={observedSpheres} onChange={setObservedSpheres} />
          {step === "mood" ? (
            <section>
              <h2 className="font-serif text-[24px] leading-tight text-foreground">
                Как прошёл день?
              </h2>
              {yesterday?.forecastAvailable ? (
                <p
                  data-testid="yesterday-forecast-available"
                  className="mt-2 text-[13px] text-muted-foreground"
                >
                  Прогноз за этот день сохранён
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
        </>
      ) : null}
    </div>
  )
}
// END_BLOCK: CHECKIN_SCREEN_COMPONENT
