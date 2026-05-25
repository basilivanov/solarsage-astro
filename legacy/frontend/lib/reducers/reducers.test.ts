/**
 * Тесты reducer'ов — чистая бизнес-логика без jsdom.
 *
 * Эти тесты гарантируют, что:
 * 1. State transitions работают корректно
 * 2. Валидация шагов онбординга корректна
 * 3. Chat events обрабатываются правильно
 */

import { describe, it, expect } from "vitest"

import {
  chatReducer,
  initialChatState,
  selectLastMessage,
  selectIsStreaming,
  selectCanSend,
  type ChatState,
} from "./chat-reducer"

import {
  onboardingReducer,
  initialOnboardingState,
  isValidBirthDate,
  isValidBirthTime,
  isStepValid,
  selectProgress,
  selectIsFirstStep,
  selectIsLastStep,
  type OnboardingState,
} from "./onboarding-reducer"

// ---------------------------------------------------------------------------
// Chat Reducer Tests
// ---------------------------------------------------------------------------

describe("chatReducer", () => {
  describe("hydrated", () => {
    it("sets messages and hydrated flag", () => {
      const messages = [
        { id: "1", role: "user" as const, content: "Hi", createdAt: Date.now() },
      ]
      const next = chatReducer(initialChatState, { type: "hydrated", messages })
      expect(next.messages).toEqual(messages)
      expect(next.hydrated).toBe(true)
    })
  })

  describe("user_sent", () => {
    it("adds user message and sets pending", () => {
      const now = Date.now()
      const next = chatReducer(initialChatState, {
        type: "user_sent",
        id: "msg-1",
        text: "Hello",
        createdAt: now,
      })

      expect(next.messages).toHaveLength(1)
      expect(next.messages[0].role).toBe("user")
      expect(next.messages[0].content).toBe("Hello")
      expect(next.pending).toBe(true)
    })

    it("ignores if already pending", () => {
      const pendingState: ChatState = { ...initialChatState, pending: true }
      const next = chatReducer(pendingState, {
        type: "user_sent",
        id: "msg-2",
        text: "Another",
        createdAt: Date.now(),
      })
      expect(next.messages).toHaveLength(0)
    })
  })

  describe("stream_started", () => {
    it("adds empty assistant message and sets streamingId", () => {
      const now = Date.now()
      const next = chatReducer(initialChatState, {
        type: "stream_started",
        id: "assistant-1",
        createdAt: now,
      })

      expect(next.messages).toHaveLength(1)
      expect(next.messages[0].role).toBe("assistant")
      expect(next.messages[0].content).toBe("")
      expect(next.streamingId).toBe("assistant-1")
    })
  })

  describe("token", () => {
    it("updates streaming message content", () => {
      const state: ChatState = {
        ...initialChatState,
        messages: [
          { id: "assistant-1", role: "assistant", content: "Hello", createdAt: Date.now() },
        ],
        streamingId: "assistant-1",
      }
      const next = chatReducer(state, {
        type: "token",
        id: "assistant-1",
        content: "Hello world",
      })

      expect(next.messages[0].content).toBe("Hello world")
    })

    it("ignores token for different id", () => {
      const state: ChatState = {
        ...initialChatState,
        messages: [
          { id: "assistant-1", role: "assistant", content: "Hello", createdAt: Date.now() },
        ],
        streamingId: "assistant-1",
      }
      const next = chatReducer(state, {
        type: "token",
        id: "different-id",
        content: "Should not apply",
      })

      expect(next.messages[0].content).toBe("Hello")
    })
  })

  describe("done", () => {
    it("clears pending and streamingId", () => {
      const state: ChatState = {
        ...initialChatState,
        pending: true,
        streamingId: "assistant-1",
      }
      const next = chatReducer(state, { type: "done", id: "assistant-1" })

      expect(next.pending).toBe(false)
      expect(next.streamingId).toBeNull()
    })
  })

  describe("error", () => {
    it("adds error message and clears pending", () => {
      const state: ChatState = { ...initialChatState, pending: true }
      const errorMsg = {
        id: "error-1",
        role: "assistant" as const,
        content: "Error occurred",
        createdAt: Date.now(),
      }
      const next = chatReducer(state, { type: "error", message: errorMsg })

      expect(next.messages).toHaveLength(1)
      expect(next.pending).toBe(false)
    })
  })

  describe("reset", () => {
    it("resets to initial state but keeps hydrated", () => {
      const state: ChatState = {
        messages: [{ id: "1", role: "user", content: "Hi", createdAt: Date.now() }],
        pending: true,
        streamingId: "x",
        hydrated: true,
      }
      const next = chatReducer(state, { type: "reset" })

      expect(next.messages).toHaveLength(0)
      expect(next.pending).toBe(false)
      expect(next.streamingId).toBeNull()
      expect(next.hydrated).toBe(true)
    })
  })

  describe("selectors", () => {
    it("selectLastMessage returns last message", () => {
      const state: ChatState = {
        ...initialChatState,
        messages: [
          { id: "1", role: "user", content: "First", createdAt: 1 },
          { id: "2", role: "assistant", content: "Second", createdAt: 2 },
        ],
      }
      expect(selectLastMessage(state)?.content).toBe("Second")
    })

    it("selectIsStreaming returns true when streaming", () => {
      const state: ChatState = { ...initialChatState, streamingId: "x" }
      expect(selectIsStreaming(state)).toBe(true)
    })

    it("selectCanSend returns false when pending", () => {
      const state: ChatState = { ...initialChatState, pending: true }
      expect(selectCanSend(state)).toBe(false)
    })
  })
})

