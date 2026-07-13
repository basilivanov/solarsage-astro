// ############################################################################
// AI_HEADER: FRONTEND_API_DEV_AUTH_GUARD — fail-closed local development origin validation.
// ROLE: Security-critical host and proxy-origin validation used only by dev auth and fixture route handlers.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-DEV-AUTH-GUARD
// purpose: Fail closed for non-local hosts and untrusted forwarding metadata.
// owns:
//   - lib/api/dev-auth-guard.ts
// inputs: Host header or Web Request.
// outputs: boolean local-host and unsafe-proxy decisions.
// dependencies: Web Headers, Request and URL; fixed local and allowed header sets.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - Only localhost, 127.0.0.1 and ::1 host forms are local.
//   - Forwarded, x-real-ip and unknown x-forwarded-* headers are unsafe.
//   - Forwarded host, port and protocol must agree with the request.
//   - Every x-forwarded-for address must be in the fixed local allowlist.
//   - Absence of suspicious forwarding metadata remains safe.
// failure_policy: Malformed or mismatched forwarding state returns unsafe=true; missing or non-local host returns false from isLocalDevHost.
// END_MODULE_CONTRACT: M-FRONTEND-API-DEV-AUTH-GUARD

// START_MODULE_MAP: M-FRONTEND-API-DEV-AUTH-GUARD
// public_entrypoints:
//   - isLocalDevHost
//   - hasUnsafeProxyOriginHeaders
// semantic_blocks:
//   - LOCAL_ALLOWLISTS: define accepted forwarding headers and local addresses.
//   - HOST_NORMALIZATION: normalize bracketed, named and numeric host forms.
//   - HOST_PORT_PARSE: extract an optional host port safely.
//   - FORWARDING_VALIDATION: reject unknown, inconsistent or non-local proxy metadata.
// owned_tests:
//   - __tests__/api/dev-auth-route.test.ts
//   - __tests__/guardrails/preview-isolation.test.ts
// END_MODULE_MAP: M-FRONTEND-API-DEV-AUTH-GUARD

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

export function hasUnsafeProxyOriginHeaders(request: Request): boolean {
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
