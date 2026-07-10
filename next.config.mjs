import { assertProductionSafety } from "./lib/env/production-guard.mjs";
import { resolveNextDistDir } from "./lib/env/next-dist-dir.mjs";

// Build-time production environment check (fixes W-PROD-DEMO-GUARD)
assertProductionSafety();

/**
 * Server-only API rewrite base.
 * Production always uses the canonical local API.
 * DEV_API_REWRITE_BASE_URL is read only when NODE_ENV !== "production".
 * No fixture/mock modules are imported here.
 */
function resolveApiRewriteBase() {
  const canonical = "http://127.0.0.1:8000";
  if (process.env.NODE_ENV === "production") {
    return canonical;
  }
  const override = process.env.DEV_API_REWRITE_BASE_URL?.trim();
  return override || canonical;
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: resolveNextDistDir(),
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
