import { assertProductionSafety } from "./lib/env/production-guard.mjs";

// Build-time production environment check (fixes W-PROD-DEMO-GUARD)
assertProductionSafety();

/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    unoptimized: true,
  },
  // In the sandbox/preview environment we run the Next.js app standalone:
  // the FastAPI backend (apps/api) and SolarSage sidecar are not available,
  // so /api/* is served by Next.js route handlers under app/api/* (mock/demo
  // data). When NEXT_PUBLIC_DEMO_MODE=true the client bypasses most API calls
  // entirely and uses lib/demo-data.ts fixtures.
  allowedDevOrigins: [
    "127.0.0.1",
    "localhost",
    "*.space-z.ai",
    "*.preview.chat",
    "*.preview.chat",
  ],
};

export default nextConfig
