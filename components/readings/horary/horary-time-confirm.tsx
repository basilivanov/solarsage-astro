"use client"

import { useState, useEffect } from "react"
import { Clock, MapPin} from "lucide-react"
import { CityPicker } from "@/components/onboarding/city-picker"
import type { City } from "@/lib/contracts/city"

type Props = {
  profileCurrentCity?: string | null
  profileCurrentLat?: number | null
  profileCurrentLon?: number | null
  profileCurrentTz?: string | null
  profileBirthCity?: string | null
  profileBirthLat?: number | null
  profileBirthLon?: number | null
  profileBirthTz?: string | null
  onChange: (_localTime: string, _timezone: string, _lat?: number, _lon?: number, _locationName?: string) => void
}

export function HoraryTimeConfirm({
  profileCurrentCity,
  profileCurrentLat,
  profileCurrentLon,
  profileCurrentTz,
  profileBirthCity,
  profileBirthLat,
  profileBirthLon,
  profileBirthTz,
  onChange,
}: Props) {
  const [localTime, setLocalTime] = useState("")
  const [timezone, setTimezone] = useState("")
  const [selectedCity, setSelectedCity] = useState<City | null>(null)
  const [isEditingTime, setIsEditingTime] = useState(false)
  const [isEditingPlace, setIsEditingPlace] = useState(false)

  // Resolve default location based on fallbacks
  useEffect(() => {
    let resolvedCity: City | null = null
    if (profileCurrentCity) {
      const parts = profileCurrentCity.split(",")
      resolvedCity = {
        name: parts[0].trim(),
        country: parts[1]?.trim() || "",
        lat: profileCurrentLat ?? undefined,
        lon: profileCurrentLon ?? undefined,
        timezone: profileCurrentTz ?? undefined,
      }
    } else if (profileBirthCity) {
      const parts = profileBirthCity.split(",")
      resolvedCity = {
        name: parts[0].trim(),
        country: parts[1]?.trim() || "",
        lat: profileBirthLat ?? undefined,
        lon: profileBirthLon ?? undefined,
        timezone: profileBirthTz ?? undefined,
      }
    }
    setSelectedCity(resolvedCity)
  }, [profileCurrentCity, profileCurrentLat, profileCurrentLon, profileCurrentTz, profileBirthCity, profileBirthLat, profileBirthLon, profileBirthTz])

  // Sync timezone when selected city changes (fixes F2)
  useEffect(() => {
    if (selectedCity?.timezone) {
      setTimezone(selectedCity.timezone)
    }
  }, [selectedCity])

  // Initialize time/timezone
  useEffect(() => {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Moscow"
    const now = new Date()
    const offsetMs = now.getTimezoneOffset() * 60 * 1000
    const localISO = new Date(now.getTime() - offsetMs).toISOString().slice(0, 16)

    setTimezone(tz)
    setLocalTime(localISO)
  }, [])

  // Call onChange whenever time or city changes
  useEffect(() => {
    if (localTime && timezone) {
      const lat = selectedCity?.lat
      const lon = selectedCity?.lon
      const locationName = selectedCity ? `${selectedCity.name}${selectedCity.country ? `, ${selectedCity.country}` : ""}` : undefined
      onChange(localTime, timezone, lat, lon, locationName)
    }
  }, [localTime, timezone, selectedCity, onChange])

  const formatDisplayDate = (iso: string) => {
    if (!iso) return ""
    try {
      const d = new Date(iso)
      return d.toLocaleString("ru-RU", {
        day: "numeric",
        month: "long",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch {
      return iso
    }
  }

  const formatCityDisplay = (city: City | null) => {
    if (!city) return "не определено"
    return `${city.name}${city.country ? `, ${city.country}` : ""}`
  }

  return (
    <div className="rounded-xl border border-border/60 bg-muted/30 p-4 space-y-4">
      <div>
        <h4 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground mb-3">
          Момент вопроса — важно для расчёта карты
        </h4>

        <div className="space-y-3">
          {/* Time row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 text-[13px] text-foreground/80">
              <Clock className="h-4 w-4 text-muted-foreground flex-none" />
              <span>
                Время: <strong className="text-foreground">{formatDisplayDate(localTime)}</strong> ({timezone})
              </span>
            </div>
            <button
              type="button"
              onClick={() => {
                setIsEditingTime(!isEditingTime)
                setIsEditingPlace(false)
              }}
              className="text-[12px] font-medium text-primary hover:text-primary/80 transition active:scale-95"
            >
              Изменить время
            </button>
          </div>

          {/* Place row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 text-[13px] text-foreground/80">
              <MapPin className="h-4 w-4 text-muted-foreground flex-none" />
              <span>
                Место: <strong className="text-foreground">{formatCityDisplay(selectedCity)}</strong>
              </span>
            </div>
            <button
              type="button"
              onClick={() => {
                setIsEditingPlace(!isEditingPlace)
                setIsEditingTime(false)
              }}
              className="text-[12px] font-medium text-primary hover:text-primary/80 transition active:scale-95"
            >
              {selectedCity ? "Изменить место" : "Указать место"}
            </button>
          </div>
        </div>
      </div>

      {/* Inline Time Editor */}
      {isEditingTime && (
        <div className="border-t border-border/40 pt-3 space-y-2">
          <label className="block text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
            Выбрать другое время
          </label>
          <input
            type="datetime-local"
            value={localTime}
            onChange={(e) => setLocalTime(e.target.value)}
            className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-[14px] text-foreground focus:border-accent focus:outline-none"
          />
        </div>
      )}

      {/* Inline Place Editor */}
      {isEditingPlace && (
        <div className="border-t border-border/40 pt-3 space-y-2">
          <label className="block text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
            Поиск города
          </label>
          <CityPicker
            value={selectedCity}
            onChange={(city) => {
              setSelectedCity(city)
              setIsEditingPlace(false)
            }}
            placeholder="Начни вводить город"
            autoFocus
          />
        </div>
      )}
    </div>
  )
}

