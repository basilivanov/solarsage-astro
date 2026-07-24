// ############################################################################
// AI_HEADER: MODULE_ELECTION_FORM
// ROLE: Form component for selecting elective categories, subcategories, and date windows
// ############################################################################

"use client"

import { useState } from "react"
import { Sparkles } from "lucide-react"
import { ELECTION_CATEGORIES } from "@/lib/contracts/election"

type Props = {
  onSubmit: (params: {
    eventType: string
    windowFrom: string
    windowTo: string
  }) => void
  disabled?: boolean
  disabledReason?: string
}

function formatDateISO(d: Date): string {
  return d.toISOString().split("T")[0]
}

export function ElectionForm({ onSubmit, disabled = false, disabledReason }: Props) {
  const [selectedCatKey, setSelectedCatKey] = useState<string | null>(null)
  const [selectedSubKey, setSelectedSubKey] = useState<string | null>(null)
  const [customText, setCustomText] = useState("")

  const [preset, setPreset] = useState<"7d" | "14d" | "30d" | "custom">("14d")

  const today = new Date()
  const todayStr = formatDateISO(today)
  const defaultTo14 = formatDateISO(new Date(today.getTime() + 14 * 86400000))

  const [windowFrom, setWindowFrom] = useState(todayStr)
  const [windowTo, setWindowTo] = useState(defaultTo14)
  const [dateError, setDateError] = useState<string | null>(null)

  const activeCategory = ELECTION_CATEGORIES.find((c) => c.key === selectedCatKey)

  const handleCategorySelect = (catKey: string) => {
    setSelectedCatKey(catKey)
    setSelectedSubKey(null)
    setCustomText("")
  }

  const handleSubSelect = (subKey: string, subLabel: string) => {
    setSelectedSubKey(subKey)
    setCustomText(subLabel)
  }

  const handlePresetChange = (p: "7d" | "14d" | "30d" | "custom") => {
    setPreset(p)
    setDateError(null)
    const now = new Date()
    const fromStr = formatDateISO(now)
    setWindowFrom(fromStr)

    if (p === "7d") {
      setWindowTo(formatDateISO(new Date(now.getTime() + 7 * 86400000)))
    } else if (p === "14d") {
      setWindowTo(formatDateISO(new Date(now.getTime() + 14 * 86400000)))
    } else if (p === "30d") {
      setWindowTo(formatDateISO(new Date(now.getTime() + 30 * 86400000)))
    }
  }

  const validateDates = (from: string, to: string): boolean => {
    if (!from || !to) {
      setDateError("Укажите обе даты")
      return false
    }
    const dFrom = new Date(from)
    const dTo = new Date(to)
    if (dTo < dFrom) {
      setDateError("Дата окончания должна быть не раньше даты начала")
      return false
    }
    const diffDays = Math.round((dTo.getTime() - dFrom.getTime()) / 86400000)
    if (diffDays > 62) {
      setDateError("Максимальный интервал подбора — 62 дня")
      return false
    }
    setDateError(null)
    return true
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedSubKey && !customText.trim()) return
    if (!validateDates(windowFrom, windowTo)) return

    const eventType = selectedCatKey && selectedSubKey
      ? `${selectedCatKey}:${selectedSubKey}`
      : selectedSubKey || "relations:date"

    onSubmit({
      eventType,
      windowFrom,
      windowTo,
    })
  }

  const hasSelection = Boolean(selectedSubKey || customText.trim())
  const canSubmit = hasSelection && !disabled && !dateError

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-6 rounded-2xl border border-border/70 bg-card p-6 shadow-sm"
      data-testid="election-form"
    >
      <div>
        <h2 className="font-serif text-[22px] font-bold text-foreground">
          Лучшие дни по звёздам
        </h2>
        <p className="text-[13px] text-muted-foreground mt-1">
          Выбери событие и интервал — рассчитем подлинное астрологическое окно
        </p>
      </div>

      {/* 6 Base Categories 2x3 grid */}
      <div className="flex flex-col gap-3">
        <label className="text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
          1. Категория события
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5" data-testid="election-categories-grid">
          {ELECTION_CATEGORIES.map((cat) => {
            const isSelected = selectedCatKey === cat.key
            return (
              <button
                key={cat.key}
                type="button"
                onClick={() => handleCategorySelect(cat.key)}
                data-testid={`election-category-card-${cat.key}`}
                data-state={isSelected ? "selected" : "unselected"}
                className={`flex flex-col items-start gap-1 rounded-2xl border p-4 text-left transition active:scale-[0.98] ${
                  isSelected
                    ? "border-primary bg-primary/10 text-foreground shadow-sm"
                    : "border-border/70 bg-card text-foreground hover:border-border"
                }`}
              >
                <span className="text-[22px]">{cat.emoji}</span>
                <span className="text-[14px] font-medium mt-1">{cat.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Subcategories Chips (if category selected) */}
      {activeCategory && (
        <div className="flex flex-col gap-2.5 animate-in fade-in slide-in-from-top-2" data-testid="election-subcategories">
          <label className="text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
            Уточните цель
          </label>
          <div className="flex flex-wrap gap-2">
            {activeCategory.subs.map((sub) => {
              const isSubSelected = selectedSubKey === sub.key
              return (
                <button
                  key={sub.key}
                  type="button"
                  onClick={() => handleSubSelect(sub.key, sub.label)}
                  data-testid={`election-sub-chip-${sub.key}`}
                  data-state={isSubSelected ? "selected" : "unselected"}
                  className={`rounded-full border px-4 py-2 text-[13px] font-medium transition active:scale-[0.98] ${
                    isSubSelected
                      ? "border-primary bg-primary text-primary-foreground shadow-sm"
                      : "border-border/70 bg-card text-foreground hover:border-border"
                  }`}
                >
                  {sub.label}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Editable Request Field */}
      <div className="flex flex-col gap-1.5">
        <label className="text-[12px] font-medium text-muted-foreground">
          Свой запрос (можно править)
        </label>
        <input
          type="text"
          value={customText}
          onChange={(e) => {
            setCustomText(e.target.value)
            if (selectedSubKey) setSelectedSubKey(null)
          }}
          placeholder="Например, Свидание или Свадьба"
          data-testid="election-custom-input"
          className="w-full rounded-xl border border-border/70 bg-background px-4 py-2.5 text-[14px] text-foreground focus:border-primary focus:outline-none"
        />
      </div>

      {/* Date Window Segmented Control */}
      <div className="flex flex-col gap-3">
        <label className="text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
          2. Интервал подбора
        </label>

        <div className="flex gap-2">
          {[
            { id: "7d", label: "Неделя" },
            { id: "14d", label: "2 недели" },
            { id: "30d", label: "Месяц" },
            { id: "custom", label: "Свои" },
          ].map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => handlePresetChange(p.id as any)}
              data-testid={`election-preset-${p.id}`}
              className={`flex-1 rounded-xl border py-2.5 text-[13px] font-medium transition active:scale-[0.98] ${
                preset === p.id
                  ? "border-primary bg-primary/10 text-primary font-semibold"
                  : "border-border/70 bg-card text-muted-foreground hover:text-foreground"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {preset === "custom" && (
          <div className="grid grid-cols-2 gap-3 mt-1" data-testid="election-custom-dates">
            <div>
              <label className="block text-[11px] text-muted-foreground mb-1">С даты</label>
              <input
                type="date"
                value={windowFrom}
                onChange={(e) => {
                  setWindowFrom(e.target.value)
                  validateDates(e.target.value, windowTo)
                }}
                className="w-full rounded-xl border border-border/70 bg-background px-3 py-2 text-[13px] text-foreground focus:border-primary focus:outline-none"
                data-testid="election-date-from"
              />
            </div>
            <div>
              <label className="block text-[11px] text-muted-foreground mb-1">По дату</label>
              <input
                type="date"
                value={windowTo}
                onChange={(e) => {
                  setWindowTo(e.target.value)
                  validateDates(windowFrom, e.target.value)
                }}
                className="w-full rounded-xl border border-border/70 bg-background px-3 py-2 text-[13px] text-foreground focus:border-primary focus:outline-none"
                data-testid="election-date-to"
              />
            </div>
          </div>
        )}

        {dateError && (
          <p className="text-[12px] text-destructive mt-1" role="alert" data-testid="election-date-error">
            {dateError}
          </p>
        )}
      </div>

      {disabledReason && (
        <p className="text-[12.5px] text-destructive text-center" role="alert">
          {disabledReason}
        </p>
      )}

      {/* Submit CTA */}
      <button
        type="submit"
        disabled={!canSubmit}
        aria-disabled={!canSubmit}
        data-testid="election-submit-btn"
        className="inline-flex h-12 items-center justify-center gap-2 rounded-full bg-primary px-6 text-[14px] font-semibold text-primary-foreground transition active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Sparkles className="h-4 w-4" />
        Подобрать даты ✨
      </button>
    </form>
  )
}
