
// ############################################################################
// AI_HEADER: MODULE_API_CHAT
// ROLE: Tests — chat.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ####// START_MODULE_CONTRACT
// purpose: Tests for chat.ts behavior
// owns:
//   - lib/api/chat.ts
// inputs: Endpoint params, request body
// outputs: Parsed response / typed data
// dependencies: local modules
// side_effects: Network calls to API
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
/**
 * API-фасад чата.
 *
 * Единственная точка интеграции с ИИ. UI и хук `useChat` зовут только её.
 * Использует реальные backend-эндпоинты.
 */

import type { ChatContext, ChatMessage } from "@/lib/contracts/chat"
import { IS_DEMO_MODE } from "@/lib/demo-mode"
import { DEMO_CHAT_MESSAGES } from "@/lib/demo-data"

export type { ChatContext, ChatMessage }

export async function* sendMessage(args: {
  history: ChatMessage[]
  message: string
  context: ChatContext
  signal?: AbortSignal
}): AsyncGenerator<string, void, unknown> {
  if (IS_DEMO_MODE) {
    const reply = generateDemoReply(args.message)
    // Simulate streaming — yield word by word
    const words = reply.split(" ")
    for (let i = 0; i < words.length; i++) {
      yield (i === 0 ? "" : " ") + words[i]
      await new Promise(r => setTimeout(r, 30))
    }
    return
  }

  const createRes = await fetch("/api/chat/threads", {
    method: "POST",
    credentials: "include",
    headers: { "Accept": "application/json" },
    signal: args.signal,
  })
  if (!createRes.ok) {
    throw new Error(`Failed to create chat thread: ${createRes.status}`)
  }
  const { id: threadId } = await createRes.json()

  const msgRes = await fetch(`/api/chat/threads/${threadId}/messages`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
    },
    body: JSON.stringify({ content: args.message }),
    signal: args.signal,
  })
  if (!msgRes.ok) {
    throw new Error(`Failed to send message: ${msgRes.status}`)
  }
  const body = await msgRes.json()

  const assistantMsg = body.assistant_message ?? body.assistantMessage
  if (assistantMsg?.content) {
    yield assistantMsg.content
  }
}

// ── Demo-mode context-aware reply generator ────────────────────────────
/**
 * Generates a plausible astrological reply based on keyword matching.
 * Not a real LLM — this keeps the demo engaging without a backend.
 */
