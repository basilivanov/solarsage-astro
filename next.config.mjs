import { assertProductionSafety } from "./lib/env/production-guard.mjs";
import { resolveNextDistDir } from "./lib/env/next-dist-dir.mjs";

// Build-time production environment check (fixes W-PROD-DEMO-GUARD)
assertProductionSafety();

/**
 * Server-only API rewrite base.
 * Production uses the server-only PROD_API_REWRITE_BASE_URL when set
 * (canonical Compose sets exactly http://api:8000) and otherwise falls back
 * to the canonical local API http://127.0.0.1:8000.
 * DEV_API_REWRITE_BASE_URL is read only when NODE_ENV !== "production".
 * No fixture/mock modules are imported here.
 */
function resolveApiRewriteBase() {
  const canonical = "http://127.0.0.1:8000";
  if (process.env.NODE_ENV === "production") {
    const internal = process.env.PROD_API_REWRITE_BASE_URL?.trim();
    return internal || canonical;
  }
  const override = process.env.DEV_API_REWRITE_BASE_URL?.trim();
  return override || canonical;
}

/**
 * C2 (dev-only experiment): make app document HTML ineligible for the WebView
 * page cache. The dev frontend is built with NODE_ENV=production, so the flag
 * (not NODE_ENV) is the gate. Production Docker CI never sets
 * ENTRY_HTML_NO_STORE, so this returns [] there.
 *
 * Keep this list to app document routes: API, _next assets, icons and other
 * file-extension paths must never receive the no-store header.
 */
const ENTRY_HTML_NO_STORE_SOURCES = [
  "/",
  "/today",
  "/day/:path*",
  "/calendar",
  "/chat",
  "/checkin",
  "/debug",
  "/debug-auth",
  "/onboarding",
  "/profile",
  "/readings/:path*",
  "/reset",
  "/sandbox/:path*",
  "/synastry",
  "/test-hook",
];

function entryHtmlNoStoreHeaders() {
  if (process.env.ENTRY_HTML_NO_STORE !== "1") return [];
  return ENTRY_HTML_NO_STORE_SOURCES.map((source) => ({
    source,
    headers: [{ key: "Cache-Control", value: "no-store" }],
  }));
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: resolveNextDistDir(),
  experimental: {
    // Synchronous MVP endpoints (e.g. natal report generation) legitimately
    // exceed the 30 s default rewrite proxy timeout and can pass 300 s on
    // slow candidates (observed >360 s first pass); production nginx already
    // allows 300 s, so the fallback rewrite covers the full 600 s budget the
    // E2E generation wait uses.
    proxyTimeout: 600_000,
  },
  ...(process.env.NODE_ENV !== "production"
    ? {
        allowedDevOrigins: [
          "127.0.0.1",
          // Optional Cloudflare quick-tunnel hostname for sandbox previews (no scheme).
          ...(process.env.SANDBOX_ALLOWED_DEV_ORIGIN ? [process.env.SANDBOX_ALLOWED_DEV_ORIGIN] : []),
        ],
      }
    : {}),
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async headers() {
    return entryHtmlNoStoreHeaders();
  },
  async redirects() {
    // The root page lives under the client (grace) layout, so its server
    // redirect() is streamed as a 200 RSC instruction in Next 16. Handle the
    // compatibility entry at the framework layer to guarantee a real 307.
    return [
      {
        source: "/",
        destination: "/day/today",
        permanent: false,
      },
    ];
  },
  async rewrites() {
    const apiBase = resolveApiRewriteBase();
    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
};

export default nextConfig
