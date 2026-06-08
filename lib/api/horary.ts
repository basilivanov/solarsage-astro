import type {
  HoraryQuestion,
  HoraryQuestionCreate,
  HoraryQuota,
} from "@/lib/contracts/horary"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

export async function getHoraryQuota(): Promise<HoraryQuota> {
  const res = await fetch(`${API_BASE}/api/horary/quota`, { credentials: "include" })
  if (!res.ok) throw new Error("Failed to fetch horary quota")
  return res.json()
}

export async function listHoraryQuestions(
  limit = 20,
  offset = 0
): Promise<HoraryQuestion[]> {
  const res = await fetch(
    `${API_BASE}/api/horary/questions?limit=${limit}&offset=${offset}`,
    { credentials: "include" }
  )
  if (!res.ok) throw new Error("Failed to list horary questions")
  return res.json()
}

export async function getHoraryQuestion(id: string): Promise<HoraryQuestion> {
  const res = await fetch(`${API_BASE}/api/horary/questions/${id}`, {
    credentials: "include",
  })
  if (!res.ok) throw new Error("Failed to fetch horary question")
  return res.json()
}

export async function createHoraryQuestion(
  data: HoraryQuestionCreate
): Promise<HoraryQuestion> {
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
