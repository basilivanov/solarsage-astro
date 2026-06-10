"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { ChevronLeft, Check, Sparkles, Send } from "lucide-react"

/**
 * Красивый экран генерации натального отчёта.
 *
 * Показывает:
 *  1. Анимированный таймер прошедшего времени
 *  2. Поэтапное заполнение 13 разделов с чекмарками
 *  3. Сообщение об уведомлении в Telegram
 *  4. Плавные анимации, космическая стилистика
 *
 * В демо-режиме секции «генерируются» с задержкой.
 * В проде — реальный поллинг статуса с бэкенда.
 */

const GENERATING_SECTIONS = [
  { id: "impression", title: "Главное впечатление от карты", icon: "✨" },
  { id: "asc", title: "Твоя базовая настройка", icon: "🌙" },
  { id: "rulers", title: "Управители карты", icon: "👑" },
  { id: "sun", title: "Солнце: ядро личности", icon: "☀️" },
  { id: "stellium", title: "Сильный дом: стеллиум", icon: "🏠" },
  { id: "mercury", title: "Меркурий: мышление и речь", icon: "💬" },
  { id: "moon", title: "Луна: эмоции и внутренняя база", icon: "🌊" },
  { id: "venus-saturn", title: "Венера, Сатурн и Лилит", icon: "💫" },
  { id: "mars", title: "Марс: воля и действие", icon: "🔥" },
  { id: "money", title: "Деньги и ресурс", icon: "💰" },
  { id: "career", title: "Карьера и видимость", icon: "⭐" },
  { id: "parses", title: "Дополнительные точки", icon: "🔮" },
  { id: "stars", title: "Фиксированные звёзды и аспекты", icon: "🌟" },
]

/** Среднее время генерации одного раздела (мс). В демо ускоряем. */
const DEMO_SECTION_DELAY_MS = 1800
const REAL_SECTION_DELAY_MS = 12_000 // ~12 сек на раздел = ~2.5 мин всего

type Props = {
  /** Имя пользователя для персонализации */
  name?: string | null
  /** Цена в копейках — показываем, что оплата прошла */
  priceKopecks?: number
  /** Колбэк по завершении генерации (в демо — через ~23 сек) */
  onComplete?: () => void
  /** Реальный режим (не демо) — замедляем анимацию */
  isLive?: boolean
}

