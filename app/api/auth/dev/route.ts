
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

const NEXT_FORWARDED_HEADERS = new Set([
  'x-forwarded-for',
  'x-forwarded-host',
  'x-forwarded-port',
  'x-forwarded-proto',
])
const LOCAL_FORWARDED_ADDRESSES = new Set([
  '127.0.0.1',
  '::1',
  '::ffff:127.0.0.1',
  'localhost',
])

export function isLocalDevHost(hostHeader: string | null): boolean {
  if (!hostHeader) {
    return false
  }

  const host = hostHeader.trim().toLowerCase()
  let hostname = host

  if (host.startsWith('[')) {
    const endBracket = host.indexOf(']')
    hostname = endBracket === -1 ? host : host.slice(1, endBracket)
  } else if (host !== '::1') {
    hostname = host.split(':', 1)[0]
  }

  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1'
}

function hostPort(hostHeader: string): string | null {
  const host = hostHeader.trim()

  if (host.startsWith('[')) {
    const endBracket = host.indexOf(']')
    const suffix = endBracket === -1 ? '' : host.slice(endBracket + 1)
    return suffix.startsWith(':') ? suffix.slice(1) : null
  }

  if (host === '::1') {
    return null
  }

  const separator = host.lastIndexOf(':')
  return separator === -1 ? null : host.slice(separator + 1)
}

function hasUnsafeProxyOriginHeaders(request: Request): boolean {
  const headers = request.headers

  if (headers.has('forwarded') || headers.has('x-real-ip')) {
    return true
  }

  for (const header of headers.keys()) {
    const name = header.toLowerCase()
    if (name.startsWith('x-forwarded-') && !NEXT_FORWARDED_HEADERS.has(name)) {
      return true
    }
  }

  const host = headers.get('host')?.trim().toLowerCase()
  const forwardedHost = headers.get('x-forwarded-host')?.trim().toLowerCase()
  if (
    forwardedHost !== undefined &&
    (!host || forwardedHost !== host || !isLocalDevHost(forwardedHost))
  ) {
    return true
  }

  const forwardedPort = headers.get('x-forwarded-port')?.trim()
  if (
    forwardedPort !== undefined &&
    (!host || !/^\d+$/.test(forwardedPort) || forwardedPort !== hostPort(host))
  ) {
    return true
  }

  const forwardedProto = headers.get('x-forwarded-proto')?.trim().toLowerCase()
  if (forwardedProto !== undefined) {
    const requestProto = new URL(request.url).protocol.slice(0, -1).toLowerCase()
    if (
      !['http', 'https'].includes(requestProto) ||
      forwardedProto !== requestProto
    ) {
      return true
    }
  }

  const forwardedFor = headers.get('x-forwarded-for')
  if (forwardedFor !== null) {
    const addresses = forwardedFor
      .split(',')
      .map((address) => address.trim().toLowerCase())
    if (
      addresses.length === 0 ||
      addresses.some(
        (address) => !address || !LOCAL_FORWARDED_ADDRESSES.has(address),
      )
    ) {
      return true
    }
  }

  return false
}

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
