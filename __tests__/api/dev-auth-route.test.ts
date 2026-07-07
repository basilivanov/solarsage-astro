import { afterEach, describe, expect, it, vi } from "vitest"
import { POST } from "@/app/api/auth/dev/route"
import { isLocalDevHost } from "@/lib/api/dev-auth-guard"

afterEach(() => {
  vi.unstubAllEnvs()
  vi.restoreAllMocks()
})

describe("dev auth route host guard", () => {
  it("allows localhost and loopback hosts", () => {
    expect(isLocalDevHost("localhost:3000")).toBe(true)
    expect(isLocalDevHost("127.0.0.1:3000")).toBe(true)
    expect(isLocalDevHost("[::1]:3000")).toBe(true)
  })

  it("rejects public hosts", () => {
    expect(isLocalDevHost("dev.astro.vasiliy-ivanov.ru")).toBe(false)
    expect(isLocalDevHost("test.astro.vasiliy-ivanov.ru")).toBe(false)
  })

  it("allows direct local Next-synthesized forwarded headers", async () => {
    vi.stubEnv("NODE_ENV", "development")
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response('{"ok":true}', { status: 200 }))

    const response = await POST(
      new Request("http://localhost:3000/api/auth/dev", {
        method: "POST",
        headers: {
          host: "localhost:3000",
          "x-forwarded-host": "localhost:3000",
          "x-forwarded-port": "3000",
          "x-forwarded-proto": "http",
          "x-forwarded-for": "127.0.0.1, ::ffff:127.0.0.1",
        },
      }),
    )

    expect(response.status).toBe(200)
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/auth/dev",
      { method: "POST" },
    )
  })

  it.each([
    [
      "public x-forwarded-host",
      { "x-forwarded-host": "dev.astro.vasiliy-ivanov.ru" },
    ],
    ["public x-forwarded-for", { "x-forwarded-for": "203.0.113.10" }],
    ["unexpected x-forwarded header", { "x-forwarded-prefix": "/api" }],
    ["x-real-ip", { "x-real-ip": "127.0.0.1" }],
    [
      "forwarded",
      { forwarded: "for=127.0.0.1;proto=http;host=localhost:3000" },
    ],
  ])(
    "rejects %s before proxying to the backend",
    async (_caseName, forwardedHeaders) => {
      vi.stubEnv("NODE_ENV", "development")
      const fetchMock = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValue(new Response("{}", { status: 200 }))

      const response = await POST(
        new Request("http://localhost:3000/api/auth/dev", {
          method: "POST",
          headers: {
            host: "localhost:3000",
            ...forwardedHeaders,
          },
        }),
      )

      expect(response.status).toBe(403)
      expect(fetchMock).not.toHaveBeenCalled()
    },
  )
})