function generateDemoReply(message: string): string {
  const m = message.toLowerCase().trim()

  // Greetings
  if (/^(привет|здравствуй|хай|hello|hi|добр(ый|ое|ого))/.test(m)) {
    return "Привет! Я твой астрологический ассистент SolarSage. Можешь спросить меня про сегодняшний день, отношения, работу, деньги или просто рассказать, что тебя беспокоит — я помогу разобрать это через призму текущих аспектов."
  }

  // Relationships / love
  if (m.includes("отношен") || m.includes("любов") || m.includes("партнёр") || m.includes("бывш") || m.includes("встречаюсь") || m.includes("свидан")) {
    return "Сегодня твоя Венера — планета любви и удовольствий — соединяется с Юпитером, планетой роста и удачи, в твоём 3 доме общения. Это значит, что симпатии и возможности могут прийти через разговор или переписку. Особенно удачны откровенные беседы один-на-один. При этом дневная оппозиция Солнца и Марса создаёт напряжённый фон — старайся не вступать в ненужные споры с близкими. Если есть недосказанность — вечерний разговор прояснит многое."
  }

  // Career / work
  if (m.includes("работ") || m.includes("карьер") || m.includes("дел") || m.includes("проект") || m.includes("начин") || m.includes("бизнес")) {
    return "Активен 10 дом карьеры и общественного статуса — сегодня рабочие темы ощущаются заметнее обычного. Солнце в оппозиции с Марсом (сила 0.94) создаёт напряжение между личной инициативой и внешними обстоятельствами: не пытайся продавить ситуацию, лучше найди баланс. Плутон в тринах с Сатурном помогает находить нестандартные решения и устойчивые компромиссы. Хороший день для планирования, но не для резких решений."
  }

  // Money / finances
  if (m.includes("деньг") || m.includes("финанс") || m.includes("доход") || m.includes("зарплат") || m.includes("покупк")) {
    return "Венера в соединении с Юпитером в 3 доме общения — деньги и симпатии могут прийти через контакты, переговоры или переписку. Это удачное время для убеждения и презентаций. Однако квадратура Меркурия с Сатурном во второй половине дня может принести задержки в документах или договорённостях — перепроверяй условия и не подписывай ничего на бегу."
  }

  // Health / wellbeing
  if (m.includes("здоров") || m.includes("бол") || m.includes("устал") || m.includes("энерг") || m.includes("сон")) {
    return "Луна в Козероге активирует твой 6 дом работы и здоровья — сегодня важно соблюдать режим и не перегружать себя. Квадратура Луны с натальным Сатурном добавляет ощущение тяжести и ответственности, поэтому дай себе паузу перед реакцией. Вечером избегай физических перегрузок, лучше займись растяжкой или спокойной прогулкой. Сон сегодня особенно важен для восстановления."
  }

  // Evening / plans
  if (m.includes("вечер") || m.includes("план") || m.includes("отдых") || m.includes("провест")) {
    return "Вечером Луна в Козероге активирует 6 дом порядка — хорошее время для планирования завтрашнего дня или завершения начатых дел. Квадратура Меркурия с Сатурном может принести задержки в переписке, так что не жди мгновенных ответов на сообщения. Лучше проведи вечер за чтением, спокойным общением с близкими или рефлексией — эмоциональный фон будет менее напряжённым во второй половине дня."
  }

  // Moon / planets / astrology meta
  if (m.includes("лун") || m.includes("планет") || m.includes("аспект") || m.includes("знак") || m.includes("гороскоп")) {
    return "Сегодня в фокусе несколько аспектов: оппозиция Солнца и Марса (орб 0.5°, сила 0.94) создаёт фоновую напряжённость; секстиль Луны с Меркурием (орб 1.6°, сила 0.73) даёт шанс разобраться в чувствах через разговор; квадратура Меркурия с Сатурном (орб 1.4°, сила 0.80) добавляет тяжесть в коммуникациях. Луна в Козероге, 18° — знак дисциплины и структуры. Полнолуние ещё ощущается, поэтому эмоции проявляются ярче обычного."
  }

  // Emotions / mood
  if (m.includes("чувств") || m.includes("эмоц") || m.includes("трев") || m.includes("пережива") || m.includes("груст") || m.includes("злюсь")) {
    return "Полнолуние ещё ощущается — то, что раньше было фоном, может выйти наружу и потребовать реакции. Секстиль Луны с Меркурием даёт тебе шанс осознать и назвать свои чувства через разговор или дневник. Не подавляй эмоции, но и не принимай решений на пике — дай себе паузу. Дом полнолуния показывает сферу, где проще увидеть результат: обрати внимание на темы 4 дома — дом, семья, внутренняя база."
  }

  // Future / decisions
  if (m.includes("будущ") || m.includes("решен") || m.includes("выбор") || m.includes("перееезд") || m.includes("смен")) {
    return "Плутон в тринах с Сатурном (сила 0.92) помогает находить устойчивые решения и трансформировать то, что давно требовало перемен. Однако при текущей оппозиции Солнца и Марса лучше не принимать резких решений — дождись, когда напряжённый фон спадёт (через 2-3 дня). Сформулируй вопрос письменно и вернись к нему на неделе — ответ станет яснее. Для срочных решений опирайся на рутину и проверенные схемы."
  }

  // Thanks / closing
  if (m.includes("спасибо") || m.includes("благодар") || m.includes("понят")) {
    return "Рад помочь! Если возникнут ещё вопросы про день, аспекты или решения — спрашивай. Помни: звёзты указывают на энергии, но выбор всегда за тобой. Хорошего дня!"
  }

  // Default
  return "Интересный вопрос. Сегодня день вызовов и возможностей: оппозиция Солнца и Марса (сила 0.94) создаёт фоновую напряжённость, но секстиль Луны с Меркурием (0.73) даёт шанс разобраться в чувствах и найти точку равновесия. Уточни, что именно тебя интересует — отношения, работа, самочувствие или конкретная ситуация? Я разберу это через текущие аспекты."
}

