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