// ---------------------------------------------------------------------------
// Onboarding Reducer Tests
// ---------------------------------------------------------------------------

describe("onboardingReducer", () => {
  describe("navigation", () => {
    it("next advances to next step", () => {
      const next = onboardingReducer(initialOnboardingState, { type: "next" })
      expect(next.step).toBe("birth") // welcome -> birth
    })

    it("back goes to previous step", () => {
      const state: OnboardingState = { ...initialOnboardingState, step: "birth" }
      const next = onboardingReducer(state, { type: "back" })
      expect(next.step).toBe("welcome")
    })

    it("back does nothing on first step", () => {
      const next = onboardingReducer(initialOnboardingState, { type: "back" })
      expect(next.step).toBe("welcome")
    })

    it("skip jumps to done", () => {
      const next = onboardingReducer(initialOnboardingState, { type: "skip" })
      expect(next.step).toBe("done")
    })
  })

  describe("set_birth_date", () => {
    it("updates birth date", () => {
      const next = onboardingReducer(initialOnboardingState, {
        type: "set_birth_date",
        value: { day: "15", month: "06", year: "1990" },
      })
      expect(next.birthDate).toEqual({ day: "15", month: "06", year: "1990" })
    })
  })

  describe("set_birth_time", () => {
    it("updates birth time", () => {
      const next = onboardingReducer(initialOnboardingState, {
        type: "set_birth_time",
        value: { hours: "14", minutes: "30", unknown: false },
      })
      expect(next.birthTime).toEqual({ hours: "14", minutes: "30", unknown: false })
    })
  })

  describe("set_birth_place", () => {
    it("updates birth place", () => {
      const next = onboardingReducer(initialOnboardingState, {
        type: "set_birth_place",
        value: "Moscow",
      })
      expect(next.birthPlace).toBe("Moscow")
    })
  })

  describe("reset", () => {
    it("resets to initial state", () => {
      const state: OnboardingState = {
        ...initialOnboardingState,
        step: "place",
        birthPlace: "Moscow",
      }
      const next = onboardingReducer(state, { type: "reset" })
      expect(next).toEqual(initialOnboardingState)
    })
  })
})

// ---------------------------------------------------------------------------
// Validation Functions Tests
// ---------------------------------------------------------------------------

describe("isValidBirthDate", () => {
  it("returns true for valid date", () => {
    expect(isValidBirthDate({ day: "15", month: "06", year: "1990" })).toBe(true)
  })

  it("returns false for empty fields", () => {
    expect(isValidBirthDate({ day: "", month: "06", year: "1990" })).toBe(false)
    expect(isValidBirthDate({ day: "15", month: "", year: "1990" })).toBe(false)
    expect(isValidBirthDate({ day: "15", month: "06", year: "" })).toBe(false)
  })

  it("returns false for invalid day", () => {
    expect(isValidBirthDate({ day: "32", month: "06", year: "1990" })).toBe(false)
    expect(isValidBirthDate({ day: "0", month: "06", year: "1990" })).toBe(false)
  })

  it("returns false for invalid month", () => {
    expect(isValidBirthDate({ day: "15", month: "13", year: "1990" })).toBe(false)
    expect(isValidBirthDate({ day: "15", month: "0", year: "1990" })).toBe(false)
  })

  it("returns false for future year", () => {
    expect(isValidBirthDate({ day: "15", month: "06", year: "2030" })).toBe(false)
  })

  it("returns false for very old year", () => {
    expect(isValidBirthDate({ day: "15", month: "06", year: "1800" })).toBe(false)
  })

  it("validates February 29 correctly", () => {
    // 2020 is a leap year
    expect(isValidBirthDate({ day: "29", month: "02", year: "2020" })).toBe(true)
    // 2019 is not a leap year
    expect(isValidBirthDate({ day: "29", month: "02", year: "2019" })).toBe(false)
  })
})

