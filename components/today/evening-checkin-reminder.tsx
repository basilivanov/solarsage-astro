"use client"

import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Moon, X } from "lucide-react"
import { useRouter } from "next/navigation"

/**
 * EveningCheckinReminder — показывает баннер-напоминание об оценке
 * дня вечером (после 18:00), если пользователь ещё не оценил день.
 *
 * Баннер появляется после 18:00 и остаётся до тех пор, пока
 * пользователь не оценит день или не закроет баннер.
 * Состояние "закрыто" хранится в sessionStorage на сегодня.
 */

interface EveningCheckinReminderProps {
  /** Дата для проверки (по умолчанию сегодня) */
  date?: Date
}

const STORAGE_KEY = "evening-checkin-dismissed"

export function EveningCheckinReminder({ date }: EveningCheckinReminderProps) {
  const router = useRouter()
  const [show, setShow] = useState(false)
  const [now, setNow] = useState<Date>(date ?? new Date())

  useEffect(() => {
    const check = () => {
      const d = new Date()
      setNow(d)
      const hour = d.getHours()
      const todayKey = `${STORAGE_KEY}-${d.toDateString()}`
      const dismissed = sessionStorage.getItem(todayKey) === "1"
      // Показывать после 18:00 и до 23:59
      if (hour >= 18 && !dismissed) {
        setShow(true)
      } else {
        setShow(false)
      }
    }
    check()
    // Проверять каждые 5 минут (на случай долгой сессии)
    const interval = setInterval(check, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  const dismiss = () => {
    const todayKey = `${STORAGE_KEY}-${now.toDateString()}`
    sessionStorage.setItem(todayKey, "1")
    setShow(false)
  }

  const goToCheckin = () => {
    dismiss()
    router.push("/checkin")
  }

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: -8, height: 0 }}
          animate={{ opacity: 1, y: 0, height: "auto" }}
          exit={{ opacity: 0, y: -8, height: 0 }}
          transition={{ duration: 0.3 }}
          className="px-5"
        >
          <div className="relative overflow-hidden rounded-2xl border border-primary/30 bg-gradient-to-br from-primary/8 via-card to-card p-3.5">
            {/* Декоративный лунный glow */}
            <div
              aria-hidden
              className="pointer-events-none absolute -right-6 -top-6 h-20 w-20 rounded-full opacity-30"
              style={{
                background: "radial-gradient(circle, oklch(0.62 0.04 295 / 0.20), transparent 70%)",
              }}
            />
            <div className="relative flex items-center gap-3">
              <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-primary/15">
                <Moon className="h-4 w-4 text-primary" strokeWidth={1.8} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-medium text-foreground">
                  Вечер — время оценить день
                </div>
                <div className="text-[11px] text-muted-foreground">
                  Как прошёл день? 30 секунд — и прогноз станет точнее.
                </div>
              </div>
              <button
                type="button"
                onClick={goToCheckin}
                className="flex-none rounded-full bg-foreground px-3.5 py-1.5 text-[12px] font-medium text-background transition active:scale-95"
              >
                Оценить
              </button>
              <button
                type="button"
                onClick={dismiss}
                aria-label="Закрыть"
                className="flex-none text-muted-foreground transition hover:text-foreground"
              >
                <X className="h-4 w-4" strokeWidth={1.8} />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