export function NatalGeneratingScreen({
  name,
  priceKopecks,
  onComplete,
  isLive = false,
}: Props) {
  const [completedIds, setCompletedIds] = useState<Set<string>>(new Set())
  const [activeId, setActiveId] = useState<string>(GENERATING_SECTIONS[0].id)
  const [elapsed, setElapsed] = useState(0)
  const startTimeRef = useRef(Date.now())
  const completedCountRef = useRef(0)

  const sectionDelay = isLive ? REAL_SECTION_DELAY_MS : DEMO_SECTION_DELAY_MS

  // Timer — считаем прошедшее время
  useEffect(() => {
    startTimeRef.current = Date.now()
    const interval = setInterval(() => {
      setElapsed(Date.now() - startTimeRef.current)
    }, 500)
    return () => clearInterval(interval)
  }, [])

  // Section progression — по одной секции «завершается»
  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>

    function tick() {
      const currentIndex = GENERATING_SECTIONS.findIndex((s) => s.id === activeId)
      if (currentIndex >= GENERATING_SECTIONS.length - 1) {
        // Последняя секция — завершаем
        setCompletedIds((prev) => new Set([...prev, activeId]))
        completedCountRef.current = GENERATING_SECTIONS.length
        // Небольшая пауза перед onComplete
        timeout = setTimeout(() => onComplete?.(), 1200)
        return
      }

      // Текущая завершена
      setCompletedIds((prev) => new Set([...prev, activeId]))
      completedCountRef.current += 1

      // Переключаем на следующую
      const nextIndex = currentIndex + 1
      setActiveId(GENERATING_SECTIONS[nextIndex].id)

      // Планируем следующий тик
      timeout = setTimeout(tick, sectionDelay)
    }

    timeout = setTimeout(tick, sectionDelay)
    return () => clearTimeout(timeout)
  }, [activeId, sectionDelay, onComplete])

  const progress = useMemo(() => {
    return Math.round(
      ((completedIds.size + (activeId && !completedIds.has(activeId) ? 0.5 : 0)) /
        GENERATING_SECTIONS.length) *
        100
    )
  }, [completedIds, activeId])

  const isDone = completedIds.size === GENERATING_SECTIONS.length

  const formatTime = useCallback((ms: number) => {
    const totalSeconds = Math.floor(ms / 1000)
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    return `${minutes}:${seconds.toString().padStart(2, "0")}`
  }, [])

  const price = priceKopecks ? Math.round(priceKopecks / 100) : null

  return (
    <div className="flex h-full w-full flex-col bg-background overflow-y-auto">
      {/* Header */}
      <header
        className="flex-none px-4 pb-4 border-b border-border/40"
        style={{ paddingTop: "max(env(safe-area-inset-top), 1rem)" }}
      >
        <Link
          href="/readings/natal"
          className="inline-flex items-center gap-1.5 text-[14px] text-muted-foreground hover:text-foreground active:scale-95 transition"
        >
          <ChevronLeft className="h-4 w-4" />
          <span>Натальная карта</span>
        </Link>
      </header>

      <main className="flex-1 px-5 py-6 max-w-md mx-auto w-full space-y-6">
        {/* Hero block */}
        <div className="space-y-3">
          <div className="relative flex items-center justify-center">
            {/* Orbiting dot */}
            <div className="relative h-20 w-20">
              <div className="absolute inset-0 rounded-full border-2 border-primary/15" />
              <div className="absolute inset-[6px] rounded-full border border-primary/10" />
              <div
                className="absolute inset-0 animate-spin"
                style={{ animationDuration: "6s" }}
              >
                <div className="absolute left-1/2 top-0 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/80 shadow-lg shadow-primary/30" />
              </div>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-primary/10">
                  <Sparkles className="h-5 w-5 text-primary animate-pulse" />
                </div>
              </div>
            </div>
          </div>

          <div className="text-center space-y-1.5">
            <h1 className="font-serif text-[24px] leading-tight tracking-tight text-foreground">
              {isDone ? "Готово!" : "Собираем твой разбор"}
            </h1>
            <p className="text-[14px] leading-relaxed text-muted-foreground">
              {isDone
                ? name
                  ? `${name}, твой натал готов — сейчас откроем`
                  : "Разбор готов — сейчас откроем"
                : name
                  ? `${name}, ЛLM бережно анализирует каждый фактор твоей карты`
                  : "LLM бережно анализирует каждый фактор карты"}
            </p>
          </div>
        </div>

        {/* Timer + progress */}
        <div className="space-y-2">
          <div className="h-2.5 overflow-hidden rounded-full bg-primary/8">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary/50 via-primary/80 to-primary transition-all duration-700 ease-out"
              style={{ width: `${Math.min(progress, 100)}%` }}
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-muted-foreground">
              {completedIds.size} из {GENERATING_SECTIONS.length} разделов
            </span>
            <span className="font-mono text-[13px] tabular-nums text-primary/80">
              {formatTime(elapsed)}
            </span>
          </div>
        </div>

        {/* Sections list */}
        <div className="space-y-1.5">
          {GENERATING_SECTIONS.map((section) => {
            const isCompleted = completedIds.has(section.id)
            const isActive = section.id === activeId && !isCompleted
            const isPending = !isCompleted && !isActive

            return (
              <div
                key={section.id}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-500 ${
                  isCompleted
                    ? "bg-emerald-500/[0.06] border border-emerald-500/15"
                    : isActive
                      ? "bg-primary/[0.06] border border-primary/15"
                      : "bg-card border border-border/40 opacity-50"
                }`}
              >
                {/* Status circle */}
                <div
                  className={`flex h-7 w-7 flex-none items-center justify-center rounded-full transition-colors duration-500 ${
                    isCompleted
                      ? "bg-emerald-500/15 text-emerald-500"
                      : isActive
                        ? "bg-primary/12 text-primary"
                        : "bg-muted/60 text-muted-foreground/50"
                  }`}
                >
                  {isCompleted ? (
                    <Check className="h-3.5 w-3.5" strokeWidth={3} />
                  ) : isActive ? (
                    <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                  ) : (
                    <span className="text-[11px]">{section.icon}</span>
                  )}
                </div>

                {/* Title */}
                <span
                  className={`text-[13px] leading-snug transition-colors duration-500 ${
                    isCompleted
                      ? "text-foreground/90"
                      : isActive
                        ? "text-foreground font-medium"
                        : "text-muted-foreground/70"
                  }`}
                >
                  {section.title}
                </span>
              </div>
            )
          })}
        </div>

        {/* Telegram notification message */}
        <div className="rounded-2xl border border-primary/12 bg-gradient-to-br from-primary/[0.05] via-background to-primary/[0.02] px-4 py-3.5 space-y-2">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#2AABEE]/10">
              <Send className="h-3.5 w-3.5 text-[#2AABEE]" />
            </div>
            <div className="text-[13px] font-medium text-foreground">
              Пришлём уведомление в Telegram
            </div>
          </div>
          <p className="text-[12.5px] leading-relaxed text-muted-foreground pl-[42px]">
            Можно закрыть этот экран — когда разбор будет готов, мы пришлём
            уведомление. Обычно это занимает 2–3 минуты.
          </p>
        </div>

        {/* Price confirmation */}
        {price ? (
          <p className="text-center text-[11.5px] text-muted-foreground/60">
            Оплата {price} ₽ подтверждена · Разбор привязан к твоему профилю
          </p>
        ) : null}
      </main>
    </div>
  )
}
