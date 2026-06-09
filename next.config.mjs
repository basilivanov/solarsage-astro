import { assertProductionSafety } from "./lib/env/production-guard.mjs";

// Build-time production environment check (fixes W-PROD-DEMO-GUARD)
assertProductionSafety();

/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
    ];
  },
}

export default nextConfig
