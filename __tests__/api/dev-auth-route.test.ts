import { afterEach, describe, expect, it, vi } from "vitest"
import { isLocalDevHost, POST } from "@/app/api/auth/dev/route"

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

  it.each(["x-forwarded-for", "x-forwarded-host", "x-real-ip", "forwarded"])(
    "rejects %s before proxying to the backend",
    async (headerName) => {
      vi.stubEnv("NODE_ENV", "development")
      const fetchMock = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValue(new Response("{}", { status: 200 }))

      const response = await POST(
        new Request("http://localhost:3000/api/auth/dev", {
          method: "POST",
          headers: {
            host: "localhost:3000",
            [headerName]: "203.0.113.10",
          },
        }),
      )

      expect(response.status).toBe(403)
      expect(fetchMock).not.toHaveBeenCalled()
    },
  )
})
