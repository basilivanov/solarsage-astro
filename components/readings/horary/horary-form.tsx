"use client"

import { useState } from "react"
import { Sparkles } from "lucide-react"
import { HORARY_CATEGORIES } from "@/lib/contracts/horary"
import type { HoraryCategory } from "@/lib/contracts/horary"
import { HoraryTimeConfirm } from "./horary-time-confirm"

type Props = {
  hasSpendableCredit: boolean
  submitting?: boolean
  submitError?: string | null
  profileCurrentCity?: string | null
  profileCurrentLat?: number | null
  profileCurrentLon?: number | null
  profileCurrentTz?: string | null
  profileBirthCity?: string | null
  profileBirthLat?: number | null
  profileBirthLon?: number | null
  profileBirthTz?: string | null
  onSubmit: (
    text: string,
    category: HoraryCategory | undefined,
    localTime: string,
    timezone: string,
    lat?: number,
    lon?: number,
    locationName?: string
  ) => void
}


export function HoraryForm({
  hasSpendableCredit,
  submitting = false,
  submitError = null,
  profileCurrentCity,
  profileCurrentLat,
  profileCurrentLon,
  profileCurrentTz,
  profileBirthCity,
  profileBirthLat,
  profileBirthLon,
  profileBirthTz,
  onSubmit,
}: Props) {

  const [text, setText] = useState("")
  const [selectedCategory, setSelectedCategory] = useState<HoraryCategory | undefined>(undefined)
  const [localTime, setLocalTime] = useState("")
  const [timezone, setTimezone] = useState("")
  const [questionLat, setQuestionLat] = useState<number | undefined>(undefined)
  const [questionLon, setQuestionLon] = useState<number | undefined>(undefined)
  const [questionLocationName, setQuestionLocationName] = useState<string | undefined>(undefined)
  const [blockedReason, setBlockedReason] = useState<string | null>(null)
  const [shakeKey, setShakeKey] = useState(0)

  const activeCategoryMeta = HORARY_CATEGORIES.find((c) => c.key === selectedCategory)
  const placeholder = activeCategoryMeta?.placeholder || "Сформулируй вопрос так, чтобы на него можно было ответить Да или Нет..."

  const hasQuestionPlace = typeof questionLat === "number" && typeof questionLon === "number"
  const isValid = text.trim().length >= 5 && text.length <= 500 && hasSpendableCredit && hasQuestionPlace

  const handleCategoryClick = (cat: HoraryCategory) => {
    // Tapping another chip switches selection; tapping already selected chip keeps it selected (fixes 3.1)
    setSelectedCategory(cat)
    // If textarea is empty, prefill with example placeholder
    if (text.trim() === "") {
      const catMeta = HORARY_CATEGORIES.find((c) => c.key === cat)
      if (catMeta) setText(catMeta.placeholder)
    }
  }

  const handleMomentChange = (
    lt: string,
    tz: string,
    lat?: number,
    lon?: number,
    locName?: string
  ) => {
    setLocalTime(lt)
    setTimezone(tz)
    setQuestionLat(lat)
    setQuestionLon(lon)
    setQuestionLocationName(locName)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (submitting) return

    if (!isValid) {
      let reason = ""
      if (!hasSpendableCredit) {
        reason = "Нужен доступный хорарный вопрос"
      } else if (!hasQuestionPlace) {
        reason = "Укажи место вопроса"
      } else if (text.trim().length < 5) {
        reason = "Напиши вопрос (минимум 5 символов)"
      }
      setBlockedReason(reason)
      setShakeKey((k) => k + 1)
      setTimeout(() => setBlockedReason(null), 4000)
      return
    }

    setBlockedReason(null)
    onSubmit(
      text,
      selectedCategory,
      localTime,
      timezone,
      questionLat,
      questionLon,
      questionLocationName
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Category Selection */}
      <div className="space-y-2.5">
        <label className="block text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Категория вопроса
        </label>
        <div className="flex flex-wrap gap-2">
          {HORARY_CATEGORIES.map((cat) => {
            const isSelected = selectedCategory === cat.key
            return (
              <button
                key={cat.key}
                type="button"
                onClick={() => handleCategoryClick(cat.key)}
                className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 font-sans text-[13px] transition active:scale-95 ${
                  isSelected
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border/70 bg-card text-foreground/75 hover:bg-foreground/[0.02]"
                }`}
              >
                <span>{cat.emoji}</span>
                <span>{cat.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Text Area */}
      <div className="space-y-2">
        <label className="block text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Твой вопрос
        </label>
        <div className="relative">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={placeholder}
            maxLength={500}
            rows={4}
            className="w-full rounded-2xl border border-border/70 bg-card p-4 font-serif text-[16px] text-foreground placeholder:text-foreground/30 focus:border-accent focus:outline-none resize-none"
          />
          <div className="absolute bottom-3 right-3 text-[11px] text-muted-foreground/60">
            {text.length}/500
          </div>
        </div>
      </div>

      {/* Time & Location Confirmation */}
      <HoraryTimeConfirm
        profileCurrentCity={profileCurrentCity}
        profileCurrentLat={profileCurrentLat}
        profileCurrentLon={profileCurrentLon}
        profileCurrentTz={profileCurrentTz}
        profileBirthCity={profileBirthCity}
        profileBirthLat={profileBirthLat}
        profileBirthLon={profileBirthLon}
        profileBirthTz={profileBirthTz}
        onChange={handleMomentChange}
      />

      {/* Blocked reason */}
      {blockedReason && (
        <div
          key={shakeKey}
          className="rounded-xl bg-destructive/10 border border-destructive/20 p-3 text-[13px] text-destructive/90 animate-in slide-in-from-top-1"
          data-testid="horary-blocked-reason"
        >
          {blockedReason}
        </div>
      )}

      {/* Submit error from API */}
      {submitError && (
        <div
          className="rounded-xl bg-destructive/10 border border-destructive/20 p-3 text-[13px] text-destructive/90"
          data-testid="horary-submit-error"
        >
          {submitError}
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        className={`flex h-12 w-full items-center justify-center gap-2 rounded-full bg-foreground px-5 text-[14px] font-medium text-background transition active:scale-[0.99] ${
          !isValid || submitting
            ? "opacity-40 cursor-not-allowed"
            : "hover:opacity-90"
        }`}
      >
        <Sparkles className="h-4 w-4" />
        {submitting ? "Считаем карту..." : "Получить ответ карты"}
      </button>

      {!isValid && (
        <div className="space-y-1 px-1">
          {text.trim().length > 0 && text.trim().length < 5 && (
            <p className="text-[12.5px] text-muted-foreground">
              Вопрос должен быть минимум 5 символов.
            </p>
          )}
          {!hasQuestionPlace && (
            <p className="text-[12.5px] text-muted-foreground">
              Укажи место вопроса.
            </p>
          )}
          {!hasSpendableCredit && (
            <p className="text-[12.5px] text-muted-foreground">
              Нужен хорарный вопрос на балансе.
            </p>
          )}
        </div>
      )}

    </form>
  )
}
