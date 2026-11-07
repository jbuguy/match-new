import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { AuthUser, Role } from "./auth";
import { analyzeCommunicationSignals, summarizeInterviewProgress } from "./workspaces";

const userForRole = (role: Role): AuthUser => ({
  id: `user-${role}`,
  email: `${role}@demo.maharamatch.test`,
  role,
});

function authenticate(role: Role) {
  sessionStorage.setItem("mahara-match-token", "test-token");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(async (input: string) => {
      let payload: unknown = {};
      if (input.endsWith("/auth/me")) {
        payload = userForRole(role);
      } else if (input.endsWith("/candidate/roadmap")) {
        payload = { steps: [], completed_steps: 0, total_steps: 0, progress_percent: 0 };
      } else if (input.endsWith("/candidate/interview-prep/roles")) {
        payload = [];
      } else if (input.endsWith("/admin/indicators")) {
        payload = {
          start_date: null,
          end_date: null,
          candidate_registrations: 0,
          organisations: 0,
          published_job_offers: 0,
          applications_total: 0,
          applications_by_status: [],
          closed_applications: 0,
          hired_applications: 0,
          hire_rate_percent: null,
          top_skills: [],
          published_courses: 0,
          active_enrollments: 0,
          course_completions: 0,
        };
      } else if (
        input.endsWith("/training/courses") ||
        input.includes("/training/courses/") ||
        input.endsWith("/candidate/courses") ||
        input.endsWith("/candidate/enrollments") ||
        input.endsWith("/candidate/applications")
      ) {
        payload = [];
      }
      return { ok: true, status: 200, json: async () => payload };
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
    expect(screen.getByRole("button", { name: "Créer une offre" })).toBeVisible();
  });

  it.each([
    ["ministry_admin", "Vue d’ensemble", "Tableau de bord administration"],
    ["training_provider", "Catalogue de formations", "Votre catalogue de formations"],
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
      [
        "Vue d’ensemble",
        "Mes opportunités",
        "Mon parcours",
        "Préparer un entretien",
        "Formations",
        "Mes candidatures",
        "Assistant",
        "Mon profil",
      ],
    ],
    ["employer", ["Vue d’ensemble", "Mes offres", "Candidatures", "Assistant", "Mon organisation"]],
    [
      "ministry_admin",
      ["Vue d’ensemble", "Assistant"],
    ],
    [
      "training_provider",
      ["Vue d’ensemble", "Catalogue de formations", "Assistant"],
    ],
    ["operator", ["Vue d’ensemble", "Services", "Journaux d’audit", "Assistant"]],
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
  }  );

  it("shows meaningful aggregate metrics on the administration dashboard", async () => {
    sessionStorage.setItem("mahara-match-token", "test-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(async (input: string) => ({
        ok: true,
        status: 200,
        json: async () =>
          input.endsWith("/auth/me")
            ? userForRole("ministry_admin")
            : {
                start_date: null,
                end_date: null,
                candidate_registrations: 25,
                organisations: 4,
                published_job_offers: 12,
                applications_total: 8,
                applications_by_status: [{ status: "hired", count: 2 }],
                closed_applications: 4,
                hired_applications: 2,
                hire_rate_percent: 50,
                top_skills: [{ skill: "Python", offer_count: 7 }],
                published_courses: 3,
                active_enrollments: 6,
                course_completions: 2,
              },
      })),
    );
    render(<App />);

    expect(await screen.findByText("25")).toBeVisible();
    expect(screen.getByText(/50/)).toBeVisible();
    expect(screen.getAllByText("Python")).toHaveLength(2);
    expect(screen.getByText(/2 embauches sur 4 candidatures clôturées/i)).toBeVisible();
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

  it("shows offer requirements separately from general interview suggestions", async () => {
    const candidate = userForRole("candidate");
    const fetchMock = vi.fn().mockImplementation(async (input: string) => ({
      ok: true,
      status: 200,
      json: async () => {
        if (input.endsWith("/auth/me")) return candidate;
        if (input.endsWith("/candidate/interview-prep/roles")) {
          return [{
            id: "offer-1",
            title: "Développeuse Python",
            description: "Créer des services.",
            location: "Tunis",
            required_skills: ["Python", "SQL"],
          }];
        }
        if (input.endsWith("/candidate/interview-prep/profiles/offer-1")) {
          return {
            role: {
              id: "offer-1",
              title: "Développeuse Python",
              description: "Créer des services.",
              location: "Tunis",
              required_skills: ["Python", "SQL"],
            },
            required_competencies: [
              {
                id: "hard:python",
                name: "Python",
                description: "Python est indiquée comme compétence requise dans cette offre.",
                category: "hard",
                associated_skill: "Python",
                assessment_criteria: ["Présentez un exemple concret."],
                required_proficiency_level: null,
                importance_weight: null,
                mandatory: true,
                source: "job_offer",
                candidate_evidence: "self_reported",
              },
              {
                id: "hard:sql",
                name: "SQL",
                description: "SQL est indiquée comme compétence requise dans cette offre.",
                category: "hard",
                associated_skill: "SQL",
                assessment_criteria: ["Expliquez votre méthode."],
                required_proficiency_level: null,
                importance_weight: null,
                mandatory: true,
                source: "job_offer",
                candidate_evidence: "gap",
              },
            ],
            suggested_competencies: [
              {
                id: "communication",
                name: "Communication",
                description: "Présenter une idée clairement.",
                category: "communication",
                associated_skill: null,
                assessment_criteria: ["Structurez votre réponse."],
                required_proficiency_level: null,
                importance_weight: null,
                mandatory: false,
                source: "platform_guidance",
                candidate_evidence: "not_assessed",
              },
            ],
            proficiency_levels: [
              { level: 1, name: "Débutant", description: "Notions de base." },
            ],
          };
        }
        return {};
      },
    }));
    sessionStorage.setItem("mahara-match-token", "test-token");
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await screen.findByRole("navigation", { name: /navigation principale/i });
    fireEvent.click(screen.getByRole("button", { name: "Préparer un entretien" }));

    expect(await screen.findByRole("heading", { name: "Développeuse Python" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Python" })).toBeVisible();
    expect(screen.getByText("Déclarée dans votre profil")).toBeVisible();
    expect(screen.getByText("À préparer")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Communication" })).toBeVisible();
    expect(
      screen.getByText(/ils ne sont pas présentés comme des exigences de cet employeur/i),
    ).toBeVisible();
  });

  it("shows an adaptive mock interview plan for the selected role", async () => {
    const candidate = userForRole("candidate");
    const fetchMock = vi.fn().mockImplementation(async (input: string) => ({
      ok: true,
      status: 200,
      json: async () => {
        if (input.endsWith("/auth/me")) return candidate;
        if (input.endsWith("/candidate/interview-prep/roles")) {
          return [{
            id: "offer-1",
            title: "Développeuse Python",
            description: "Créer des services.",
            location: "Tunis",
            required_skills: ["Python", "SQL"],
          }];
        }
        if (input.endsWith("/candidate/interview-prep/profiles/offer-1")) {
          return {
            role: {
              id: "offer-1",
              title: "Développeuse Python",
              description: "Créer des services.",
              location: "Tunis",
              required_skills: ["Python", "SQL"],
            },
            required_competencies: [
              {
                id: "hard:python",
                name: "Python",
                description: "Python est indiquée comme compétence requise dans cette offre.",
                category: "hard",
                associated_skill: "Python",
                assessment_criteria: ["Présentez un exemple concret."],
                required_proficiency_level: null,
                importance_weight: null,
                mandatory: true,
                source: "job_offer",
                candidate_evidence: "gap",
              },
            ],
            suggested_competencies: [
              {
                id: "communication",
                name: "Communication",
                description: "Présenter une idée clairement.",
                category: "communication",
                associated_skill: null,
                assessment_criteria: ["Structurez votre réponse."],
                required_proficiency_level: null,
                importance_weight: null,
                mandatory: false,
                source: "platform_guidance",
                candidate_evidence: "not_assessed",
              },
            ],
            proficiency_levels: [
              { level: 1, name: "Débutant", description: "Notions de base." },
            ],
          };
        }
        return {};
      },
    }));
    sessionStorage.setItem("mahara-match-token", "test-token");
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await screen.findByRole("navigation", { name: /navigation principale/i });
    fireEvent.click(screen.getByRole("button", { name: "Préparer un entretien" }));

    expect(await screen.findByText("Simulation d’entretien adaptative")).toBeVisible();
    expect(screen.getByRole("button", { name: /Lancer une simulation Python/i })).toBeVisible();
  });

  it("runs a persisted technical assessment and displays its evaluation", async () => {
    const candidate = userForRole("candidate");
    const questions = [
      {
        id: "q1",
        type: "knowledge",
        format: "multiple_choice",
        skill: "Python",
        prompt: "Quelle affirmation décrit correctement les listes et les tuples en Python ?",
        options: [
          { id: "a", label: "Une liste est modifiable, tandis qu'un tuple ne l'est pas." },
          { id: "b", label: "Une liste et un tuple sont tous deux immuables." },
        ],
        criteria: [],
      },
      {
        id: "q2",
        type: "practical",
        format: "text_exercise",
        skill: "Python",
        prompt: "Décrivez une démarche.",
        options: [],
        criteria: [{ id: "reasoning", label: "Raisonnement" }],
      },
      {
        id: "q3",
        type: "scenario",
        format: "text_exercise",
        skill: "Python",
        prompt: "Une tâche ne fonctionne pas.",
        options: [],
        criteria: [{ id: "diagnosis", label: "Diagnostic" }],
      },
    ];
    const initialAssessment = {
      id: "assessment-1",
      offer_id: "offer-1",
      offer_title: "Développeuse Python",
      skill: "Python",
      status: "in_progress",
      questions,
      answers: [],
      created_at: "2026-11-07T10:00:00Z",
      updated_at: "2026-11-07T10:00:00Z",
    };
    const answeredAssessment = {
      ...initialAssessment,
      answers: [{
        question_id: "q1",
        answer: questions[0].options[0].label,
        evaluation: {
          score: 5,
          max_score: 5,
          criteria_scores: [{
            criterion_id: "correctness",
            label: "Exactitude technique",
            score: 5,
            max_score: 5,
          }],
          explanation: "Réponse correcte.",
          strengths: ["La notion est comprise."],
          weaknesses: [],
          suggested_improvements: [],
          method: "deterministic",
        },
        created_at: "2026-11-07T10:01:00Z",
      }],
    };
    const fetchMock = vi.fn().mockImplementation(async (input: string) => ({
      ok: true,
      status: 200,
      json: async () => {
        if (input.endsWith("/auth/me")) return candidate;
        if (input.endsWith("/candidate/interview-prep/roles")) {
          return [{
            id: "offer-1",
            title: "Développeuse Python",
            description: "Créer des services.",
            location: "Tunis",
            required_skills: ["Python"],
          }];
        }
        if (input.endsWith("/candidate/interview-prep/profiles/offer-1")) {
          return {
            role: {
              id: "offer-1",
              title: "Développeuse Python",
              description: "Créer des services.",
              location: "Tunis",
              required_skills: ["Python"],
            },
            required_competencies: [{
              id: "hard:python",
              name: "Python",
              description: "Requise.",
              category: "hard",
              associated_skill: "Python",
              assessment_criteria: ["Présentez un exemple."],
              required_proficiency_level: null,
              importance_weight: null,
              mandatory: true,
              source: "job_offer",
              candidate_evidence: "gap",
            }],
            suggested_competencies: [],
            proficiency_levels: [],
          };
        }
        if (input.endsWith("/candidate/interview-prep/assessments")) {
          return initialAssessment;
        }
        if (input.endsWith("/answers")) return answeredAssessment;
        return {};
      },
    }));
    sessionStorage.setItem("mahara-match-token", "test-token");
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await screen.findByRole("navigation", { name: /navigation principale/i });
    fireEvent.click(screen.getByRole("button", { name: "Préparer un entretien" }));
    fireEvent.click(await screen.findByRole("button", { name: "Évaluer Python" }));
    expect(await screen.findByText(/question 1 sur 3/i)).toBeVisible();
    fireEvent.click(screen.getByLabelText(/une liste est modifiable/i));
    fireEvent.click(screen.getByRole("button", { name: "Envoyer ma réponse" }));

    expect(await screen.findByText("Réponse correcte.")).toBeVisible();
    expect(screen.getByText("5/5")).toBeVisible();
    expect(screen.getByText(/question 2 sur 3/i)).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/candidate/interview-prep/assessments/assessment-1/answers"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ question_id: "q1", selected_option_id: "a" }),
      }),
    );
  });

  it("runs a STAR behavioral assessment and displays structured feedback", async () => {
    const candidate = userForRole("candidate");
    const behavioralAssessment = {
      id: "behavioral-1",
      offer_id: "offer-1",
      offer_title: "Développeuse Python",
      competency_id: "teamwork",
      competency_name: "Travail en équipe",
      status: "in_progress",
      questions: [
        {
          id: "q1",
          type: "behavioral",
          format: "star_text",
          competency_id: "teamwork",
          competency_name: "Travail en équipe",
          prompt: "Décrivez une expérience réelle selon STAR.",
          criteria: [{ id: "clarity", label: "Clarté de la réponse" }],
          star_components: [
            { id: "situation", label: "Situation" },
            { id: "task", label: "Task" },
            { id: "action", label: "Action" },
            { id: "result", label: "Result" },
          ],
        },
        {
          id: "q2",
          type: "situational",
          format: "text_answer",
          competency_id: "teamwork",
          competency_name: "Travail en équipe",
          prompt: "Comment partageriez-vous les informations ?",
          criteria: [{ id: "reasoning", label: "Raisonnement" }],
          star_components: [],
        },
      ],
      answers: [],
      created_at: "2026-11-07T10:00:00Z",
      updated_at: "2026-11-07T10:00:00Z",
    };
    const scoredAssessment = {
      ...behavioralAssessment,
      answers: [
        {
          question_id: "q1",
          answer: "Dans un projet scolaire, notre équipe devait livrer une présentation.",
          evaluation: {
            score: 7,
            max_score: 10,
            criteria_scores: [{
              criterion_id: "clarity",
              label: "Clarté de la réponse",
              score: 4,
              max_score: 5,
            }],
            star_scores: {
              situation: { score: 3, max_score: 5, evidence: "Projet scolaire." },
              task: { score: 3, max_score: 5, evidence: "Livrer la présentation." },
              action: { score: 4, max_score: 5, evidence: "A réparti les tâches." },
              result: { score: 3, max_score: 5, evidence: "Présentation livrée." },
            },
            explanation: "Votre exemple présente une action concrète.",
            strengths: ["Votre contribution est visible."],
            weaknesses: ["Le résultat peut être précisé."],
            suggested_improvements: ["Ajoutez un résultat observable."],
            method: "llm",
          },
          created_at: "2026-11-07T10:01:00Z",
        },
      ],
    };
    const fetchMock = vi.fn().mockImplementation(async (input: string) => ({
      ok: true,
      status: 200,
      json: async () => {
        if (input.endsWith("/auth/me")) return candidate;
        if (input.endsWith("/candidate/interview-prep/roles")) {
          return [{
            id: "offer-1",
            title: "Développeuse Python",
            description: "Créer des services.",
            location: "Tunis",
            required_skills: [],
          }];
        }
        if (input.endsWith("/candidate/interview-prep/profiles/offer-1")) {
          return {
            role: {
              id: "offer-1",
              title: "Développeuse Python",
              description: "Créer des services.",
              location: "Tunis",
              required_skills: [],
            },
            required_competencies: [],
            suggested_competencies: [{
              id: "teamwork",
              name: "Travail en équipe",
              description: "Coopérer avec des collègues.",
              category: "soft",
              associated_skill: null,
              assessment_criteria: ["Décrivez votre contribution."],
              required_proficiency_level: null,
              importance_weight: null,
              mandatory: false,
              source: "platform_guidance",
              candidate_evidence: "not_assessed",
            }],
            proficiency_levels: [],
          };
        }
        if (input.endsWith("/candidate/interview-prep/behavioral-assessments")) {
          return behavioralAssessment;
        }
        if (input.endsWith("/behavioral-assessments/behavioral-1/answers")) {
          return scoredAssessment;
        }
        return {};
      },
    }));
    sessionStorage.setItem("mahara-match-token", "test-token");
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await screen.findByRole("navigation", { name: /navigation principale/i });
    fireEvent.click(screen.getByRole("button", { name: "Préparer un entretien" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "S’entraîner : Travail en équipe" }),
    );
    expect(await screen.findByText(/question 1 sur 2/i)).toBeVisible();
    expect(screen.getByText(/situation, tâche, action, résultat/i)).toBeVisible();
    fireEvent.change(screen.getByLabelText("Votre réponse"), {
      target: { value: "Dans un projet scolaire, notre équipe devait livrer une présentation." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Envoyer ma réponse" }));

    expect(await screen.findByText("Votre exemple présente une action concrète.")).toBeVisible();
    expect(screen.getByText(/SITUATION : 3\/5 — Projet scolaire/i)).toBeVisible();
    expect(screen.getByText("Votre contribution est visible.")).toBeVisible();
    expect(screen.getByText(/question 2 sur 2/i)).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/behavioral-assessments/behavioral-1/answers"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          question_id: "q1",
          answer: "Dans un projet scolaire, notre équipe devait livrer une présentation.",
        }),
      }),
    );
  });

  it("records a behavioral answer, uploads it and previews the transcript for editing", async () => {
    class MockMediaRecorder {
      state: RecordingState = "inactive";
      mimeType = "audio/webm";
      private listeners = new Map<string, ((event: Event) => void)[]>();

      addEventListener(type: string, listener: EventListenerOrEventListenerObject) {
        const callback =
          typeof listener === "function"
            ? listener
            : (event: Event) => listener.handleEvent(event);
        this.listeners.set(type, [...(this.listeners.get(type) ?? []), callback]);
      }

      start() {
        this.state = "recording";
      }

      stop() {
        const data = new Event("dataavailable");
        Object.defineProperty(data, "data", { value: new Blob(["voice audio"]) });
        for (const listener of this.listeners.get("dataavailable") ?? []) listener(data);
        this.state = "inactive";
        for (const listener of this.listeners.get("stop") ?? []) listener(new Event("stop"));
      }
    }

    const candidate = userForRole("candidate");
    const stream = {
      getTracks: () => [{ stop: vi.fn() }],
    } as unknown as MediaStream;
    const getUserMedia = vi.fn().mockResolvedValue(stream);
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia },
    });
    vi.stubGlobal("MediaRecorder", MockMediaRecorder);

    const fetchMock = vi.fn().mockImplementation(async (input: string, init?: RequestInit) => ({
      ok: true,
      status: input.includes("/transcription") ? 202 : 200,
      json: async () => {
        if (input.endsWith("/auth/me")) return candidate;
        if (input.endsWith("/candidate/interview-prep/roles")) {
          return [{
            id: "offer-1",
            title: "Développeuse Python",
            description: "Créer des services.",
            location: "Tunis",
            required_skills: [],
          }];
        }
        if (input.endsWith("/candidate/interview-prep/profiles/offer-1")) {
          return {
            role: {
              id: "offer-1",
              title: "Développeuse Python",
              description: "Créer des services.",
              location: "Tunis",
              required_skills: [],
            },
            required_competencies: [],
            suggested_competencies: [{
              id: "teamwork",
              name: "Travail en équipe",
              description: "Coopérer avec des collègues.",
              category: "soft",
              associated_skill: null,
              assessment_criteria: ["Décrivez votre contribution."],
              required_proficiency_level: null,
              importance_weight: null,
              mandatory: false,
              source: "platform_guidance",
              candidate_evidence: "not_assessed",
            }],
            proficiency_levels: [],
          };
        }
        if (input.endsWith("/candidate/interview-prep/behavioral-assessments")) {
          return {
            id: "behavioral-voice-1",
            offer_id: "offer-1",
            offer_title: "Développeuse Python",
            competency_id: "teamwork",
            competency_name: "Travail en équipe",
            status: "in_progress",
            questions: [{
              id: "q1",
              type: "behavioral",
              format: "star_text",
              competency_id: "teamwork",
              competency_name: "Travail en équipe",
              prompt: "Décrivez une expérience selon STAR.",
              criteria: [{ id: "clarity", label: "Clarté" }],
              star_components: [],
            }],
            answers: [],
            created_at: "2026-11-07T10:00:00Z",
            updated_at: "2026-11-07T10:00:00Z",
          };
        }
        if (input.includes("/behavioral-assessments/behavioral-voice-1/questions/q1/transcription")) {
          const audioForm = init?.body as FormData;
          expect(audioForm.get("audio")).toBeInstanceOf(File);
          return {
            id: "transcription-1",
            assessment_type: "behavioral",
            assessment_id: "behavioral-voice-1",
            question_id: "q1",
            status: "completed",
            transcript: "Notre équipe a réparti les tâches et livré le projet.",
            error_message: null,
            created_at: "2026-11-07T10:01:00Z",
            updated_at: "2026-11-07T10:01:00Z",
          };
        }
        return {};
      },
    }));
    sessionStorage.setItem("mahara-match-token", "test-token");
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await screen.findByRole("navigation", { name: /navigation principale/i });
    fireEvent.click(screen.getByRole("button", { name: "Préparer un entretien" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "S’entraîner : Travail en équipe" }),
    );
    fireEvent.click(await screen.findByRole("button", { name: "Enregistrer une réponse vocale" }));
    expect(await screen.findByRole("button", { name: "Arrêter l’enregistrement" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Arrêter l’enregistrement" }));

    expect((await screen.findByText(/Transcription à vérifier :/)).parentElement).toHaveTextContent(
      "Notre équipe a réparti les tâches et livré le projet.",
    );
    expect(screen.getByLabelText("Votre réponse")).toHaveValue(
      "Notre équipe a réparti les tâches et livré le projet.",
    );
    expect(getUserMedia).toHaveBeenCalledWith({ audio: true });
    expect(
      fetchMock.mock.calls.some(([input]) =>
        String(input).includes("/behavioral-assessments/behavioral-voice-1/questions/q1/transcription"),
      ),
    ).toBe(true);
  });

  it("analyzes communication signals from a candidate answer", () => {
    const result = analyzeCommunicationSignals(
      "D'abord, j'ai clarifié le problème avec l'équipe. Ensuite, j'ai choisi une méthode simple et j'ai vérifié le résultat avec un test. Par exemple, lors d'un projet, j'ai partagé les étapes et le client a validé la solution.",
    );

    expect(result.score).toBeGreaterThan(60);
    expect(result.signals.some((signal) => signal.label === "Structure")).toBe(true);
    expect(result.exercises.some((exercise) => exercise.title === "Structure simple")).toBe(true);
  });

  it("summarizes interview progress from completed assessments", () => {
    const result = summarizeInterviewProgress({
      technicalAssessment: {
        id: "tech-1",
        offer_id: "offer-1",
        offer_title: "Développeuse Python",
        skill: "Python",
        status: "completed",
        questions: [{
          id: "q1",
          type: "knowledge",
          format: "multiple_choice",
          skill: "Python",
          prompt: "Quelle fonction est utilisée pour itérer ?",
          options: [{ id: "a", label: "for" }],
          criteria: [{ id: "correct", label: "Bonne réponse" }],
        }],
        answers: [{
          question_id: "q1",
          answer: "for",
          evaluation: {
            score: 4,
            max_score: 5,
            criteria_scores: [{ criterion_id: "correct", label: "Bonne réponse", score: 4, max_score: 5 }],
            explanation: "Bonne réponse.",
            strengths: ["Clair"],
            weaknesses: [],
            suggested_improvements: ["Exemples"],
            method: "deterministic",
          },
          created_at: "2026-11-07T11:00:00Z",
        }],
        created_at: "2026-11-07T11:00:00Z",
        updated_at: "2026-11-07T11:00:00Z",
      },
      behavioralAssessment: {
        id: "soft-1",
        offer_id: "offer-1",
        offer_title: "Développeuse Python",
        competency_id: "teamwork",
        competency_name: "Travail en équipe",
        status: "completed",
        questions: [{
          id: "q1",
          type: "behavioral",
          format: "star_text",
          competency_id: "teamwork",
          competency_name: "Travail en équipe",
          prompt: "Décrivez votre exemple.",
          criteria: [{ id: "clarity", label: "Clarté" }],
          star_components: [{ id: "situation", label: "Situation" }],
        }],
        answers: [{
          question_id: "q1",
          answer: "J'ai travaillé en équipe.",
          evaluation: {
            score: 3,
            max_score: 5,
            criteria_scores: [{ criterion_id: "clarity", label: "Clarté", score: 3, max_score: 5 }],
            explanation: "Bonne structure.",
            strengths: ["Clair"],
            weaknesses: [],
            suggested_improvements: ["Tester"],
            star_scores: { situation: { score: 3, max_score: 5, evidence: "Contexte clair" } },
            method: "llm",
          },
          created_at: "2026-11-07T11:00:00Z",
        }],
        created_at: "2026-11-07T11:00:00Z",
        updated_at: "2026-11-07T11:00:00Z",
      },
    });

    expect(result.answeredQuestions).toBe(2);
    expect(result.totalQuestions).toBe(2);
    expect(result.globalProgress).toBe(100);
    expect(result.averageScore).toBeGreaterThan(0);
    expect(result.recommendations.length).toBeGreaterThan(0);
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
      name: "Mon profil professionnel",
    })).toBeVisible();
    expect(screen.getByText(/Derja tunisien/i)).toBeVisible();
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

  it("reviews and edits CV extraction before saving it to the candidate profile", async () => {
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
    const extractedProfile = {
      ...emptyProfile,
      full_name: "Amira Ben Salem",
      phone: "+216 20 000 000",
      location: "Tunis",
      education: "Master en gestion",
      experience: "Support client",
      skills: ["Excel", "CRM"],
    };
    const fetchMock = vi.fn().mockImplementation(
      async (input: string, init?: RequestInit) => ({
        ok: true,
        status: 200,
        json: async () => {
          if (input.endsWith("/auth/me")) return candidate;
          if (input.endsWith("/candidate/profile/cv")) return extractedProfile;
          if (input.endsWith("/candidate/profile") && init?.method === "PUT") {
            return { ...emptyProfile, ...JSON.parse(String(init.body)) };
          }
          if (input.endsWith("/candidate/profile")) return emptyProfile;
          return {};
        },
      }),
    );
    sessionStorage.setItem("mahara-match-token", "test-token");
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await screen.findByRole("navigation", { name: /navigation principale/i });
    fireEvent.click(screen.getByRole("button", { name: "Mon profil" }));
    await screen.findByRole("button", { name: "Importer un CV" });
    const cvInput = document.querySelector<HTMLInputElement>("#candidate-cv-upload");
    if (!cvInput) throw new Error("CV upload input is missing.");
    fireEvent.change(cvInput, {
      target: { files: [new File(["CV text"], "amira-cv.txt", { type: "text/plain" })] },
    });

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("heading", { name: "Vérifiez les informations extraites" })).toBeVisible();
    expect(within(dialog).getByLabelText("Compétences")).toHaveValue("Excel, CRM");
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) => String(url).endsWith("/candidate/profile") && init?.method === "PUT",
      ),
    ).toBe(false);

    fireEvent.change(within(dialog).getByLabelText("Nom complet"), {
      target: { value: "Amira Ben Salah" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Enregistrer le profil" }));

    expect(await screen.findByText("Votre profil extrait du CV a été enregistré.")).toBeVisible();
    expect(screen.getByLabelText("Nom complet")).toHaveValue("Amira Ben Salah");
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) =>
          String(url).endsWith("/candidate/profile") &&
          init?.method === "PUT" &&
          JSON.parse(String(init.body)).full_name === "Amira Ben Salah",
      ),
    ).toBe(true);
  });
});
