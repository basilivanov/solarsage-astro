
// ############################################################################
// AI_HEADER: MODULE_CHAT_CHAT_SCREEN
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI chat-screen — component
// owns:
//   - components/chat/chat-screen.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { useEffect, useMemo, useRef } from "react"
import { Trash2 } from "lucide-react"

import type { Profile } from "@/lib/profile"
import type { ChatMessage } from "@/lib/contracts/chat"
import { buildContextSummary, suggestedPrompts } from "@/lib/chat"
import { useChat } from "@/hooks/use-chat"

import { ChatEmpty } from "./chat-empty"
import { Composer } from "./composer"
import { ContextPill } from "./context-pill"
import { MessageBubble } from "./message-bubble"
import { SuggestedPrompts } from "./suggested-prompts"

type Props = {
  profile: Profile
}

/**
 * Главный экран чата с агентом.
 *
 * Лэйаут учитывает архитектуру AppShell: единственный скролл-контейнер
 * — родительский div в AppShell. Поэтому здесь:
 *   - сам экран — это flex-колонка на всю min-h,
 *   - Composer фиксируется через `sticky bottom-0`, чтобы залипал
 *     над TabBar'ом, который живёт сразу под скролл-контейнером,
 *   - при новых сообщениях/печатающем индикаторе/новых токенах стрима
 *     скроллим к низу именно ближайшего скролл-предка, а не window.
 */
export function ChatScreen({ profile }: Props) {
  // context мемоизируем, иначе useChat будет ловить новый объект на
  // каждом рендере и `send` будет пересоздаваться
  const context = useMemo(() => ({ profile }), [profile])
  const { messages, pending, streamingId, send, stop, reset, loaded } =
    useChat(context)

  const bottomRef = useRef<HTMLDivElement | null>(null)

  // Длина последнего сообщения — чтобы автоскролл срабатывал и во время
  // стрима, когда количество сообщений не меняется, но содержимое растёт.
  const lastLen = messages[messages.length - 1]?.content.length ?? 0

  useEffect(() => {
    const el = bottomRef.current
    if (!el) return
    const scrollParent = findScrollParent(el)
    if (scrollParent) {
      // Во время стрима пользователь может листать вверх — не дёргаем.
      const distanceFromBottom =
        scrollParent.scrollHeight -
        scrollParent.scrollTop -
        scrollParent.clientHeight
      if (streamingId && distanceFromBottom > 120) return
      scrollParent.scrollTo({
        top: scrollParent.scrollHeight,
        behavior: streamingId ? "auto" : "smooth",
      })
    } else {
      el.scrollIntoView({ behavior: "smooth", block: "end" })
    }
  }, [messages.length, pending, streamingId, lastLen])

  if (!loaded) return null

  const isEmpty = messages.length === 0
  const summary = buildContextSummary(profile)
  // Показываем «печатает» только до первого токена — потом уже виден живой пузырь.
  const showTyping = pending && !streamingId

  return (
    <div className="flex min-h-full flex-col">
      <header
        className="flex items-start justify-between gap-3 px-5 pb-1 pt-4"
        style={{ paddingTop: "max(env(safe-area-inset-top), 1rem)" }}
      >
        <div className="min-w-0">
          <h1 className="font-serif text-[26px] leading-tight text-foreground text-balance">
            Спросить
          </h1>
          <p className="mt-1 text-[13px] leading-snug text-muted-foreground">
            Личный ассистент по твоей карте
          </p>
        </div>
        {!isEmpty ? (
          <button
            type="button"
            onClick={reset}
            aria-label="Очистить историю"
            className="-mr-1 flex h-9 w-9 flex-none items-center justify-center rounded-full text-muted-foreground transition active:bg-accent active:text-foreground"
          >
            <Trash2 className="h-[18px] w-[18px]" strokeWidth={1.6} />
          </button>
        ) : null}
      </header>

      <div className="px-5 pt-2">
        <ContextPill summary={summary} />
      </div>

      <div className="flex-1 px-4 pt-5">
        {isEmpty ? (
          <ChatEmpty>
            <SuggestedPrompts
              prompts={suggestedPrompts(profile)}
              onPick={send}
            />
          </ChatEmpty>
        ) : (
          <ul className="flex flex-col gap-3 pb-3">
            {messages.map((m: ChatMessage) => (
              <MessageBubble
                key={m.id}
                message={m}
                streaming={m.id === streamingId}
              />
            ))}
            {showTyping ? <TypingBubble /> : null}
          </ul>
        )}
        <div ref={bottomRef} aria-hidden className="h-0" />
      </div>

      <div
        className="sticky bottom-0 z-10 mt-3 border-t border-border/60 bg-background/90 backdrop-blur-md"
        style={{ paddingBottom: "max(env(safe-area-inset-bottom), 0.25rem)" }}
      >
        <Composer
          onSend={send}
          onStop={stop}
          disabled={pending}
          streaming={pending}
        />
        <p className="px-5 pb-2 text-[10px] leading-tight text-muted-foreground/70">
          Заготовка: здесь будет ИИ-ассистент, который читает твою натальную карту.
        </p>
      </div>
    </div>
  )
}

function TypingBubble() {
  return (
    <li className="flex" aria-live="polite" aria-label="Ассистент печатает">
      <div className="rounded-2xl rounded-bl-md border border-border/70 bg-card px-3.5 py-3">
        <span className="flex items-center gap-1">
          <Dot delay="0ms" />
          <Dot delay="150ms" />
          <Dot delay="300ms" />
        </span>
      </div>
    </li>
  )
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      aria-hidden
      className="block h-1.5 w-1.5 rounded-full bg-muted-foreground/60"
      style={{
        animation: "lumen-typing 1s ease-in-out infinite",
        animationDelay: delay,
      }}
    />
  )
}

/** Ищем ближайший вверх по DOM элемент с прокруткой. */
function findScrollParent(node: HTMLElement): HTMLElement | null {
  let el: HTMLElement | null = node.parentElement
  while (el && el !== document.body) {
    const oy = window.getComputedStyle(el).overflowY
    if (oy === "auto" || oy === "scroll") return el
    el = el.parentElement
  }
  return null
}
