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
    vi.fn().mockImplementation(async (input: string) => ({
      ok: true,
      status: 200,
      json: async () =>
        input.endsWith("/auth/me")
          ? userForRole(role)
          : input.endsWith("/candidate/roadmap")
            ? { steps: [], completed_steps: 0, total_steps: 0, progress_percent: 0 }
            : {},
    })),
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
    expect(screen.getByRole("button", { name: "Créer une offre" })).toBeVisible();
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

  it.each([
    [
      "candidate",
      ["Vue d’ensemble", "Mes opportunités", "Mon parcours", "Formations", "Assistant", "Mon profil"],
    ],
    ["employer", ["Vue d’ensemble", "Mes offres", "Candidatures", "Assistant", "Mon organisation"]],
    [
      "ministry_admin",
      ["Vue d’ensemble", "Référentiels", "Suggestions", "Importations", "Indicateurs agrégés"],
    ],
    [
      "training_provider",
      ["Vue d’ensemble", "Catalogue de formations", "Mon organisation"],
    ],
    ["operator", ["Vue d’ensemble", "Services", "Journaux d’audit"]],
  ] as const)("limits %s navigation to its role", async (role, allowedItems) => {
    authenticate(role);
    render(<App />);

    await screen.findByRole("navigation", { name: /navigation principale/i });
    const navigation = within(
      screen.getByRole("navigation", { name: /navigation principale/i }),
    );
    expect(navigation.getAllByRole("button")).toHaveLength(allowedItems.length);
    for (const label of allowedItems) {
      expect(navigation.getByRole("button", { name: label })).toBeVisible();
    }
  });

  it("shows a clear empty state when the candidate has no roadmap steps", async () => {
    authenticate("candidate");
    render(<App />);

    await screen.findByRole("heading", { name: /bonjour et bienvenue/i });
    fireEvent.click(
      within(screen.getByRole("navigation", { name: /navigation principale/i })).getByRole(
        "button",
        { name: "Mon parcours" },
      ),
    );

    expect(await screen.findByRole("heading", { name: "Mon parcours professionnel" })).toBeVisible();
    expect(await screen.findByRole("heading", { name: "Aucune étape à proposer pour le moment" })).toBeVisible();
    expect(screen.queryByText(/cet espace n’est pas encore disponible/i)).toBeNull();
  });

  it("loads the candidate roadmap and persists step completion", async () => {
    const candidate = userForRole("candidate");
    const roadmap = {
      steps: [
        {
          skill: "SQL",
          skill_key: "sql",
          required_by: ["Analyste de données"],
          offer_count: 1,
          completed: false,
        },
      ],
      completed_steps: 0,
      total_steps: 1,
      progress_percent: 0,
    };
    const completedRoadmap = {
      ...roadmap,
      steps: [{ ...roadmap.steps[0], completed: true }],
      completed_steps: 1,
      progress_percent: 100,
    };
    const fetchMock = vi.fn().mockImplementation(async (input: string) => ({
      ok: true,
      status: 200,
      json: async () => {
        if (input.endsWith("/auth/me")) return candidate;
        if (input.endsWith("/candidate/roadmap/steps")) return completedRoadmap;
        if (input.endsWith("/candidate/roadmap")) return roadmap;
        return {};
      },
    }));
    sessionStorage.setItem("mahara-match-token", "test-token");
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await screen.findByRole("navigation", { name: /navigation principale/i });
    fireEvent.click(screen.getByRole("button", { name: "Mon parcours" }));

    expect(await screen.findByRole("heading", { name: "SQL" })).toBeVisible();
    expect(screen.getByRole("progressbar", { name: "Progression du parcours" })).toHaveAttribute(
      "aria-valuenow",
      "0",
    );
    fireEvent.click(screen.getByRole("button", { name: "Marquer l’étape comme terminée" }));

    expect(await screen.findByText("Terminée")).toBeVisible();
    expect(screen.getByRole("progressbar", { name: "Progression du parcours" })).toHaveAttribute(
      "aria-valuenow",
      "100",
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/candidate/roadmap/steps"),
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ skill: "SQL", completed: true }),
      }),
    );
  });

  it("supports switching the app shell to dark mode", async () => {
    authenticate("candidate");
    render(<App />);
    await screen.findByRole("heading", { name: /bonjour et bienvenue/i });

    fireEvent.click(screen.getByRole("button", { name: /activer le thème sombre/i }));

    expect(document.querySelector(".app-shell")).toHaveAttribute("data-theme", "dark");
    expect(screen.getByRole("button", { name: /activer le thème clair/i })).toBeVisible();
  });

  it.each([
    ["candidate", "Votre assistant carrière", /obtenir de meilleures correspondances/i],
    ["employer", "Votre assistant recrutement", /rédiger une offre claire/i],
  ] as const)("shows role-specific assistant guidance for %s", async (role, title, prompt) => {
    authenticate(role);
    render(<App />);

    await screen.findByRole("navigation", { name: /navigation principale/i });
    fireEvent.click(
      within(screen.getByRole("navigation", { name: /navigation principale/i })).getByRole(
        "button",
        { name: "Assistant" },
      ),
    );

    expect(screen.getByRole("heading", { name: title })).toBeVisible();
    expect(await screen.findByRole("button", { name: prompt })).toBeVisible();
  });

  it("sends a career chat message and displays the saved reply", async () => {
    const candidate = userForRole("candidate");
    const chatSession = {
      id: "session-1",
      title: "Nouvelle conversation",
      messages: [],
      created_at: "2026-11-06T12:00:00Z",
      updated_at: "2026-11-06T12:00:00Z",
    };
    const fetchMock = vi.fn().mockImplementation(
      async (input: string, init?: RequestInit) => ({
        ok: true,
        status: init?.method === "POST" && input.endsWith("/sessions") ? 201 : 200,
        json: async () => {
          if (input.endsWith("/auth/me")) return candidate;
          if (input.endsWith("/assistant/sessions") && init?.method !== "POST") return [];
          if (input.endsWith("/assistant/sessions") && init?.method === "POST") return chatSession;
          if (input.endsWith("/messages")) {
            return {
              ...chatSession,
              title: "Parler de mon parcours",
              messages: [
                { role: "user", content: "Parler de mon parcours" },
                { role: "assistant", content: "Aslema ! شنوة تحب تخدم؟" },
              ],
            };
          }
          return {};
        },
      }),
    );
    sessionStorage.setItem("mahara-match-token", "test-token");
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await screen.findByRole("navigation", { name: /navigation principale/i });
    fireEvent.click(screen.getByRole("button", { name: "Assistant" }));
    fireEvent.change(await screen.findByRole("textbox", { name: "Votre message" }), {
      target: { value: "Parler de mon parcours" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Envoyer le message" }));

    expect(await screen.findByText("Aslema ! شنوة تحب تخدم؟")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/assistant/sessions/session-1/messages"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("creates and displays an employer job offer", async () => {
    const employer = userForRole("employer");
    const offer = {
      id: "offer-1",
      title: "Chargé de projet",
      description: "Coordonner des projets avec les équipes.",
      location: "Tunis",
      required_skills: ["Gestion de projet", "Excel"],
      created_at: "2026-11-06T12:00:00Z",
    };
    const fetchMock = vi.fn().mockImplementation(
      async (input: string, init?: RequestInit) => ({
        ok: true,
        status: init?.method === "POST" ? 201 : 200,
        json: async () => {
          if (input.endsWith("/auth/me")) return employer;
          if (input.endsWith("/employer/offers")) {
            return init?.method === "POST" ? offer : [];
          }
          return {};
        },
      }),
    );
    sessionStorage.setItem("mahara-match-token", "test-token");
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await screen.findByRole("navigation", { name: /navigation principale/i });
    fireEvent.click(screen.getByRole("button", { name: "Mes offres" }));
    fireEvent.change(screen.getByLabelText("Intitulé du poste"), {
      target: { value: offer.title },
    });
    fireEvent.change(screen.getByLabelText("Lieu"), { target: { value: offer.location } });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: offer.description },
    });
    fireEvent.change(screen.getByLabelText("Compétences requises"), {
      target: { value: offer.required_skills.join(", ") },
    });
    fireEvent.click(screen.getByRole("button", { name: "Publier l’offre" }));

    expect(await screen.findByRole("heading", { name: offer.title })).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent(/votre offre est publiée/i);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/employer/offers",
      expect.objectContaining({ method: "POST" }),
    );
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
        json: async () => ({ detail: "Email or password is incorrect." }),
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
      "Adresse e-mail ou mot de passe incorrect",
    );
    expect(screen.queryByRole("navigation", { name: /navigation principale/i })).toBeNull();
  });

  it("registers candidates and opens the assisted profile onboarding", async () => {
    const candidate = userForRole("candidate");
    const emptyProfile = {
      user_id: candidate.id,
      full_name: null,
      phone: null,
      location: null,
      education: null,
      experience: null,
      skills: [],
      updated_at: null,
    };
    const fetchMock = vi.fn().mockImplementation(
      async (input: string, init?: RequestInit) => {
        if (input.endsWith("/auth/register")) {
          return {
            ok: true,
            status: 201,
            json: async () => ({ access_token: "new-candidate-token", user: candidate }),
          };
        }
        if (input.endsWith("/auth/me")) {
          return { ok: true, status: 200, json: async () => candidate };
        }
        if (input.endsWith("/candidate/profile")) {
          if (init?.method === "PUT") {
            return {
              ok: true,
              status: 200,
              json: async () => ({
                ...emptyProfile,
                ...JSON.parse(String(init.body)),
              }),
            };
          }
          return { ok: true, status: 200, json: async () => emptyProfile };
        }
        if (input.endsWith("/candidate/assistant/chat")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              reply: "Super, on commence !",
              profile_updates: { full_name: "Amira Ben Salem" },
            }),
          };
        }
        if (input.endsWith("/candidate/assistant/speech")) {
          return {
            ok: false,
            status: 503,
            json: async () => ({ detail: "TTS is not configured." }),
          };
        }
        return { ok: true, status: 200, json: async () => ({}) };
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Créer un compte candidat" }));
    fireEvent.change(screen.getByLabelText("Adresse e-mail"), {
      target: { value: "amira@example.test" },
    });
    fireEvent.change(screen.getByLabelText("Mot de passe"), {
      target: { value: "A-Secure-Local-Passphrase-123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Créer mon compte" }));

    expect(await screen.findByRole("heading", {
      name: "Complétez votre profil avec l’assistant",
    })).toBeVisible();
    expect(screen.getByText(/Le Derja tunisien/i)).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/auth/register",
      expect.objectContaining({ method: "POST" }),
    );

    fireEvent.change(screen.getByLabelText("Votre message"), {
      target: { value: "Ismi Amira Ben Salem" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Envoyer le message" }));

    expect(await screen.findByText("Super, on commence !")).toBeVisible();
    expect(screen.getByLabelText("Nom complet")).toHaveValue("Amira Ben Salem");
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) => String(url).endsWith("/candidate/profile") && init?.method === "PUT",
      ),
    ).toBe(false);

    fireEvent.click(screen.getByRole("button", { name: "Enregistrer mon profil" }));
    expect(await screen.findByText(/Votre profil a été enregistré/i)).toBeVisible();
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) =>
          String(url).endsWith("/candidate/profile") &&
          init?.method === "PUT" &&
          JSON.parse(String(init.body)).full_name === "Amira Ben Salem",
      ),
    ).toBe(true);
  });
});
