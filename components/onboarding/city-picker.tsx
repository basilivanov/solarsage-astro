"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { MapPin, Search, Loader2 } from "lucide-react"

import { getPopularCities, searchCitiesAsync } from "@/lib/api/cities"
import { getTimezone } from "@/lib/api/geo"
import type { City } from "@/lib/contracts/city"
import { formatCity } from "@/lib/contracts/city"
import { logEvent } from "@/lib/log"

type Props = {
  value: City | null
  onChange: (city: City | null) => void
  placeholder?: string
  autoFocus?: boolean
}

export function CityPicker({
  value,
  onChange,
  placeholder = "Начни вводить город",
  autoFocus = false,
}: Props) {
  const [inputValue, setInputValue] = useState(value ? formatCity(value) : "")
  const [focused, setFocused] = useState(false)
  const [matches, setMatches] = useState<City[]>([])
  const [loading, setLoading] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const popular = useMemo(() => getPopularCities(), [])

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus()
      setTimeout(() => {
        rootRef.current?.scrollIntoView({ block: "center", behavior: "smooth" })
      }, 300)
    }
  }, [autoFocus])

  // Sync input value with prop value
  useEffect(() => {
    if (value) {
      setInputValue(formatCity(value))
    }
  }, [value])

  useEffect(() => {
    if (!inputValue.trim() || inputValue.length < 2) {
      setMatches([])
      return
    }

    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const results = await searchCitiesAsync(inputValue, 8)
        setMatches(results)
      } catch (error) {
        logEvent("system.error", { error: String(error) }, { msg: "Failed to search cities", slice: "W-ONBOARDING", module: "M-CITY-PICKER", block: "SEARCH" })
        setMatches([])
      } finally {
        setLoading(false)
      }
    }, 300) // debounce

    return () => clearTimeout(timer)
  }, [inputValue])

  const showList = focused && matches.length > 0

  // Scroll into view when suggestions appear (keyboard already open)
  useEffect(() => {
    if (showList) {
      setTimeout(() => {
        rootRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" })
      }, 100)
    }
  }, [showList])

  const handleSelect = (city: City) => {
    setInputValue(formatCity(city))
    setFocused(false)
    if (city.timezone) {
      onChange(city)
    } else {
      onChange(city)
      getTimezone(city.lat!, city.lon!)
        .then((tz) => {
          if (tz.timezone_id) {
            onChange({ ...city, timezone: tz.timezone_id })
          }
        })
        .catch(() => {})
    }
  }

  const handleInputChange = (newValue: string) => {
    setInputValue(newValue)
    // Clear selection if user types manually
    if (value && newValue !== formatCity(value)) {
      onChange(null)
    }
  }

  return (
    <div className="space-y-4 scroll-mt-4" ref={rootRef}>
      <div className="relative">
        <span className="pointer-events-none absolute left-0 top-1/2 -translate-y-1/2 text-foreground/40">
          <Search className="h-4 w-4" strokeWidth={1.5} />
        </span>
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={(e) => handleInputChange(e.target.value)}
          onFocus={() => {
            setFocused(true)
            // Wait for keyboard animation, then scroll into view
            setTimeout(() => {
              rootRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" })
            }, 400)
          }}
          onBlur={() => setTimeout(() => setFocused(false), 120)}
          placeholder={placeholder}
          className="w-full border-b border-border bg-transparent py-3 pl-7 pr-2 font-serif text-[22px] tracking-tight text-foreground placeholder:text-foreground/30 focus:border-accent focus:outline-none"
        />
        {loading && (
          <span className="pointer-events-none absolute right-0 top-1/2 -translate-y-1/2 text-foreground/40">
            <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
          </span>
        )}
      </div>

      {showList ? (
        <ul className="-mx-1 max-h-[35vh] overflow-y-auto rounded-xl border border-border/60 bg-card">
          {matches.map((c, i) => (
            <li
              key={`${c.name}-${c.country}`}
              className={i > 0 ? "border-t border-border/50" : ""}
            >
              <button
                type="button"
                onClick={() => handleSelect(c)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left transition active:bg-foreground/5"
              >
                <MapPin
                  className="h-4 w-4 shrink-0 text-foreground/40"
                  strokeWidth={1.5}
                />
                <span className="flex-1">
                  <span className="block font-sans text-[15px] text-foreground">
                    {c.name}
                  </span>
                  <span className="block font-sans text-[12px] text-foreground/50">
                    {c.region ? `${c.region}, ${c.country}` : c.country}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : inputValue.trim() ? null : (
        <div>
          <p className="mb-2 font-sans text-[11px] uppercase tracking-[0.14em] text-foreground/45">
            Популярные
          </p>
          <div className="flex flex-wrap gap-2">
            {popular.map((c) => (
              <button
                key={`${c.name}-${c.country}`}
                type="button"
                onClick={() => handleSelect(c)}
                className="rounded-full border border-border/70 bg-card px-3 py-1.5 font-sans text-[13px] text-foreground/70 transition active:bg-foreground/5"
              >
                {c.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
