import { describe, expect, it } from "vitest"
import { isLocalDevHost } from "@/app/api/auth/dev/route"

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
})
