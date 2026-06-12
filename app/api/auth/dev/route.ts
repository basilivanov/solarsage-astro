
// ############################################################################
// AI_HEADER: MODULE_DEV_ROUTE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Page: route
// owns:
//   - app/api/auth/dev/route.ts
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
