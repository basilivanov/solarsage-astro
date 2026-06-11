
// ############################################################################
// AI_HEADER: MODULE_DEV_ROUTE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Next.js page — app/api/auth/dev/route.ts
// owns:
//   - app/api/auth/dev/route.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

// AI_HEADER
// module: M-API-AUTH-DEV
// wave: W-2.2
// purpose: Development-only authentication endpoint for preview outside Telegram

import { NextResponse } from 'next/server'

export async function POST() {
  // Only allow in development mode
  if (process.env.NODE_ENV !== 'development') {
    return NextResponse.json(
      { detail: 'Dev auth is only available in development mode' },
      { status: 403 }
    )
  }

  // Create a mock dev user session
  // In production, this would be handled by the Telegram auth flow
  const devUser = {
    userId: 'dev-user-001',
    username: 'dev_preview',
    firstName: 'Dev',
    lastName: 'Preview',
    isPremium: false,
  }

  const response = NextResponse.json({
    ok: true,
    userId: devUser.userId,
    username: devUser.username,
    firstName: devUser.firstName,
    lastName: devUser.lastName,
  })

  // Set a simple dev cookie so the app recognizes the session
  response.cookies.set('dev_auth', 'true', {
    httpOnly: false,
    secure: false,
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * 24, // 24 hours
  })

  return response
}
