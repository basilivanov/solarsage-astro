// ############################################################################
// AI_HEADER: APP_ELECTION_SEARCH_ID_PAGE
// ROLE: Election search detail & polling page
// ############################################################################

"use client"

import { useCallback, useEffect, useState, use } from "react"
import Link from "next/link"
import { ChevronLeft, AlertOctagon, RotateCcw } from "lucide-react"

import type { ElectionSearch } from "@/lib/contracts/election"
import { getElectionSearch } from "@/lib/api/election"
import { ElectionProcessingCard } from "@/components/readings/election/election-processing-card"
import { ElectionResultView } from "@/components/readings/election/election-result-view"

type Props = {
  params: Promise<{ id: string }>
}

export default function ElectionDetailPage({ params }: Props) {
  const { id } = use(params)
  const [search, setSearch] = useState<ElectionSearch | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [pollingTimedOut, setPollingTimedOut] = useState(false)

  const fetchSearch = useCallback(async () => {
    try {
      const data = await getElectionSearch(id)
      if (data === null) {
        setLoadError("Подбор не найден")
      } else {
        setSearch(data)
        setLoadError(null)
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Не удалось загрузить данные")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void fetchSearch()
  }, [fetchSearch])

  // Polling loop when status is pending or processing
  useEffect(() => {
    if (!search) return
    if (search.status !== "pending" && search.status !== "processing") return

    const startTime = Date.now()
    const interval = setInterval(async () => {
      if (Date.now() - startTime > 60000) {
        setPollingTimedOut(true)
        clearInterval(interval)
        return
      }

      try {
        const data = await getElectionSearch(id)
        if (data) {
          setSearch(data)
          if (data.status !== "pending" && data.status !== "processing") {
            clearInterval(interval)
          }
        }
      } catch {
        // Ignore polling network errors
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [id, search?.status])

  const dataState = loading
    ? "loading"
    : loadError
      ? "error"
      : search?.status === "pending" || search?.status === "processing"
        ? "processing"
        : search?.status === "done"
          ? "done"
          : "failed"

  return (
    <div
      className="flex flex-col gap-6 p-4 sm:p-6 max-w-xl mx-auto"
      data-testid="election-detail-page"
      data-state={dataState}
    >
      <div className="flex items-center justify-between">
        <Link
          href="/readings/election"
          className="inline-flex items-center gap-1 text-[13px] font-medium text-muted-foreground hover:text-foreground transition"
        >
          <ChevronLeft className="h-4 w-4" />
          Назад к подборам
        </Link>
      </div>

      {loading && (
        <div className="py-12 text-center text-[13px] text-muted-foreground" role="status">
          Загрузка...
        </div>
      )}

      {loadError && (
        <div className="rounded-2xl border border-destructive/20 bg-card p-6 text-center flex flex-col items-center gap-3">
          <AlertOctagon className="h-8 w-8 text-destructive" />
          <h3 className="font-serif text-[17px] font-semibold text-foreground">Ошибка</h3>
          <p className="text-[13.5px] text-muted-foreground">{loadError}</p>
          <button
            type="button"
            onClick={() => {
              setLoading(true)
              void fetchSearch()
            }}
            className="mt-2 inline-flex items-center gap-2 rounded-full bg-secondary px-4 py-2 text-[13px] font-medium text-foreground transition active:scale-95"
          >
            <RotateCcw className="h-4 w-4" />
            Попробовать снова
          </button>
        </div>
      )}

      {!loading && !loadError && search && (
        <>
          {(search.status === "pending" || search.status === "processing") && (
            <div className="flex flex-col gap-4">
              <ElectionProcessingCard />
              {pollingTimedOut && (
                <p className="text-center text-[13px] text-muted-foreground" role="alert">
                  Расчёт занимает больше времени. Вы можете вернуться к подбору позже — он появится в истории.
                </p>
              )}
            </div>
          )}

          {search.status === "done" && search.result && (
            <ElectionResultView result={search.result} />
          )}

          {(search.status === "failed" || search.status === "refunded") && (
            <div className="rounded-2xl border border-destructive/20 bg-card p-6 text-center flex flex-col items-center gap-3">
              <AlertOctagon className="h-8 w-8 text-destructive" />
              <h3 className="font-serif text-[17px] font-semibold text-foreground">
                Не удалось подобрать даты
              </h3>
              <p className="text-[13.5px] text-muted-foreground">
                {search.publicErrorMessage || "Произошла ошибка при расчёте звездного окна."}
              </p>
              {search.status === "refunded" && (
                <span className="rounded-full bg-secondary px-3 py-1 text-[12px] text-foreground font-medium">
                  Списание возвращено на ваш баланс
                </span>
              )}
              <Link
                href="/readings/election"
                className="mt-2 inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2 text-[13px] font-medium text-primary-foreground transition active:scale-95"
              >
                Попробовать снова
              </Link>
            </div>
          )}
        </>
      )}
    </div>
  )
}
