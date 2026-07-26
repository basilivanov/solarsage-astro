// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_ADD_SHEET
// ROLE: Modal bottom sheet for adding a new synastry partner
// DEPENDENCIES: react, lucide-react, lib/api/synastry
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-ADD-SHEET
// purpose: Modal sheet for adding a partner with name, birth data, and approximate time toggle.
// owns:
//   - components/synastry/synastry-add-sheet.tsx
// inputs: open, onClose, onSuccess
// outputs: SynastryAddSheet TSX render
// dependencies: lib/api/synastry
// side_effects: calls createSynastryPartner API endpoint on submit
// emitted_logs: none
// failure_policy: inline error with role=alert, sheet stays open
// END_MODULE_CONTRACT: M-SYNASTRY-ADD-SHEET

// START_MODULE_MAP: M-SYNASTRY-ADD-SHEET
// public_entrypoints:
//   - SynastryAddSheet
// semantic_blocks:
//   - SYNASTRY_ADD_SHEET: Add partner modal form component
// owned_tests: none
// END_MODULE_MAP: M-SYNASTRY-ADD-SHEET

"use client"

import { useState } from "react"
import { X, AlertCircle, Info } from "lucide-react"
import { createSynastryPartner, type PartnerCreatePayload } from "@/lib/api/synastry"
import { CityPicker } from "@/components/onboarding/city-picker"
import type { City } from "@/lib/contracts/city"
import { formatCity } from "@/lib/contracts/city"

type Props = {
  open: boolean
  onClose: () => void
  onSuccess: (partnerId: string) => void
}

