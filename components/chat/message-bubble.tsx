
// ############################################################################
// AI_HEADER: MODULE_CHAT_MESSAGE_BUBBLE
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: Module: message-bubble.tsx
// owns:
//   - components/chat/message-bubble.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import type { ChatMessage } from "@/lib/chat"

/**
 * Один пузырь сообщения в чате.
 *
 * Сообщения пользователя — справа на бренд-цвете,
 * ответы агента — слева на нейтральной карточке с лёгкой обводкой.
 * Когда сообщение стримится — рисуем мигающий каретку-курсор после текста,
 * чтобы было видно, что ответ ещё печатается.
 * Намеренно без аватарок: в Telegram MA меньше места и чище без них.
 */
export function MessageBubble({
  message,
  streaming = false,
}: {
  message: ChatMessage
  streaming?: boolean
}) {
  const isUser = message.role === "user"
  return (
    <li className={isUser ? "flex justify-end" : "flex justify-start"}>
      <div
        className={
          isUser
            ? "max-w-[85%] rounded-2xl rounded-br-md bg-primary px-3.5 py-2.5 text-[15px] leading-snug text-primary-foreground"
            : "max-w-[85%] rounded-2xl rounded-bl-md border border-border/70 bg-card px-3.5 py-2.5 text-[15px] leading-snug text-foreground"
        }
      >
        <p className="whitespace-pre-wrap text-pretty">
          {message.content}
          {streaming ? (
            <span
              aria-hidden
              className="ml-0.5 inline-block h-[0.95em] w-[2px] translate-y-[1px] bg-current align-middle"
              style={{ animation: "lumen-caret 1s steps(2) infinite" }}
            />
          ) : null}
        </p>
      </div>
    </li>
  )
}
