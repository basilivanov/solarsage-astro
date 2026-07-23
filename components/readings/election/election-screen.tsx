// ############################################################################
// AI_HEADER: MODULE_ELECTION_SCREEN
// ROLE: Root screen component for election searches and history
// ############################################################################

"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { Sparkles, Calendar, AlertCircle } from "lucide-react"

import type { HoraryQuotaRead } from "@/packages/contracts"
import { type ElectionSearch, type ElectionEventKey } from "@/lib/contracts/election"
import { getElectionQuota, listElectionSearches, createElectionSearch } from "@/lib/api/election"

import { ElectionQuotaBar } from "./election-quota-bar"
import { ElectionForm } from "./election-form"
import { ElectionSearchCard } from "./election-search-card"
import { ElectionPurchaseSheet } from "./election-purchase-sheet"

export function ElectionScreen() {
  const router = useRouter()
  const [quota, setQuota] = useState<HoraryQuotaRead | null>(null)
  const [searches, setSearches] = useState<ElectionSearch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [purchaseOpen, setPurchaseOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [qData, sData] = await Promise.all([
        getElectionQuota(),
        listElectionSearches(20, 0),
      ])
      setQuota(qData)
      setSearches(sData)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить данные")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadData()
  }, [loadData])

  const totalCredits = quota
    ? (quota.weeklyFreeAvailable ? 1 : 0) + quota.bonusCredits + quota.paidCredits
    : 0

  const handleFormSubmit = async (params: {
    eventType: ElectionEventKey
    windowFrom: string
    windowTo: string
  }) => {
    setSubmitting(true)
    setError(null)
    try {
      const search = await createElectionSearch(params)
      router.push(`/readings/election/${search.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать запрос")
      setSubmitting(false)
    }
  }

  const dataState = loading ? "loading" : error ? "error" : "ready"

  return (
    <div
      className="flex flex-col gap-6 p-4 sm:p-6 max-w-xl mx-auto"
      data-testid="election-screen"
      data-state={dataState}
      data-has-credit={totalCredits > 0 ? "true" : "false"}
      data-access-state={totalCredits > 0 ? "unlocked" : "locked"}
    >
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Calendar className="h-5 w-5" />
        </div>
        <div>
          <h1 className="font-serif text-[22px] font-bold text-foreground">Подбор даты</h1>
          <p className="text-[13px] text-muted-foreground">
            Найди идеальные дни по звёздам для важных событий
          </p>
        </div>
      </div>

      {error && (
        <div
          className="flex items-center gap-2 rounded-xl bg-destructive/10 p-4 text-[13px] text-destructive"
          role="alert"
          data-testid="election-error"
        >
          <AlertCircle className="h-5 w-5 flex-none" />
          {error}
        </div>
      )}

      {quota && (
        <ElectionQuotaBar
          quota={quota}
          onBuy={() => setPurchaseOpen(true)}
        />
      )}

      <ElectionForm
        onSubmit={(p) => void handleFormSubmit(p)}
        disabled={totalCredits === 0 || submitting}
        disabledReason={
          totalCredits === 0 ? "У вас нет доступных поисков. Докупите или дождитесь бесплатного." : undefined
        }
      />

      {/* History section */}
      {searches.length > 0 && (
        <div className="flex flex-col gap-3 mt-4" data-testid="election-history-section">
          <h3 className="text-[13px] font-medium uppercase tracking-wider text-muted-foreground">
            Предыдущие подборы
          </h3>
          <div className="flex flex-col gap-2.5">
            {searches.map((search) => (
              <ElectionSearchCard key={search.id} search={search} />
            ))}
          </div>
        </div>
      )}

      <ElectionPurchaseSheet
        open={purchaseOpen}
        onClose={() => setPurchaseOpen(false)}
        onUnlocked={() => {
          setPurchaseOpen(false)
          void loadData()
        }}
      />
    </div>
  )
}