// START_BLOCK: SYNASTRY_ADD_SHEET
export function SynastryAddSheet({ open, onClose, onSuccess }: Props) {
  const [name, setName] = useState("")
  const [relation, setRelation] = useState("romantic")
  const [birthDate, setBirthDate] = useState("")
  const [birthTime, setBirthTime] = useState("")
  const [city, setCity] = useState<City | null>(null)
  const [unknownTime, setUnknownTime] = useState(false)
  const [savedTime, setSavedTime] = useState("")

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!open) return null

  function handleToggleUnknownTime() {
    if (!unknownTime) {
      setSavedTime(birthTime)
      setBirthTime("")
      setUnknownTime(true)
    } else {
      setBirthTime(savedTime)
      setUnknownTime(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError("Пожалуйста, введите имя человека.")
      return
    }

    if (!birthDate) {
      setError("Пожалуйста, укажите дату рождения.")
      return
    }

    setLoading(true)
    try {
      const payload: PartnerCreatePayload = {
        name: name.trim(),
        relation,
        birthDate,
        birthTime: unknownTime ? null : (birthTime || null),
        birthCity: city ? formatCity(city) : null,
        birthLat: city ? (city.lat ?? null) : null,
        birthLon: city ? (city.lon ?? null) : null,
        birthTz: city ? (city.timezone ?? null) : null,
        birthTimePrecision: unknownTime ? "approximate" : "exact",
      }

      const res = await createSynastryPartner(payload)
      onSuccess(res.partnerId)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось добавить партнёра.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-0 sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="synastry-add-title"
      data-testid="synastry-add-sheet"
    >
      <div className="relative w-full max-w-md max-h-[92dvh] overflow-y-auto rounded-t-[28px] sm:rounded-[28px] border border-border/70 bg-card p-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] shadow-2xl space-y-5">
        {/* Grabber bar */}
        <div className="mx-auto h-1.5 w-12 rounded-full bg-muted-foreground/30 flex-none sm:hidden" />

        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/50 pb-3">
          <div>
            <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              НОВОЕ СРАВНЕНИЕ
            </span>
            <h2 id="synastry-add-title" className="font-serif text-[22px] font-semibold text-foreground">
              Добавить человека
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Закрыть"
            className="flex h-8 w-8 items-center justify-center rounded-full bg-muted/60 text-muted-foreground hover:text-foreground active:scale-95"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="rounded-2xl border border-destructive/20 bg-destructive/10 p-3 flex items-center gap-2 text-[13px] text-destructive" role="alert">
            <AlertCircle className="h-4 w-4 flex-none" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div className="space-y-1">
            <label htmlFor="partner-name" className="block text-[12px] font-medium text-muted-foreground uppercase tracking-wider">
              Имя или как назвать
            </label>
            <input
              id="partner-name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например: Максим"
              className="w-full rounded-xl border border-border/70 bg-background px-3.5 py-2.5 text-[14px] text-foreground focus:border-primary focus:outline-none"
            />
          </div>

          {/* Relation type */}
          <div className="space-y-1">
            <label htmlFor="partner-relation" className="block text-[12px] font-medium text-muted-foreground uppercase tracking-wider">
              Тип связи
            </label>
            <select
              id="partner-relation"
              value={relation}
              onChange={(e) => setRelation(e.target.value)}
              className="w-full rounded-xl border border-border/70 bg-background px-3.5 py-2.5 text-[14px] text-foreground focus:border-primary focus:outline-none"
            >
              <option value="romantic">Романтическая (пара)</option>
              <option value="friend">Друг / Подруга</option>
              <option value="business">Деловой партнёр</option>
              <option value="family">Семья / Родственник</option>
            </select>
          </div>

          {/* Birth date */}
          <div className="space-y-1">
            <label htmlFor="partner-birth-date" className="block text-[12px] font-medium text-muted-foreground uppercase tracking-wider">
              Дата рождения
            </label>
            <input
              id="partner-birth-date"
              type="date"
              required
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
              className="w-full rounded-xl border border-border/70 bg-background px-3.5 py-2.5 text-[14px] text-foreground focus:border-primary focus:outline-none"
            />
          </div>

          {/* Birth time */}
          <div className="space-y-1">
            <label htmlFor="partner-birth-time" className="block text-[12px] font-medium text-muted-foreground uppercase tracking-wider">
              Время рождения
            </label>
            <input
              id="partner-birth-time"
              type="time"
              disabled={unknownTime}
              value={birthTime}
              onChange={(e) => setBirthTime(e.target.value)}
              className="w-full rounded-xl border border-border/70 bg-background px-3.5 py-2.5 text-[14px] text-foreground focus:border-primary focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed"
            />
          </div>

          {/* Unknown time switch */}
          <div className="flex items-center justify-between gap-3 pt-1">
            <span className="text-[13px] font-medium text-foreground">Точное время неизвестно</span>
            <button
              type="button"
              role="switch"
              aria-checked={unknownTime}
              onClick={handleToggleUnknownTime}
              className={`relative inline-flex h-6 w-11 flex-none items-center rounded-full transition-colors ${
                unknownTime ? "bg-primary" : "bg-muted"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-background transition-transform ${
                  unknownTime ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>

          {/* Approximate precision warning */}
          {unknownTime && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-[12px] text-amber-800 dark:text-amber-200 space-y-1">
              <div className="font-semibold flex items-center gap-1">
                <Info className="h-3.5 w-3.5" />
                Примерный расчёт: без ASC и домов партнёра
              </div>
              <p className="leading-relaxed opacity-90">
                Планеты и основные аспекты останутся. Дома и Асцендент партнёра не рассчитываются, а положение Луны и общий балл будут менее точными.
              </p>
            </div>
          )}

          {/* Birth city */}
          <div className="space-y-1">
            <p className="block text-[12px] font-medium text-muted-foreground uppercase tracking-wider">
              Город рождения
            </p>
            <CityPicker
              value={city}
              onChange={setCity}
              placeholder="Например: Москва"
            />
          </div>

          {/* Submit CTA */}
          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              aria-busy={loading}
              className="w-full h-[50px] rounded-[17px] bg-primary text-primary-foreground font-semibold text-[15px] flex items-center justify-center transition active:scale-[0.99] disabled:opacity-50"
            >
              {loading ? "Сохраняем данные…" : "Построить синастрию"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
// END_BLOCK: SYNASTRY_ADD_SHEET
