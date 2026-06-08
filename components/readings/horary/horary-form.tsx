"use client"

import { useState } from "react"
import { Send, Sparkles } from "lucide-react"
import { HORARY_CATEGORIES } from "@/lib/contracts/horary"
import type { HoraryCategory } from "@/lib/contracts/horary"
import { HoraryTimeConfirm } from "./horary-time-confirm"

type Props = {
  left: number
  onSubmit: (text: string, category: HoraryCategory | undefined, localTime: string, timezone: string) => void
}

export function HoraryForm({ left, onSubmit }: Props) {
  const [text, setText] = useState("")
  const [selectedCategory, setSelectedCategory] = useState<HoraryCategory | undefined>(undefined)
  const [localTime, setLocalTime] = useState("")
  const [timezone, setTimezone] = useState("")

  const activeCategoryMeta = HORARY_CATEGORIES.find((c) => c.key === selectedCategory)
  const placeholder = activeCategoryMeta?.placeholder || "Сформулируй вопрос так, чтобы на него можно было ответить Да или Нет..."

  const isValid = text.trim().length >= 5 && text.length <= 500 && left > 0

  const handleCategoryClick = (cat: HoraryCategory) => {
    if (selectedCategory === cat) {
      setSelectedCategory(undefined)
    } else {
      setSelectedCategory(cat)
      // If textarea is empty, let's prefill with example placeholder for convenience
      if (text.trim() === "") {
        const catMeta = HORARY_CATEGORIES.find((c) => c.key === cat)
        if (catMeta) setText(catMeta.placeholder)
      }
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValid) return
    onSubmit(text, selectedCategory, localTime, timezone)
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
          Твой вопрос звёздам
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

      {/* Time & Timezone Confirmation */}
      <HoraryTimeConfirm onChange={(lt, tz) => {
        setLocalTime(lt)
        setTimezone(tz)
      }} />

      {/* Submit Button */}
      <button
        type="submit"
        disabled={!isValid}
        className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-foreground px-5 text-[14px] font-medium text-background transition active:scale-[0.99] disabled:opacity-40 disabled:pointer-events-none"
      >
        <Sparkles className="h-4 w-4" />
        Спросить звёзды
      </button>
    </form>
  )
}
