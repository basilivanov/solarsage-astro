"use client"

import { useMemo, useState } from "react"
import { MapPin, Search } from "lucide-react"

import { getPopularCities, searchCities } from "@/lib/api/cities"

type Props = {
  value: string
  onChange: (city: string) => void
  placeholder?: string
  suggestions?: string[]
}

export function CityPicker({
  value,
  onChange,
  placeholder = "Начни вводить город",
  suggestions,
}: Props) {
  const [focused, setFocused] = useState(false)

  const popular = useMemo(
    () => suggestions ?? getPopularCities(),
    [suggestions],
  )

  const matches = useMemo(() => searchCities(value), [value])

  const showList = focused && matches.length > 0

  return (
    <div className="space-y-4">
      <div className="relative">
        <span className="pointer-events-none absolute left-0 top-1/2 -translate-y-1/2 text-foreground/40">
          <Search className="h-4 w-4" strokeWidth={1.5} />
        </span>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 120)}
          placeholder={placeholder}
          className="w-full border-b border-border bg-transparent py-3 pl-7 pr-2 font-serif text-[22px] tracking-tight text-foreground placeholder:text-foreground/30 focus:border-accent focus:outline-none"
        />
      </div>

      {showList ? (
        <ul className="-mx-1 overflow-hidden rounded-xl border border-border/60 bg-card">
          {matches.map((c, i) => (
            <li
              key={`${c.name}-${c.country}`}
              className={i > 0 ? "border-t border-border/50" : ""}
            >
              <button
                type="button"
                onClick={() => onChange(`${c.name}, ${c.country}`)}
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
                    {c.country}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : value.trim() ? null : (
        <div>
          <p className="mb-2 font-sans text-[11px] uppercase tracking-[0.14em] text-foreground/45">
            Популярные
          </p>
          <div className="flex flex-wrap gap-2">
            {popular.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onChange(s)}
                className="rounded-full border border-border/70 bg-card px-3 py-1.5 font-sans text-[13px] text-foreground/70 transition active:bg-foreground/5"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
