import type {
  HoraryQuestionCreate,
  HoraryQuestionRead,
  HoraryQuotaRead,
} from "@/packages/contracts"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

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
  if (!res.ok) throw new Error("Failed to list horary questions")
  return res.json()
}

export async function getHoraryQuestion(id: string): Promise<HoraryQuestionRead> {
  const res = await fetch(`${API_BASE}/api/horary/questions/${id}`, {
    credentials: "include",
  })
  if (!res.ok) throw new Error("Failed to fetch horary question")
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
  if (res.status === 403) throw new Error("Horary quota exceeded")
  if (!res.ok) throw new Error("Failed to create horary question")
  return res.json()
}
