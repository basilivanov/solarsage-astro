import { describe, it, expect } from "vitest"
import {
  CheckinMoodSchema,
  CheckinAccuracySchema,
  CheckinEnergySchema,
  CHECKIN_TAGS,
  CheckinCreateSchema,
  CheckinResponseSchema,
  MOOD_OPTIONS,
  ACCURACY_OPTIONS,
  ENERGY_OPTIONS,
  TAG_OPTIONS,
} from "@/lib/contracts/checkin"

describe("lib/contracts/checkin — схемы", () => {
  describe("CheckinMoodSchema", () => {
    it("принимает 1-5", () => {
      for (let m = 1; m <= 5; m++) {
        expect(CheckinMoodSchema.safeParse(m).success).toBe(true)
      }
    })
    it("отвергает 0", () => {
      expect(CheckinMoodSchema.safeParse(0).success).toBe(false)
    })
    it("отвергает 6", () => {
      expect(CheckinMoodSchema.safeParse(6).success).toBe(false)
    })
    it("отвергает строку", () => {
      expect(CheckinMoodSchema.safeParse("3").success).toBe(false)
    })
  })

  describe("CheckinAccuracySchema", () => {
    it("принимает miss/partial/hit", () => {
      expect(CheckinAccuracySchema.safeParse("miss").success).toBe(true)
      expect(CheckinAccuracySchema.safeParse("partial").success).toBe(true)
      expect(CheckinAccuracySchema.safeParse("hit").success).toBe(true)
    })
    it("отвергает невалидное значение", () => {
      expect(CheckinAccuracySchema.safeParse("maybe").success).toBe(false)
    })
  })

  describe("CheckinEnergySchema", () => {
    it("принимает 1-5", () => {
      for (let e = 1; e <= 5; e++) {
        expect(CheckinEnergySchema.safeParse(e).success).toBe(true)
      }
    })
    it("отвергает 0 и 6", () => {
      expect(CheckinEnergySchema.safeParse(0).success).toBe(false)
      expect(CheckinEnergySchema.safeParse(6).success).toBe(false)
    })
  })

  describe("CHECKIN_TAGS", () => {
    it("содержит 19 тегов", () => {
      expect(CHECKIN_TAGS).toHaveLength(19)
    })
    it("включает work_win, money_in, calm", () => {
      expect(CHECKIN_TAGS).toContain("work_win")
      expect(CHECKIN_TAGS).toContain("money_in")
      expect(CHECKIN_TAGS).toContain("calm")
    })
  })

  describe("CheckinCreateSchema", () => {
    it("принимает валидный объект", () => {
      const valid = {
        targetDate: "2026-06-26",
        mood: 4,
        accuracy: "hit",
        energy: 3,
        tags: ["calm", "focused"],
        note: "Хороший день",
      }
      expect(CheckinCreateSchema.safeParse(valid).success).toBe(true)
    })
    it("отвергает невалидную дату", () => {
      const invalid = { targetDate: "26-06-2026", mood: 4 }
      expect(CheckinCreateSchema.safeParse(invalid).success).toBe(false)
    })
    it("отвергает mood > 5", () => {
      const invalid = { targetDate: "2026-06-26", mood: 10 }
      expect(CheckinCreateSchema.safeParse(invalid).success).toBe(false)
    })
    it("отвергает невалидный тег", () => {
      const invalid = {
        targetDate: "2026-06-26",
        mood: 3,
        tags: ["invalid_tag"],
      }
      expect(CheckinCreateSchema.safeParse(invalid).success).toBe(false)
    })
    it("note maxLength 500", () => {
      const longNote = "а".repeat(501)
      const invalid = { targetDate: "2026-06-26", mood: 3, note: longNote }
      expect(CheckinCreateSchema.safeParse(invalid).success).toBe(false)
    })
    it("принимает note = 500 символов", () => {
      const note = "а".repeat(500)
      const valid = { targetDate: "2026-06-26", mood: 3, note }
      expect(CheckinCreateSchema.safeParse(valid).success).toBe(true)
    })
  })

  describe("CheckinResponseSchema", () => {
    it("принимает валидный ответ", () => {
      const valid = {
        id: 1,
        targetDate: "2026-06-26",
        mood: 4,
        accuracy: "hit",
        energy: 3,
        tags: ["calm"],
        note: null,
        streak: 5,
        filledAt: null,
        createdAt: "2026-06-26T18:00:00Z",
      }
      expect(CheckinResponseSchema.safeParse(valid).success).toBe(true)
    })
  })
})

describe("lib/contracts/checkin — UI опции", () => {
  describe("MOOD_OPTIONS", () => {
    it("5 вариантов", () => {
      expect(MOOD_OPTIONS).toHaveLength(5)
    })
    it("значения 1-5", () => {
      MOOD_OPTIONS.forEach((opt, i) => {
        expect(opt.value).toBe(i + 1)
      })
    })
    it("каждый имеет emoji и label", () => {
      MOOD_OPTIONS.forEach((opt) => {
        expect(typeof opt.emoji).toBe("string")
        expect(opt.emoji.length).toBeGreaterThan(0)
        expect(typeof opt.label).toBe("string")
      })
    })
  })

  describe("ACCURACY_OPTIONS", () => {
    it("3 варианта", () => {
      expect(ACCURACY_OPTIONS).toHaveLength(3)
    })
    it("значения miss/partial/hit", () => {
      const values = ACCURACY_OPTIONS.map((o) => o.value)
      expect(values).toEqual(["miss", "partial", "hit"])
    })
  })

  describe("ENERGY_OPTIONS", () => {
    it("5 вариантов", () => {
      expect(ENERGY_OPTIONS).toHaveLength(5)
    })
    it("значения 1-5", () => {
      ENERGY_OPTIONS.forEach((opt, i) => {
        expect(opt.value).toBe(i + 1)
      })
    })
    it("каждый имеет emoji и label", () => {
      ENERGY_OPTIONS.forEach((opt) => {
        expect(typeof opt.emoji).toBe("string")
        expect(typeof opt.label).toBe("string")
      })
    })
  })

  describe("TAG_OPTIONS", () => {
    it("длина = CHECKIN_TAGS", () => {
      expect(TAG_OPTIONS).toHaveLength(CHECKIN_TAGS.length)
    })
    it("каждый тег имеет emoji и label", () => {
      TAG_OPTIONS.forEach((opt) => {
        expect(typeof opt.value).toBe("string")
        expect(typeof opt.emoji).toBe("string")
        expect(typeof opt.label).toBe("string")
      })
    })
  })
})
