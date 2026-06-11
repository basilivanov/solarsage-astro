"use client"

import { useEffect, useRef, useState } from "react"
import { ArrowUp, Square } from "lucide-react"

type Props = {
  onSend: (_text: string) => void
  onStop?: () => void
  disabled?: boolean
  /** True пока стрим в полёте — показываем кнопку «стоп» вместо «отправить». */
  streaming?: boolean
}

const MAX_HEIGHT = 144 // px — ~5-6 строк, дальше внутренний скролл

/**
 * Поле ввода с авто-ростом высоты.
 *
 * - Enter — отправка (Shift+Enter — перенос строки),
 * - кнопка-стрелка справа дублирует submit; пока идёт стрим — превращается
 *   в кнопку «стоп», чтобы можно было прервать ответ агента,
 * - после отправки фокус остаётся в поле, чтобы можно было сразу
 *   задать следующий вопрос.
 */
export function Composer({ onSend, onStop, disabled, streaming }: Props) {
  const [value, setValue] = useState("")
  const ref = useRef<HTMLTextAreaElement | null>(null)

  // Авто-рост: пересчитываем при каждом изменении value
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = "0px"
    el.style.height = Math.min(el.scrollHeight, MAX_HEIGHT) + "px"
  }, [value])

  function submit() {
    const text = value.trim()
    if (!text || disabled) return
    onSend(text)
    setValue("")
    requestAnimationFrame(() => ref.current?.focus())
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
      className="flex items-end gap-2 px-4 pb-2 pt-2"
    >
      <div className="flex flex-1 items-end rounded-2xl border border-border/70 bg-card transition focus-within:border-primary/50">
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          rows={1}
          placeholder="Спроси про свою карту…"
          aria-label="Сообщение"
          className="block max-h-36 w-full resize-none bg-transparent px-3.5 py-2.5 text-[15px] leading-snug text-foreground placeholder:text-muted-foreground focus:outline-none"
        />
      </div>
      {streaming && onStop ? (
        <button
          type="button"
          onClick={onStop}
          aria-label="Остановить ответ"
          className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-foreground text-background transition active:opacity-80"
        >
          <Square className="h-[14px] w-[14px] fill-current" strokeWidth={0} />
        </button>
      ) : (
        <button
          type="submit"
          disabled={!value.trim() || disabled}
          aria-label="Отправить"
          className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-primary text-primary-foreground transition active:opacity-80 disabled:opacity-40"
        >
          <ArrowUp className="h-5 w-5" strokeWidth={2} />
        </button>
      )}
    </form>
  )
}

