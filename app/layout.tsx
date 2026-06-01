import type { Metadata, Viewport } from "next"
import { Inter, Instrument_Serif, Lora } from "next/font/google"
import Script from "next/script"
import { Analytics } from "@vercel/analytics/next"
import { TelegramInit } from "@/components/telegram-init"
import { CorrelationInit } from "@/components/correlation-init"
import "./globals.css"

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-sans",
  display: "swap",
})

const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  variable: "--font-serif-display",
  display: "swap",
})

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
      <head>
        <meta httpEquiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
        <meta httpEquiv="Pragma" content="no-cache" />
        <meta httpEquiv="Expires" content="0" />
      </head>
      <body
        className={`${inter.variable} ${instrumentSerif.variable} ${loraSerif.variable} font-sans antialiased`}
      >
        <Script
          src="https://telegram.org/js/telegram-web-app.js"
          strategy="beforeInteractive"
        />
        <Script id="error-catcher" strategy="beforeInteractive">
          {`
            window.__astroErrors = [];
            window.addEventListener('error', function(e) {
              var err = { msg: e.message, src: e.filename, line: e.lineno, col: e.colno, time: Date.now() };
              window.__astroErrors.push(err);
              try { fetch('/api/_log', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({envelopes:[{timestamp:new Date().toISOString(),level:'error',message:'CLIENT_CRASH: '+e.message+' at '+e.filename+':'+e.lineno,correlation_id:null,extra:{stack:e.error?.stack}}]}) }); } catch(_) {}
            });
            window.addEventListener('unhandledrejection', function(e) {
              var err = { msg: String(e.reason), time: Date.now() };
              window.__astroErrors.push(err);
              try { fetch('/api/_log', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({envelopes:[{timestamp:new Date().toISOString(),level:'error',message:'UNHANDLED_REJECTION: '+String(e.reason),correlation_id:null}]}) }); } catch(_) {}
            });
          `}
        </Script>
        <TelegramInit />
        <CorrelationInit />
        {children}
        {process.env.NODE_ENV === "production" && <Analytics />}
      </body>
    </html>
  )
}
