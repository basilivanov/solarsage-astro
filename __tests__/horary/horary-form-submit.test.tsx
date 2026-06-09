import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { HoraryForm } from "@/components/readings/horary/horary-form";

function renderForm(props: Record<string, unknown> = {}) {
  return render(
    <HoraryForm
      hasSpendableCredit={true}
      onSubmit={vi.fn()}
      {...props}
    />
  );
}

describe("HoraryForm — blocked reason on invalid submit", () => {
  it("shows blocked reason when location is missing but text is valid", () => {
    renderForm();
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "Выйду ли я замуж в этом году?" } });
    const button = screen.getByRole("button", { name: /Получить ответ карты/ });
    fireEvent.click(button);
    expect(screen.getByTestId("horary-blocked-reason")).toBeTruthy();
    expect(screen.getByTestId("horary-blocked-reason").textContent).toMatch(/Укажи место вопроса/);
  });

  it("shows blocked reason when text is too short", () => {
    renderForm({
      profileCurrentCity: "Москва",
      profileCurrentLat: 55.75,
      profileCurrentLon: 37.62,
      profileCurrentTz: "Europe/Moscow",
    });
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "ab" } });
    const button = screen.getByRole("button", { name: /Получить ответ карты/ });
    fireEvent.click(button);
    expect(screen.getByTestId("horary-blocked-reason")).toBeTruthy();
    expect(screen.getByTestId("horary-blocked-reason").textContent).toMatch(/Напиши вопрос/);
  });

  it("shows blocked reason when no spendable credit and text/place are valid", () => {
    render(
      <HoraryForm
        hasSpendableCredit={false}
        onSubmit={vi.fn()}
        profileCurrentCity="Москва"
        profileCurrentLat={55.75}
        profileCurrentLon={37.62}
        profileCurrentTz="Europe/Moscow"
      />
    );
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "Выйду ли я замуж в этом году?" } });
    const button = screen.getByRole("button", { name: /Получить ответ карты/ });
    fireEvent.click(button);
    expect(screen.getByTestId("horary-blocked-reason")).toBeTruthy();
    expect(screen.getByTestId("horary-blocked-reason").textContent).toMatch(/хорарный вопрос/);
  });
});

describe("HoraryForm — submit API error", () => {
  it("shows submit error when submitError prop is set", () => {
    renderForm({ submitError: "Недостаточно хорарных вопросов" });
    expect(screen.getByTestId("horary-submit-error")).toBeTruthy();
    expect(screen.getByTestId("horary-submit-error").textContent).toMatch(/Недостаточно хорарных вопросов/);
  });

  it("does not render submit error when submitError is null", () => {
    renderForm();
    expect(screen.queryByTestId("horary-submit-error")).toBeNull();
  });
});
