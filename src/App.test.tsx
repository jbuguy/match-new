import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("candidate app shell", () => {
  it("shows a real empty state instead of fabricated opportunity data", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /bonjour et bienvenue/i })).toBeVisible();
    expect(screen.getByText(/vos pistes professionnelles apparaîtront ici/i)).toBeVisible();
    expect(screen.getByText(/profil en cours de création/i)).toBeVisible();
  });

  it("navigates to unavailable sections with a clear status", () => {
    render(<App />);

    fireEvent.click(
      within(screen.getByRole("navigation", { name: /navigation principale/i })).getByRole(
        "button",
        { name: "Mon parcours" },
      ),
    );

    expect(screen.getByRole("heading", { name: "Mon parcours" })).toBeVisible();
    expect(screen.getByText(/cet espace n’est pas encore disponible/i)).toBeVisible();
  });

  it("supports switching the app shell to dark mode", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /activer le thème sombre/i }));

    expect(document.querySelector(".app-shell")).toHaveAttribute("data-theme", "dark");
    expect(screen.getByRole("button", { name: /activer le thème clair/i })).toBeVisible();
  });
});
