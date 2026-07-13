
// ############################################################################
// AI_HEADER: APP_NATAL_GENERATING_PAGE — natal preview, generation and polling route.
// ROLE: Client Next.js generation page; loads real preview context, starts generation, polls report status and routes ready reports.
// ############################################################################

// START_MODULE_CONTRACT: M-APP-NATAL-GENERATING-PAGE
// purpose: Coordinate the asynchronous natal full-report generation lifecycle with preview context and recoverable failure UI.
// owns:
//   - app/(grace)/readings/natal/generating/page.tsx
// inputs: fetchNatalPreview, fetchNatalGenerate and fetchNatalReport results plus user retry/back actions.
// outputs: preview-backed starting/generating/retryable/permanent/error UI or redirect to the ready report.
// dependencies: React hooks; next/navigation; natal API facade; NatalPreviewRead.
// side_effects: Performs preview/generate/poll requests, owns timeout handles, updates React state and navigates with router.replace/back.
// emitted_logs: none.
// invariants:
//   - Poll cadence is 3 seconds with at most 60 attempts.
//   - READY routes to /readings/natal/<reportId>.
//   - Timeout and retryable/permanent failures remain distinguishable.
//   - Timers and cancelled async work are cleaned up.
// failure_policy: Typed API failures become explicit GenState/PreviewState UI; unexpected render errors bubble to the route boundary.
// END_MODULE_CONTRACT: M-APP-NATAL-GENERATING-PAGE

// START_MODULE_MAP: M-APP-NATAL-GENERATING-PAGE
// public_entrypoints:
//   - NatalGeneratingPage (default).
// semantic_blocks:
//   - PREVIEW_LOAD: load real preview context.
//   - GENERATION_START: request or resume report generation.
//   - STATUS_POLLING: poll bounded report status with cleanup.
//   - RETRY_AND_BACK: handle recovery/navigation actions.
//   - STATE_RENDER: render generation and preview states.
// owned_tests:
//   - __tests__/natal/natal-component-states.test.tsx
// END_MODULE_MAP: M-APP-NATAL-GENERATING-PAGE
"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"

import { fetchNatalGenerate, fetchNatalPreview, fetchNatalReport } from "@/lib/api/natal"
import type { NatalPreviewRead } from "@/lib/contracts/natal"

/** Poll interval for report status when backend is generating (ms). */
const POLL_INTERVAL_MS = 3_000
/** Maximum poll attempts before showing a timeout message. */
const MAX_POLL_ATTEMPTS = 60 // 60 * 3s = 3 minutes

type GenState =
  | { status: "starting" }
  | { status: "generating"; reportId: string; attempt: number }
  | { status: "ready"; reportId: string }
  | { status: "failed_retryable"; reportId: string; message: string }
  | { status: "failed_permanent"; message: string }
  | { status: "error"; message: string }

type PreviewState =
  | { status: "loading" }
  | { status: "ready"; data: NatalPreviewRead }
  | { status: "error"; message: string }

/**
 * /readings/natal/generating
 *
 * Wave 5: Real generation flow.
 * - Calls POST /api/natal/generate on mount
 * - If READY immediately, redirects to report page
 * - If GENERATING, polls GET /api/natal/report for status
 * - On READY → redirect to /readings/natal/{reportId}
 * - On FAILED_RETRYABLE → show retry button
 * - On FAILED_PERMANENT → show error
 */
