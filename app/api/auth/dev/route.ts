
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
import {
  hasUnsafeProxyOriginHeaders,
  isLocalDevHost,
} from '@/lib/api/dev-auth-guard'

export async function POST(request: Request) {
  // Only allow in development mode
  if (process.env.NODE_ENV !== 'development') {
    return NextResponse.json(
      { detail: 'Dev auth is only available in development mode' },
      { status: 403 }
    )
  }

  if (!isLocalDevHost(request.headers.get('host'))) {
    return NextResponse.json(
      { detail: 'Dev auth is only available on localhost' },
      { status: 403 }
    )
  }

  if (hasUnsafeProxyOriginHeaders(request)) {
    return NextResponse.json(
      { detail: 'Dev auth is only available for direct local requests' },
      { status: 403 }
    )
  }

  const backendResponse = await fetch('http://127.0.0.1:8000/api/auth/dev', {
    method: 'POST',
  })

  const headers = new Headers()
  const contentType = backendResponse.headers.get('content-type')
  const setCookie = backendResponse.headers.get('set-cookie')

  if (contentType) {
    headers.set('content-type', contentType)
  }
  if (setCookie) {
    headers.set('set-cookie', setCookie)
  }

  return new NextResponse(await backendResponse.text(), {
    status: backendResponse.status,
    headers,
  })
}
