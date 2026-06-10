import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import NatalReadingPage from "@/app/(grace)/readings/natal/page";
import type { NatalPreviewRead } from "@/lib/contracts/natal";

const mockFetch = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/readings/natal",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("lucide-react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("lucide-react")>();
  const FakeIcon = (props: Record<string, unknown>) =>
    React.createElement("span", { "data-testid": "icon" });
  return {
    ...actual,
    ChevronLeft: FakeIcon,
    Sparkles: FakeIcon,
    Lock: FakeIcon,
  };
});

vi.mock("next/link", () => ({
  default: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("@/lib/api/natal", () => ({
  fetchNatalPreview: (...args: unknown[]) => mockFetch(...args),
}));

const russianPreview: NatalPreviewRead = {
  meta: {
    name: "Анна",
    birthDate: "1990-06-15",
    birthTime: "14:30",
    birthCity: "Москва",
    houseSystem: "Placidus",
    ascSign: "Раке",
    ascDegree: 12.5,
    gender: "female",
  },
  highlights: [
    { id: "asc", title: "Асцендент", value: "Раке", description: "Как ты входишь в контакт и проявляешься внешне." },
    { id: "sun-sign", title: "Солнце", value: "Скорпионе", description: "Твой базовый вектор личности." },
    { id: "moon-sign", title: "Луна", value: "Льве", description: "Эмоциональный отклик." },
  ],
  spheres: [
    { id: "love", title: "Отношения", score: 4.5, rank: 1, description: "Сильная сфера." },
    { id: "money", title: "Деньги", score: 3.8, rank: 2, description: "Хороший потенциал." },
  ],
  planets: [
    { id: "sun", name: "Солнце", sign: "Скорпион", house: 4, score: 4.96, description: "Солнце в Скорпионе, 4 дом." },
    { id: "moon", name: "Луна", sign: "Лев", house: 1, score: 3.2, description: "Луна во Льве, 1 дом." },
    { id: "mercury", name: "Меркурий", sign: "Весы", house: 3, score: 2.1, description: "Меркурий в Весах, 3 дом." },
  ],
  chapters: [
    { id: "love", eyebrow: "Полный разбор", title: "Отношения и близость", locked: true, description: "Описание." },
    { id: "money", eyebrow: "Полный разбор", title: "Деньги и стратегия роста", locked: true, description: "Описание." },
  ],
  personalHook: "Ты собрана: с ASC в Раке и Солнцем в Скорпионе у тебя особенно заметна тема «Отношения».",
  calculationStats: {
    planetsCount: 5,
    housesCount: 8,
    aspectsCount: 12,
    spheresCount: 7,
    specialPointsCount: 4,
    scoringFactorsCount: 15,
    dignityFactorsCount: 0,
    totalFactorsCount: 51,
    displayLabel: "51 факторов карты",
  },
  salesBullets: [
    "Поймёшь, где в карте ты уже проявлена сильнее всего.",
    "Увидишь приоритетные сферы, а не разрозненные факты.",
  ],
  fullReportAvailable: false,
  fullReportPriceKopecks: 99900,
};

const ENGLISH_SIGNS = ["Cancer", "Scorpio", "Leo", "Libra", "Sagittarius", "Aries", "Taurus", "Gemini", "Virgo", "Capricorn", "Aquarius", "Pisces"];

describe("NatalReadingPage — no English signs in UI", () => {
  it("renders Russian sign names and no English sign names", async () => {
    mockFetch.mockResolvedValue({ ok: true, data: russianPreview });

    render(
      <React.Suspense fallback={<div>loading</div>}>
        <NatalReadingPage />
      </React.Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText(/натальная карта/i)).toBeTruthy();
    }, { timeout: 3000 });

    const body = document.body.textContent || "";

    for (const sign of ENGLISH_SIGNS) {
      expect(body).not.toContain(sign);
    }

    expect(body).toContain("Скорпион");
    expect(body).toContain("Лев");
    expect(body).toContain("Весы");
  });
});
