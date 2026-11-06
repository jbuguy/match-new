import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { AuthUser, Role } from "./auth";

const userForRole = (role: Role): AuthUser => ({
  id: `user-${role}`,
  email: `${role}@demo.maharamatch.test`,
  role,
});

function authenticate(role: Role) {
  sessionStorage.setItem("mahara-match-token", "test-token");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => userForRole(role),
    }),
  );
}

describe("role-aware app shell", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("shows a real candidate empty state instead of fabricated opportunity data", async () => {
    authenticate("candidate");
    render(<App />);

    expect(await screen.findByRole("heading", { name: /bonjour et bienvenue/i })).toBeVisible();
    expect(screen.getByText(/vos pistes professionnelles apparaîtront ici/i)).toBeVisible();
    expect(screen.getByText(/profil en cours de création/i)).toBeVisible();
  });

  it("shows only employer navigation and dashboard for an employer", async () => {
    authenticate("employer");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Votre espace employeur" })).toBeVisible();
    const navigation = screen.getByRole("navigation", { name: /navigation principale/i });
    expect(within(navigation).getByRole("button", { name: "Mes offres" })).toBeVisible();
    expect(within(navigation).getByRole("button", { name: "Candidatures" })).toBeVisible();
    expect(within(navigation).queryByRole("button", { name: "Mon profil" })).toBeNull();
    expect(screen.getByText(/aucune offre.*simulée/i)).toBeVisible();
  });

  it.each([
    ["ministry_admin", "Indicateurs agrégés", "Espace administration"],
    ["training_provider", "Catalogue de formations", "Espace organisme de formation"],
    ["operator", "Journaux d’audit", "Espace opérations"],
  ] as const)(
    "renders the %s navigation and dashboard",
    async (role, navigationItem, dashboardTitle) => {
      authenticate(role);
      render(<App />);

      expect(await screen.findByRole("heading", { name: dashboardTitle })).toBeVisible();
      expect(
        within(screen.getByRole("navigation", { name: /navigation principale/i })).getByRole(
          "button",
          { name: navigationItem },
        ),
      ).toBeVisible();
    },
  );

  it("navigates to unavailable sections with a clear status", async () => {
    authenticate("candidate");
    render(<App />);

    await screen.findByRole("heading", { name: /bonjour et bienvenue/i });
    fireEvent.click(
      within(screen.getByRole("navigation", { name: /navigation principale/i })).getByRole(
        "button",
        { name: "Mon parcours" },
      ),
    );

    expect(screen.getByRole("heading", { name: "Mon parcours" })).toBeVisible();
    expect(screen.getByText(/cet espace n’est pas encore disponible/i)).toBeVisible();
  });

  it("supports switching the app shell to dark mode", async () => {
    authenticate("candidate");
    render(<App />);
    await screen.findByRole("heading", { name: /bonjour et bienvenue/i });

    fireEvent.click(screen.getByRole("button", { name: /activer le thème sombre/i }));

    expect(document.querySelector(".app-shell")).toHaveAttribute("data-theme", "dark");
    expect(screen.getByRole("button", { name: /activer le thème clair/i })).toBeVisible();
  });

  it("logs in via the API using the server-returned role", async () => {
    const candidate = userForRole("candidate");
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: "issued-token", user: candidate }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => candidate,
      });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Candidat" }));
    fireEvent.change(screen.getByLabelText("Mot de passe"), {
      target: { value: "DemoPassword123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));

    expect(await screen.findByRole("heading", { name: /bonjour et bienvenue/i })).toBeVisible();
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://127.0.0.1:8000/auth/login",
      expect.objectContaining({ method: "POST" }),
    );
    expect(sessionStorage.getItem("mahara-match-token")).toBe("issued-token");
  });

  it("shows authentication errors instead of a role dashboard", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Email ou mot de passe incorrect." }),
      }),
    );
    render(<App />);
    fireEvent.change(screen.getByLabelText("Adresse e-mail"), {
      target: { value: "candidate@demo.maharamatch.test" },
    });
    fireEvent.change(screen.getByLabelText("Mot de passe"), {
      target: { value: "incorrect" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email ou mot de passe incorrect.",
    );
    expect(screen.queryByRole("navigation", { name: /navigation principale/i })).toBeNull();
  });
});
