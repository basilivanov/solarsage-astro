"use client"

type Props = {
  priceKopecks: number
  disabled: boolean
  onClick?: () => void
}

export function CtaButton({ priceKopecks, disabled, onClick }: Props) {
  const price = Math.round(priceKopecks / 100)

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="w-full rounded-2xl bg-primary px-4 py-4 text-center font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-60"
    >
      {`Полный отчёт за ${price} ₽`}
    </button>
  )
}
