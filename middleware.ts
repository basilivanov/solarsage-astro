// ############################################################################
// AI_HEADER: MODULE_MIDDLEWARE_VERSIONED_ENTRY
// ROLE: Version the document entry URL with the build release sha so a WebView
//       cannot open a stale cached page after a deployment.
// DEPENDENCIES: next/server
// GRACE_ANCHORS: [VERSIONED_ENTRY, RELEASE_SHA_GUARD, DOCUMENT_REDIRECT]
// WAVE: W-CACHE-DELIVERY-HARDENING
// ############################################################################

// START_MODULE_CONTRACT: M-MIDDLEWARE-VERSIONED-ENTRY
// purpose: Redirect document requests without the current ?v=<release_sha> to
//   the same URL carrying the current release sha, without changing the hash.
// owns:
//   - middleware.ts
// inputs:
//   - NEXT_PUBLIC_RELEASE_SHA from the build/dev server environment
//   - incoming NextRequest path, query, method and fetch metadata headers
// outputs:
//   - NextResponse.next() for API, static, non-document and already-versioned requests
//   - 307 redirect to the same URL with ?v=<release_sha> for unversioned document GETs
// dependencies:
//   - next/server (NextRequest, NextResponse)
// side_effects:
//   - issues one HTTP redirect for eligible document entries
// emitted_logs: none
// invariants:
//   - empty/unknown release sha is a complete no-op (dev/preview/e2e harnesses)
//   - only GET document requests are redirected
//   - RSC/fetch navigation, API, _next, telegram-web-app.js, favicon/icon/manifest
//     and extension assets are never redirected
//   - an already-current ?v value is passed through (loop guard)
//   - every redirect response carries Cache-Control: no-store
//   - the server never reads or rewrites the URL fragment; Chromium carries it
//     across the 307 itself
// failure_policy: fail open — an unknown release sha or unrecognised request type
//   is never redirected.
// END_MODULE_CONTRACT: M-MIDDLEWARE-VERSIONED-ENTRY

// START_MODULE_MAP: M-MIDDLEWARE-VERSIONED-ENTRY
// public_entrypoints:
//   - middleware
//   - config
// semantic_blocks:
//   - RELEASE_SHA: build/dev release sha normalization and no-op guard.
//   - DOCUMENT_REQUEST: document-only detection with an RSC/fetch exclusion.
//   - ROUTE_GUARD: API/static/asset path exclusions.
//   - VERSIONED_REDIRECT: one 307 redirect with no-store on the versioned URL.
// owned_tests:
//   - e2e/versioned-entry.spec.ts
// END_MODULE_MAP: M-MIDDLEWARE-VERSIONED-ENTRY

import { NextResponse, type NextRequest } from "next/server";

const RSC_HEADERS = [
  "rsc",
  "next-router-state-tree",
  "next-router-prefetch",
  "next-router-segment-prefetch",
  "next-url",
  "x-nextjs-data",
] as const;

// START_BLOCK: RELEASE_SHA
function normalizeReleaseSha(value: string | undefined): string {
  if (typeof value !== "string") return "";
  const trimmed = value.trim();
  if (!trimmed || trimmed.toLowerCase() === "unknown") return "";
  return trimmed;
}

const RELEASE_SHA = normalizeReleaseSha(process.env.NEXT_PUBLIC_RELEASE_SHA);
// END_BLOCK: RELEASE_SHA

// START_BLOCK: DOCUMENT_REQUEST
function isDocumentRequest(request: NextRequest): boolean {
  const hasRscHeader = RSC_HEADERS.some((header) => request.headers.has(header));
  if (hasRscHeader) return false;

  const destination = request.headers.get("sec-fetch-dest")?.toLowerCase();
  if (destination === "document") return true;

  // Older WebViews do not send Sec-Fetch-* headers. Only use the Accept
  // fallback when the request did not explicitly declare another destination.
  if (destination !== null) return false;

  const accept = request.headers.get("accept")?.toLowerCase() ?? "";
  return accept.includes("text/html");
}
// END_BLOCK: DOCUMENT_REQUEST

// START_BLOCK: ROUTE_GUARD
function isExcludedPath(pathname: string): boolean {
  if (pathname === "/api" || pathname.startsWith("/api/")) return true;
  if (pathname === "/_next" || pathname.startsWith("/_next/")) return true;
  if (pathname === "/telegram-web-app.js") return true;
  if (pathname === "/favicon.ico") return true;
  if (pathname === "/icon" || pathname.startsWith("/icon.")) return true;
  if (pathname === "/manifest" || pathname.startsWith("/manifest.")) return true;

  // Any other path with a file extension is an asset, not an app document.
  return /\.[^/]+$/.test(pathname);
}
// END_BLOCK: ROUTE_GUARD

// START_BLOCK: VERSIONED_REDIRECT
export function middleware(request: NextRequest): NextResponse {
  // Unknown sha means the build cannot safely version URLs: stay completely
  // transparent so local/e2e/preview harnesses keep their existing behavior.
  if (!RELEASE_SHA) return NextResponse.next();
  if (request.method !== "GET") return NextResponse.next();
  if (isExcludedPath(request.nextUrl.pathname)) return NextResponse.next();
  if (!isDocumentRequest(request)) return NextResponse.next();
  if (request.nextUrl.searchParams.get("v") === RELEASE_SHA) {
    return NextResponse.next();
  }

  const url = request.nextUrl.clone();
  url.searchParams.set("v", RELEASE_SHA);
  const response = NextResponse.redirect(url, 307);
  response.headers.set("Cache-Control", "no-store");
  return response;
}
// END_BLOCK: VERSIONED_REDIRECT

export const config = {
  matcher: [
    // App pages only. API, Next internals, extension assets and the named
    // icon/manifest/telegram files are excluded; the middleware repeats these
    // guards so a matcher drift cannot redirect an asset.
    "/((?!api|_next/static|_next/image|_next/data|telegram-web-app[.]js|favicon[.]ico|icon[.]|manifest[.]|.*[.].*).*)",
  ],
};
