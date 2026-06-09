import type {
  HoraryQuestionCreate,
  HoraryQuestionRead,
  HoraryQuotaRead,
} from "@/packages/contracts"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

type HoraryErrorBody = {
  detail?: {
    code?: string
    message?: string
    reason?: string
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

export async function getHoraryQuota(): Promise<HoraryQuotaRead> {
  const res = await fetch(`${API_BASE}/api/horary/quota`, { credentials: "include" })
  if (!res.ok) throw new Error("Failed to fetch horary quota")
  return res.json()
}

export async function listHoraryQuestions(
  limit = 20,
  offset = 0
): Promise<HoraryQuestionRead[]> {
  const res = await fetch(
    `${API_BASE}/api/horary/questions?limit=${limit}&offset=${offset}`,
    { credentials: "include" }
  )

  if (!res.ok) {
    return []
  }

  return res.json()
}

export async function getHoraryQuestion(id: string): Promise<HoraryQuestionRead | null> {
  const res = await fetch(`${API_BASE}/api/horary/questions/${id}`, {
    credentials: "include",
  })

  if (!res.ok) {
    return null
  }

  return res.json()
}

export async function createHoraryQuestion(
  data: HoraryQuestionCreate
): Promise<HoraryQuestionRead> {
  const res = await fetch(`${API_BASE}/api/horary/questions`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })

  if (!res.ok) {
    throw new Error(await parseHoraryError(res))
  }

  return res.json()
}
