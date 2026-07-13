
// ############################################################################
// AI_HEADER: MODULE_APP_LAYOUT — root document shell.
// ROLE: Next.js RootLayout — owns HTML shell, Telegram/correlation bootstrap,
//   global client crash capture, and Vercel-only analytics injection.
// DEPENDENCIES: next/font, @vercel/analytics/next, local modules.
// GRACE_ANCHORS: [ROOT_LAYOUT]
// SLICE: SLICE-FRONTEND-LAYOUT
// ############################################################################
// START_MODULE_CONTRACT: M-APP-LAYOUT
// purpose: Root document shell. Bootstraps Telegram WebApp, correlation init,
//   client crash capture, Vercel-only analytics, and mounts children.
// owns:
//   - app/layout.tsx
// inputs: children — React node tree for the matched route.
// outputs: Full HTML document with metadata, fonts, scripts, and body.
// dependencies:
//   - @vercel/analytics/next (Analytics)
//   - next/font (Inter, Instrument_Serif, Lora)
//   - @/components/telegram-provider
//   - @/components/telegram-init
//   - @/components/correlation-init
//   - @/lib/analytics/vercel (shouldRenderVercelAnalyticsFromEnv)
// side_effects: Injects Telegram global, correlation tracking, error listeners,
//   and Vercel Analytics <script> tag exclusively in Vercel deployments.
// emitted_logs: none.
// invariants:
//   - Analytics renders only when shouldRenderVercelAnalyticsFromEnv() returns true.
//   - No direct business API fetch owned by RootLayout.
//   - Crash capture via window.__astroErrors and /api/_log POST.
// failure_policy: fail closed — analytics never renders outside actual Vercel.
// END_MODULE_CONTRACT: M-APP-LAYOUT
import type { Metadata, Viewport } from "next"
import { Inter, Instrument_Serif, Lora } from "next/font/google"
import { Analytics } from "@vercel/analytics/next"
import { TelegramProvider } from "@/components/telegram-provider"
import { TelegramInit } from "@/components/telegram-init"
import { CorrelationInit } from "@/components/correlation-init"
import { shouldRenderVercelAnalyticsFromEnv } from "@/lib/analytics/vercel"
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
        <script
          dangerouslySetInnerHTML={{
            __html: `
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
`,
          }}
        />
      </head>
      <body
        className={`${inter.variable} ${instrumentSerif.variable} ${loraSerif.variable} font-sans antialiased`}
      >
        <TelegramProvider>
          <TelegramInit />
          <CorrelationInit />
          {children}
        </TelegramProvider>
        {shouldRenderVercelAnalyticsFromEnv() && <Analytics />}
      </body>
    </html>
  )
}
