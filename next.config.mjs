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

/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: resolveNextDistDir(),
  experimental: {
    // Synchronous MVP endpoints (e.g. natal report generation) legitimately
    // exceed the 30 s default rewrite proxy timeout; production nginx already
    // allows 300 s, so the fallback rewrite matches it.
    proxyTimeout: 300_000,
  },
  ...(process.env.NODE_ENV !== "production"
    ? { allowedDevOrigins: ["127.0.0.1"] }
    : {}),
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
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
