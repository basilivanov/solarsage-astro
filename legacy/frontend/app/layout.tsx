import type { Metadata, Viewport } from "next"
import { Inter, Instrument_Serif, Lora } from "next/font/google"
import Script from "next/script"
import { Analytics } from "@vercel/analytics/next"
import { TelegramInit } from "@/components/telegram-init"
import "./globals.css"

// Основной sans — с кириллицей, как и было
const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-sans",
  display: "swap",
})

// Instrument Serif — визуально главный serif, но он НЕ содержит
// кириллического subset'а. Просим только latin, чтобы Next не тянул
// пустой ответ и не сыпал ворнингами.
const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  variable: "--font-serif-display",
  display: "swap",
})

// Lora — serif с полноценным cyrillic subset'ом. Держим его как
// per-glyph fallback: латиница отрисуется Instrument Serif, а как
// только встретится кириллический символ — браузер сам подхватит Lora.
// Визуально она достаточно близка по пропорциям и не ломает ритм.
const loraSerif = Lora({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500"],
  style: ["normal", "italic"],
  variable: "--font-serif-cyrillic",
  display: "swap",
})

export const metadata: Metadata = {
  title: "Today — астрологический навигатор дня",
  description:
    "Персональный разбор дня: что сегодня происходит, как это проявляется у тебя, какие силы формируют день.",
  generator: "v0.app",
}

export const viewport: Viewport = {
  themeColor: "#f6f3ec",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="ru" className="bg-background">
      <body
        className={`${inter.variable} ${instrumentSerif.variable} ${loraSerif.variable} font-sans antialiased`}
      >
        <Script
          src="https://telegram.org/js/telegram-web-app.js"
          strategy="beforeInteractive"
        />
        <TelegramInit />
        {children}
        {process.env.NODE_ENV === "production" && <Analytics />}
      </body>
    </html>
  )
}
