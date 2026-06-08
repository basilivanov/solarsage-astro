"use client"

import { useState, useEffect } from "react"
import { Calendar, Clock, Edit2 } from "lucide-react"

type Props = {
  onChange: (localTime: string, timezone: string) => void
}

export function HoraryTimeConfirm({ onChange }: Props) {
  const [localTime, setLocalTime] = useState("")
  const [timezone, setTimezone] = useState("")
  const [isEditing, setIsEditing] = useState(false)

  useEffect(() => {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Moscow"
    const now = new Date()
    // Convert to ISO string in local time format without seconds: YYYY-MM-DDTHH:MM
    const offsetMs = now.getTimezoneOffset() * 60 * 1000
    const localISO = new Date(now.getTime() - offsetMs).toISOString().slice(0, 16)

    setTimezone(tz)
    setLocalTime(localISO)
    onChange(localISO, tz)
  }, [onChange])

  const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setLocalTime(val)
    onChange(val, timezone)
  }

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

  return (
    <div className="rounded-xl border border-border/60 bg-muted/30 p-3.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[13px] text-foreground/70">
          <Clock className="h-4 w-4 text-muted-foreground" />
          <span>
            Время вопроса: <strong className="text-foreground">{formatDisplayDate(localTime)}</strong> ({timezone})
          </span>
        </div>
        <button
          type="button"
          onClick={() => setIsEditing(!isEditing)}
          className="flex h-7 w-7 items-center justify-center rounded-full bg-card border border-border/60 text-muted-foreground hover:text-foreground active:scale-95 transition"
        >
          <Edit2 className="h-3 w-3" />
        </button>
      </div>

      {isEditing && (
        <div className="mt-3 border-t border-border/40 pt-3">
          <label className="block text-[11px] uppercase tracking-[0.14em] text-muted-foreground mb-1">
            Выбрать другое время
          </label>
          <input
            type="datetime-local"
            value={localTime}
            onChange={handleTimeChange}
            className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-[14px] text-foreground focus:border-accent focus:outline-none"
          />
          <p className="mt-1 text-[11px] text-muted-foreground">
            Время построения хорарной карты является ключевым для вердикта.
          </p>
        </div>
      )}
    </div>
  )
}