describe("isValidBirthTime", () => {
  it("returns true for valid time", () => {
    expect(isValidBirthTime({ hours: "14", minutes: "30", unknown: false })).toBe(true)
  })

  it("returns true if unknown is true", () => {
    expect(isValidBirthTime({ hours: "", minutes: "", unknown: true })).toBe(true)
  })

  it("returns false for invalid hours", () => {
    expect(isValidBirthTime({ hours: "25", minutes: "30", unknown: false })).toBe(false)
    expect(isValidBirthTime({ hours: "-1", minutes: "30", unknown: false })).toBe(false)
  })

  it("returns false for invalid minutes", () => {
    expect(isValidBirthTime({ hours: "14", minutes: "60", unknown: false })).toBe(false)
    expect(isValidBirthTime({ hours: "14", minutes: "-1", unknown: false })).toBe(false)
  })

  it("returns false for empty fields when not unknown", () => {
    expect(isValidBirthTime({ hours: "", minutes: "30", unknown: false })).toBe(false)
    expect(isValidBirthTime({ hours: "14", minutes: "", unknown: false })).toBe(false)
  })

  it("accepts edge values", () => {
    expect(isValidBirthTime({ hours: "0", minutes: "0", unknown: false })).toBe(true)
    expect(isValidBirthTime({ hours: "23", minutes: "59", unknown: false })).toBe(true)
  })
})

describe("isStepValid", () => {
  it("welcome is always valid", () => {
    expect(isStepValid(initialOnboardingState)).toBe(true)
  })

  it("birth requires valid date and time", () => {
    const invalidDate: OnboardingState = {
      ...initialOnboardingState,
      step: "birth",
    }
    expect(isStepValid(invalidDate)).toBe(false)

    const validDateInvalidTime: OnboardingState = {
      ...invalidDate,
      birthDate: { day: "15", month: "06", year: "1990" },
    }
    expect(isStepValid(validDateInvalidTime)).toBe(false)

    const valid: OnboardingState = {
      ...validDateInvalidTime,
      birthTime: { hours: "14", minutes: "30", unknown: false },
    }
    expect(isStepValid(valid)).toBe(true)
  })

  it("place requires birth place", () => {
    const invalid: OnboardingState = {
      ...initialOnboardingState,
      step: "place",
    }
    expect(isStepValid(invalid)).toBe(false)

    const validSameAsBirth: OnboardingState = {
      ...invalid,
      birthPlace: "Moscow",
      sameAsBirth: true,
    }
    expect(isStepValid(validSameAsBirth)).toBe(true)

    const needsCurrentCity: OnboardingState = {
      ...invalid,
      birthPlace: "Moscow",
      sameAsBirth: false,
    }
    expect(isStepValid(needsCurrentCity)).toBe(false)

    const validWithCurrentCity: OnboardingState = {
      ...needsCurrentCity,
      currentCity: "Berlin",
    }
    expect(isStepValid(validWithCurrentCity)).toBe(true)
  })
})

describe("selectors", () => {
  it("selectProgress returns correct percentage", () => {
    expect(selectProgress(initialOnboardingState)).toBe(0) // welcome
    expect(selectProgress({ ...initialOnboardingState, step: "done" })).toBe(100)
  })

  it("selectIsFirstStep returns true for welcome", () => {
    expect(selectIsFirstStep(initialOnboardingState)).toBe(true)
    expect(selectIsFirstStep({ ...initialOnboardingState, step: "birth" })).toBe(false)
  })

  it("selectIsLastStep returns true for done", () => {
    expect(selectIsLastStep(initialOnboardingState)).toBe(false)
    expect(selectIsLastStep({ ...initialOnboardingState, step: "done" })).toBe(true)
  })
})
