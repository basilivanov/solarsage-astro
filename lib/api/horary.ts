import type {
  HoraryQuestionCreate,
  HoraryQuestionRead,
  HoraryQuotaRead,
} from "@/packages/contracts"
import { IS_DEMO_MODE } from "@/lib/demo-mode"
import { DEMO_HORARY_QUOTA, DEMO_HORARY_QUESTIONS } from "@/lib/demo-data"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

// ── Demo-mode local cache ─────────────────────────────────────────
// Stores questions created in demo mode so that getHoraryQuestion
// can find them (they have random IDs not in DEMO_HORARY_QUESTIONS).
const demoCreatedQuestions = new Map<string, { question: HoraryQuestionRead; createdAt: number }>()

/** Simulates the processing→answered transition after ~4 seconds. */
function simulateDemoAnswer(q: HoraryQuestionRead): HoraryQuestionRead {
  // Pick a random answered demo question to borrow its answer
  const answeredDemo = DEMO_HORARY_QUESTIONS.find((d) => d.status === "answered" && d.answer)
  const answer = answeredDemo?.answer ?? null

  return {
    ...q,
    status: "answered",
    answer: answer
      ? { ...answer }
      : {
          verdict: "maybe" as const,
          confidence: 0.55,
          confidenceLabel: "medium" as const,
          confidenceExplanation: "Демо-ответ: карта не даёт однозначного ответа.",
          blocks: [
            { type: "verdict_card" as const, verdict: "maybe" as const, confidence: 0.55, label: "Возможно", confidenceLabel: "medium" as const, confidenceExplanation: "Демо-ответ: карта не даёт однозначного ответа." },
            { type: "divider" as const },
            { type: "paragraph" as const, text: "Это демо-ответ. В реальном режиме здесь будет полный разбор хорарной карты с свидетельствами, сроками и рекомендацией." },
          ],
          planets: [],
          generatedAt: new Date().toISOString(),
        },
    creditRefunded: false,
  } as unknown as HoraryQuestionRead
}

type HoraryErrorBody = {
  detail?: {
    code?: string
    message?: string
    reason?: string
  }
}

export class HoraryApiError extends Error {
  status: number
  code?: string

  constructor({ status, code, message }: { status: number; code?: string; message: string }) {
    super(message)
    this.name = "HoraryApiError"
    this.status = status
    this.code = code
  }
}

async function parseHoraryError(res: Response) {
  const body = await res.json().catch(() => ({} as HoraryErrorBody))
  const detail = body?.detail

  if (res.status === 402 || detail?.code === "NO_HORARY_CREDITS") {
    return "Недостаточно хорарных вопросов"
  }
  if (res.status === 409 || detail?.code === "IDEMPOTENCY_CONFLICT") {
    return "Этот запрос уже был отправлен. Попробуй ещё раз."
  }
  if (res.status === 0 || !res.statusText) {
    return "Не удалось связаться с сервером. Попробуй ещё раз."
  }

  return detail?.message || detail?.reason || "Не удалось отправить вопрос."
}

async function buildHoraryApiError(res: Response): Promise<HoraryApiError> {
  const body = await res.json().catch(() => ({} as HoraryErrorBody))
  const detail = body?.detail
  const message = await parseHoraryError(
    new Response(JSON.stringify(body), {
      status: res.status,
      statusText: res.statusText,
      headers: res.headers,
    })
  )

  return new HoraryApiError({
    status: res.status,
    code: detail?.code,
    message,
  })
}

export async function getHoraryQuota(): Promise<HoraryQuotaRead> {
  if (IS_DEMO_MODE) return DEMO_HORARY_QUOTA as unknown as HoraryQuotaRead

  const res = await fetch(`${API_BASE}/api/horary/quota`, { credentials: "include" })
  if (!res.ok) throw new Error("Failed to fetch horary quota")
  return res.json()
}

export async function listHoraryQuestions(
  limit = 20,
  offset = 0
): Promise<HoraryQuestionRead[]> {
  if (IS_DEMO_MODE) {
    const staticDemos = DEMO_HORARY_QUESTIONS.slice(offset, offset + limit) as unknown as HoraryQuestionRead[]
    // Also include any demo-created questions (most recent first)
    const created = Array.from(demoCreatedQuestions.values())
      .map((e) => e.question)
      .filter((q) => q.status === "answered")
    return [...created, ...staticDemos].slice(offset, offset + limit)
  }

  const res = await fetch(
    `${API_BASE}/api/horary/questions?limit=${limit}&offset=${offset}`,
    { credentials: "include" }
  )

  if (!res.ok) {
    throw await buildHoraryApiError(res)
  }

  return res.json()
}

export async function getHoraryQuestion(id: string): Promise<HoraryQuestionRead | null> {
  if (IS_DEMO_MODE) {
    // Check demo-created questions first
    const cached = demoCreatedQuestions.get(id)
    if (cached) {
      const elapsed = Date.now() - cached.createdAt
      // Simulate processing: keep "processing" for ~4 seconds, then return "answered"
      if (elapsed >= 4000) {
        const answered = simulateDemoAnswer(cached.question)
        // Update cache so next call returns answered immediately
        demoCreatedQuestions.set(id, { question: answered, createdAt: cached.createdAt })
        return answered
      }
      return cached.question
    }

    // Fall back to static demo questions
    return (DEMO_HORARY_QUESTIONS.find((q) => q.id === id) ?? null) as unknown as HoraryQuestionRead | null
  }

  const res = await fetch(`${API_BASE}/api/horary/questions/${id}`, {
    credentials: "include",
  })

  if (res.status === 404) {
    return null
  }

  if (!res.ok) {
    throw await buildHoraryApiError(res)
  }

  return res.json()
}

export async function createHoraryQuestion(
  data: HoraryQuestionCreate
): Promise<HoraryQuestionRead> {
  if (IS_DEMO_MODE) {
    // In demo mode, create a "processing" question and cache it
    const mockQ: HoraryQuestionRead = {
      id: `hq-demo-${Date.now()}`,
      text: data.text,
      category: data.category ?? null,
      status: "processing",
      spentCreditSource: "paid",
      creditRefunded: false,
      clientTimezone: data.clientTimezone,
      clientLocalTime: data.clientLocalTime ?? null,
      questionLocationName: data.questionLocationName ?? null,
      createdAt: new Date().toISOString(),
      answer: null,
    } as unknown as HoraryQuestionRead

    demoCreatedQuestions.set(mockQ.id, { question: mockQ, createdAt: Date.now() })
    return mockQ
  }

  const res = await fetch(`${API_BASE}/api/horary/questions`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })

  if (!res.ok) {
    throw await buildHoraryApiError(res)
  }

  return res.json()
}
