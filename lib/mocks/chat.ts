
// ############################################################################
// AI_HEADER: MODULE_MOCKS_CHAT
// ROLE: Lib — chat.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Library: chat
// owns:
//   - lib/mocks/chat.ts
// inputs: Function arguments
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
/**
 * Mock-генератор стрима ассистента.
 *
 * Имитирует TTFB и токеновую раздачу настоящего LLM, чтобы UI
 * можно было тестировать целиком (typing-indicator, скролл, отмена).
 *
 * Импортируется ТОЛЬКО из `lib/api/chat.ts`.
 */

export async function* streamMockReply(args: {
  message: string
  signal?: AbortSignal
}): AsyncGenerator<string, void, unknown> {
  await delay(450 + Math.random() * 350, args.signal)

  const reply = pickReply(args.message)
  const tokens = tokenize(reply)
  for (const token of tokens) {
    if (args.signal?.aborted) return
    yield token
    await delay(18 + Math.random() * 42, args.signal)
  }
}

/** Режем строку на «токены» так, чтобы пробелы оставались в чанках. */
function tokenize(text: string): string[] {
  const matches = text.match(/\S+\s*/g)
  if (!matches) return [text]
  const out: string[] = []
  let buf = ""
  let count = 0
  const target = () => 1 + Math.floor(Math.random() * 3)
  let next = target()
  for (const m of matches) {
    buf += m
    count++
    if (count >= next) {
      out.push(buf)
      buf = ""
      count = 0
      next = target()
    }
  }
  if (buf) out.push(buf)
  return out
}

function delay(ms: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"))
      return
    }
    const t = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort)
      resolve()
    }, ms)
    const onAbort = () => {
      clearTimeout(t)
      reject(new DOMException("Aborted", "AbortError"))
    }
    signal?.addEventListener("abort", onAbort, { once: true })
  })
}

function pickReply(question: string): string {
  const q = question.trim().toLowerCase()
  if (!q) return "Расскажи, что тебя сейчас волнует — отталкиваясь от твоей карты, подберу ответ."

  if (q.includes("карьер") || q.includes("работ") || q.includes("проект")) {
    return "10-й дом твоей карты сейчас активно подсвечен транзитами: тема публичной роли и того, где твой голос слышен. Хороший момент не для громких заявлений, а для того, чтобы аккуратно укрепить позиции. Хочешь, посмотрим конкретные дни для шагов?"
  }
  if (q.includes("отнош") || q.includes("любов") || q.includes("парт")) {
    return "Венера в твоей карте — про ценности и то, чем ты готов делиться. На этой неделе её транзит подсвечивает разговоры «о важном». Расскажи чуть больше: про текущие отношения или про новое знакомство?"
  }
  if (q.includes("деньг") || q.includes("финанс") || q.includes("доход")) {
    return "2-й дом отвечает за твои ресурсы и то, как ты их умножаешь. Сейчас стоит смотреть не на «быстро заработать», а на «во что вкладываюсь регулярно». Хочешь разобрать конкретный сценарий?"
  }
  if (q.includes("день") || q.includes("сегодн") || q.includes("завтра")) {
    return "Я учту твой natal-фон и текущие транзиты к нему. В полной версии здесь будет конкретный совет на день — пока это заготовка, чтобы поймать ритм диалога."
  }

  return "Хороший вопрос. Я учитываю твою натальную карту и текущие транзиты — здесь будет полноценный персональный ответ, как только подключим ИИ. Это пока заготовка интерфейса."
}
