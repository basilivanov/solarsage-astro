'use client'

import { useEffect, useState } from 'react'
import { useTelegramAuth } from '@/hooks/use-telegram-auth'

interface DebugInfo {
  timestamp?: string
  dev_mode: boolean
  session_cookie_present: boolean
  session_cookie_length: number
  user_authenticated: boolean
  user_info?: {
    id: string
    tg_user_id: number  // Backend uses snake_case for debug endpoint
    tg_username?: string
    first_name?: string  // Backend uses snake_case for debug endpoint
    is_onboarded: boolean  // Backend uses snake_case for debug endpoint
  }
  cookies: string[]
  headers: {
    'user-agent'?: string
    origin?: string
    referer?: string
  }
  env: {
    python_version: string
    app_version: string
  }
  error?: string
}

export default function DebugPage() {
  const [debugInfo, setDebugInfo] = useState<DebugInfo | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const { isAuthenticated, isLoading: authLoading } = useTelegramAuth()

  useEffect(() => {
    if (authLoading) return

    fetch('/api/debug', { credentials: 'include' })
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`)
        }
        return res.text()
      })
      .then(text => {
        try {
          const data = JSON.parse(text)

          // Check if API returned an error
          if (data.error) {
            setError(`API Error: ${data.error}`)
            setDebugInfo(data)
          } else {
            setDebugInfo(data)
          }
          setLoading(false)
        } catch (e) {
          throw new Error(`Invalid JSON response: ${text.substring(0, 100)}...`)
        }
      })
      .catch(err => {
        console.error('[Debug] Fetch error:', err)
        setError(err.message)
        setLoading(false)
      })
  }, [authLoading])

  if (loading || authLoading) {
    return (
      <div className="p-4">
        <h1 className="text-2xl font-bold mb-4">Debug Info</h1>
        <p>Loading...</p>
      </div>
    )
  }

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">🔍 Debug Info</h1>

      {/* Frontend Auth Status */}
      <div className="mb-6 p-4 bg-gray-100 rounded">
        <h2 className="text-lg font-semibold mb-2">Frontend Auth</h2>
        <div className="space-y-1 text-sm">
          <div>
            <span className="font-medium">Authenticated:</span>{' '}
            <span className={isAuthenticated ? 'text-green-600' : 'text-red-600'}>
              {isAuthenticated ? '✅ Yes' : '❌ No'}
            </span>
          </div>
        </div>
      </div>

      {/* Backend Debug Info */}
      {error && (
        <div className="mb-6 p-4 bg-red-100 rounded">
          <h2 className="text-lg font-semibold mb-2 text-red-800">Error</h2>
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {debugInfo && (
        <>
          {/* Session Status */}
          <div className="mb-6 p-4 bg-gray-100 rounded">
            <h2 className="text-lg font-semibold mb-2">Backend Session</h2>
            <div className="space-y-1 text-sm">
              <div>
                <span className="font-medium">Dev Mode:</span>{' '}
                <span className={debugInfo.dev_mode ? 'text-green-600' : 'text-red-600'}>
                  {debugInfo.dev_mode ? '✅ Enabled' : '❌ Disabled'}
                </span>
              </div>
              <div>
                <span className="font-medium">Session Cookie:</span>{' '}
                <span className={debugInfo.session_cookie_present ? 'text-green-600' : 'text-red-600'}>
                  {debugInfo.session_cookie_present ? '✅ Present' : '❌ Missing'}
                </span>
              </div>
              {debugInfo.session_cookie_present && (
                <div>
                  <span className="font-medium">Cookie Length:</span> {debugInfo.session_cookie_length} chars
                </div>
              )}
              <div>
                <span className="font-medium">User Authenticated:</span>{' '}
                <span className={debugInfo.user_authenticated ? 'text-green-600' : 'text-red-600'}>
                  {debugInfo.user_authenticated ? '✅ Yes' : '❌ No'}
                </span>
              </div>
            </div>
          </div>

          {/* User Info */}
          {debugInfo.user_info && (
            <div className="mb-6 p-4 bg-gray-100 rounded">
              <h2 className="text-lg font-semibold mb-2">User Info</h2>
              <div className="space-y-1 text-sm">
                <div>
                  <span className="font-medium">ID:</span> {debugInfo.user_info.id}
                </div>
                <div>
                  <span className="font-medium">Telegram ID:</span> {debugInfo.user_info.tg_user_id}
                </div>
                {debugInfo.user_info.tg_username && (
                  <div>
                    <span className="font-medium">Telegram Username:</span> @{debugInfo.user_info.tg_username}
                  </div>
                )}
                <div>
                  <span className="font-medium">First Name:</span> {debugInfo.user_info.first_name || 'Not set'}
                </div>
                <div>
                  <span className="font-medium">Onboarded:</span>{' '}
                  <span className={debugInfo.user_info.is_onboarded ? 'text-green-600' : 'text-orange-600'}>
                    {debugInfo.user_info.is_onboarded ? '✅ Yes' : '⚠️ No'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Cookies */}
          <div className="mb-6 p-4 bg-gray-100 rounded">
            <h2 className="text-lg font-semibold mb-2">Cookies</h2>
            <div className="text-sm">
              {debugInfo.cookies.length > 0 ? (
                <ul className="list-disc list-inside">
                  {debugInfo.cookies.map(cookie => (
                    <li key={cookie}>{cookie}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-red-600">No cookies found</p>
              )}
            </div>
          </div>

          {/* Headers */}
          <div className="mb-6 p-4 bg-gray-100 rounded">
            <h2 className="text-lg font-semibold mb-2">Headers</h2>
            <div className="space-y-1 text-sm">
              <div>
                <span className="font-medium">User Agent:</span>
                <div className="text-xs break-all">{debugInfo.headers['user-agent']}</div>
              </div>
              {debugInfo.headers.origin && (
                <div>
                  <span className="font-medium">Origin:</span> {debugInfo.headers.origin}
                </div>
              )}
              {debugInfo.headers.referer && (
                <div>
                  <span className="font-medium">Referer:</span> {debugInfo.headers.referer}
                </div>
              )}
            </div>
          </div>

          {/* Environment */}
          <div className="mb-6 p-4 bg-gray-100 rounded">
            <h2 className="text-lg font-semibold mb-2">Environment</h2>
            <div className="space-y-1 text-sm">
              <div>
                <span className="font-medium">App Version:</span> {debugInfo.env.app_version}
              </div>
              <div>
                <span className="font-medium">Python:</span>
                <div className="text-xs">{debugInfo.env.python_version}</div>
              </div>
            </div>
          </div>

          {/* Timestamp */}
          {debugInfo.timestamp && (
            <div className="text-xs text-gray-500 text-center">
              Generated at: {debugInfo.timestamp}
            </div>
          )}
        </>
      )}

      {/* Actions */}
      <div className="mt-6 space-y-2">
        <button
          onClick={() => window.location.reload()}
          className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          🔄 Refresh
        </button>
        <button
          onClick={() => {
            localStorage.clear()
            window.location.href = '/'
          }}
          className="w-full px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
        >
          🗑️ Clear Storage & Restart
        </button>
      </div>
    </div>
  )
}