export default function NatalGeneratingPage() {
  const router = useRouter()
  const [previewState, setPreviewState] = useState<PreviewState>({ status: "loading" })
  const [genState, setGenState] = useState<GenState>({ status: "starting" })
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ---- Load real preview context before starting generation ----
  useEffect(() => {
    let cancelled = false

    async function loadPreview() {
      const result = await fetchNatalPreview()

      if (cancelled) return

      if (!result.ok) {
        setPreviewState({ status: "error", message: result.error.message })
        return
      }

      setPreviewState({ status: "ready", data: result.data })
    }

    void loadPreview()

    return () => {
      cancelled = true
    }
  }, [])

  // ---- Start generation on mount ----
  useEffect(() => {
    if (previewState.status !== "ready") return

    let cancelled = false

    async function startGeneration() {
      const result = await fetchNatalGenerate(false)

      if (cancelled) return

      if (!result.ok) {
        setGenState({ status: "error", message: result.error.message })
        return
      }

      const { reportId, status } = result.data

      if (status === "READY") {
        // Report already exists — go straight there
        router.replace(`/readings/natal/${reportId}`)
        return
      }

      if (status === "GENERATING" || status === "PENDING") {
        setGenState({ status: "generating", reportId, attempt: 0 })
        return
      }

      if (status === "FAILED_RETRYABLE") {
        setGenState({ status: "failed_retryable", reportId, message: result.data.errorMessage || "Generation failed, retrying may help" })
        return
      }

      if (status === "FAILED_PERMANENT") {
        setGenState({ status: "failed_permanent", message: result.data.errorMessage || "Generation failed permanently" })
        return
      }
    }

    void startGeneration()

    return () => {
      cancelled = true
    }
  }, [previewState.status, router])

  // ---- Poll for status when generating ----
  useEffect(() => {
    if (genState.status !== "generating") return

    const { reportId, attempt } = genState

    if (attempt >= MAX_POLL_ATTEMPTS) {
      setGenState({ status: "failed_retryable", reportId, message: "Generation is taking too long. Please try again." })
      return
    }

    pollTimerRef.current = setTimeout(async () => {
      const result = await fetchNatalReport(reportId)

      if (result.ok) {
        const { status } = result.data
        if (status === "READY") {
          router.replace(`/readings/natal/${reportId}`)
          return
        }
        if (status === "GENERATING" || status === "PENDING") {
          setGenState({ status: "generating", reportId, attempt: attempt + 1 })
          return
        }
        if (status === "FAILED_RETRYABLE") {
          setGenState({ status: "failed_retryable", reportId, message: result.data.errorMessage || "Generation failed" })
          return
        }
        if (status === "FAILED_PERMANENT") {
          setGenState({ status: "failed_permanent", message: result.data.errorMessage || "Generation failed permanently" })
          return
        }
      }
      // Network error — keep polling
      setGenState({ status: "generating", reportId, attempt: attempt + 1 })
    }, POLL_INTERVAL_MS)

    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
    }
  }, [genState, router])

  // ---- Retry handler ----
  const handleRetry = useCallback(async () => {
    if (genState.status !== "failed_retryable") return

    setGenState({ status: "starting" })
    const result = await fetchNatalGenerate(true)

    if (!result.ok) {
      setGenState({ status: "error", message: result.error.message })
      return
    }

    const { reportId, status } = result.data

    if (status === "READY") {
      router.replace(`/readings/natal/${reportId}`)
      return
    }

    if (status === "GENERATING" || status === "PENDING") {
      setGenState({ status: "generating", reportId, attempt: 0 })
      return
    }

    if (status === "FAILED_RETRYABLE") {
      setGenState({ status: "failed_retryable", reportId, message: result.data.errorMessage || "Generation failed" })
      return
    }

    if (status === "FAILED_PERMANENT") {
      setGenState({ status: "failed_permanent", message: result.data.errorMessage || "Generation failed permanently" })
    }
  }, [genState, router])

  // ---- Back to preview ----
  const handleBack = useCallback(() => {
    router.push("/readings/natal")
  }, [router])

  // ---- Production: show status/errors ----
  const sectionNames = [
    "Психологический портрет",
    "Асцендент и базовая настройка",
    "Управители карты",
    "Ключевые аспекты",
    "Сферы жизни",
    "Ключевые планеты",
    "Теневые темы",
    "Синтез и рекомендации",
  ]

  // Compute progress from poll attempts
  const progress = genState.status === "generating"
    ? Math.min(Math.round((genState.attempt / MAX_POLL_ATTEMPTS) * 100), 95)
    : genState.status === "ready"
      ? 100
      : 5

  // Estimate completed sections from progress
  const completedCount = genState.status === "generating"
    ? Math.min(Math.floor(progress / (100 / sectionNames.length)), sectionNames.length - 1)
    : 0
  const previewName = previewState.status === "ready" ? previewState.data.meta.name : null
  const isLoadingPreview = previewState.status === "loading"
  const visibleState: GenState =
    previewState.status === "error"
      ? { status: "error", message: previewState.message }
      : genState

  return (
    <div className="flex h-full w-full flex-col bg-background overflow-y-auto">
      <header
        className="flex-none px-4 pb-4 border-b border-border/40"
        style={{ paddingTop: "max(env(safe-area-inset-top), 1rem)" }}
      >
        <button
          type="button"
          onClick={handleBack}
          className="inline-flex items-center gap-1.5 text-[14px] text-muted-foreground hover:text-foreground active:scale-95 transition"
        >
          <span>Натальная карта</span>
        </button>
      </header>

      <main className="flex-1 px-5 py-6 max-w-md mx-auto w-full space-y-6">
        {/* Hero */}
        <div className="text-center space-y-3">
          <div className="relative flex items-center justify-center">
            <div className="relative h-20 w-20">
              <div className="absolute inset-0 rounded-full border-2 border-primary/15" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-primary/10">
                  <span className="text-[20px]">✨</span>
                </div>
              </div>
            </div>
          </div>

          <h1 className="font-serif text-[24px] leading-tight tracking-tight text-foreground">
            {visibleState.status === "failed_permanent"
              ? "Не удалось создать разбор"
              : visibleState.status === "failed_retryable"
                ? "Ошибка генерации"
                : "Собираем твой разбор"}
          </h1>
          <p className="text-[14px] leading-relaxed text-muted-foreground">
            {visibleState.status === "failed_permanent"
              ? visibleState.message
              : visibleState.status === "failed_retryable"
                ? visibleState.message
                : visibleState.status === "error"
                  ? visibleState.message
                  : previewName
                    ? `${previewName}, анализируем каждый фактор твоей натальной карты`
                    : "Анализируем каждый фактор твоей натальной карты"}
          </p>
        </div>

        {/* Progress bar (only when generating) */}
        {visibleState.status === "generating" && (
          <div className="space-y-2">
            <div className="h-2.5 overflow-hidden rounded-full bg-primary/8">
              <div
                className="h-full rounded-full bg-gradient-to-r from-primary/50 via-primary/80 to-primary transition-all duration-700 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[12px] text-muted-foreground">
                {completedCount} из {sectionNames.length} разделов
              </span>
              <span className="text-[12px] text-muted-foreground">
                Это может занять 2–3 минуты
              </span>
            </div>
          </div>
        )}

        {/* Error states */}
        {(visibleState.status === "failed_retryable" || visibleState.status === "failed_permanent" || visibleState.status === "error") && (
          <div className="space-y-3">
            <div className="rounded-2xl border border-rose-500/15 bg-rose-500/[0.04] px-4 py-3.5 space-y-2">
              <p className="text-[13px] text-foreground/80">
                {visibleState.message}
              </p>
            </div>

            <div className="flex gap-3">
              {visibleState.status === "failed_retryable" && (
                <button
                  type="button"
                  onClick={handleRetry}
                  className="flex-1 rounded-xl bg-primary px-4 py-3 text-[14px] font-medium text-primary-foreground transition active:scale-[0.99]"
                >
                  Попробовать ещё раз
                </button>
              )}
              <button
                type="button"
                onClick={handleBack}
                className="flex-1 rounded-xl border border-border/50 bg-card px-4 py-3 text-[14px] font-medium text-foreground transition active:scale-[0.99]"
              >
                Вернуться
              </button>
            </div>
          </div>
        )}

        {/* Starting state */}
        {(isLoadingPreview || visibleState.status === "starting") && (
          <div className="flex items-center justify-center py-8">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        )}

        {/* Notification note */}
        {visibleState.status === "generating" && (
          <div className="rounded-2xl border border-primary/10 bg-primary/[0.02] px-4 py-3 space-y-1">
            <p className="text-[12.5px] text-muted-foreground">
              Можно закрыть этот экран — когда разбор будет готов, мы пришлём уведомление в Telegram.
            </p>
          </div>
        )}
      </main>
    </div>
  )
}
