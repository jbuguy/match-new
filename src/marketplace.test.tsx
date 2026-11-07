import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  EmployerApplicationsPage,
  TrainingProviderDashboardPage,
} from "./marketplace";

const savedCourse = {
  id: "course-1",
  title: "Excel avancé",
  summary: "Analyser et présenter des données métier.",
  skills: ["Excel", "Analyse"],
  delivery_mode: "online",
  location: null,
  starts_on: "2026-12-01",
  ends_on: "2026-12-10",
  duration_hours: 20,
  capacity: 12,
  price_tnd: "90.00",
  status: "published",
  created_at: "2026-11-01T10:00:00Z",
  updated_at: "2026-11-01T10:00:00Z",
  enrollment_count: 2,
  completed_count: 1,
};

function jsonResponse(payload: unknown, status = 200) {
  return {
    ok: status < 400,
    status,
    json: async () => payload,
  };
}

describe("marketplace dashboards", () => {
  it("creates a provider course with its metadata and shows the updated catalog", async () => {
    const fetchMock = vi.fn().mockImplementation(
      async (input: string, init?: RequestInit) => {
        if (input.endsWith("/training/courses") && init?.method === "POST") {
          expect(JSON.parse(String(init.body))).toMatchObject({
            title: "Excel avancé",
            skills: ["Excel", "Analyse"],
            delivery_mode: "online",
            duration_hours: 20,
            capacity: 12,
            price_tnd: "90",
            status: "published",
          });
          return jsonResponse(savedCourse, 201);
        }
        if (input.endsWith("/training/courses")) return jsonResponse([savedCourse]);
        if (input.endsWith("/training/courses/course-1/enrollments")) return jsonResponse([]);
        throw new Error(`Unexpected API request: ${input}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<TrainingProviderDashboardPage token="token" />);

    fireEvent.change(screen.getByLabelText("Titre"), { target: { value: "Excel avancé" } });
    fireEvent.change(screen.getByLabelText("Résumé"), {
      target: { value: "Analyser et présenter des données métier." },
    });
    fireEvent.change(screen.getByPlaceholderText("Ex. Excel, analyse de données"), {
      target: { value: "Excel, Analyse" },
    });
    fireEvent.change(screen.getByLabelText("Date de début"), {
      target: { value: "2026-12-01" },
    });
    fireEvent.change(screen.getByLabelText("Date de fin"), {
      target: { value: "2026-12-10" },
    });
    fireEvent.change(screen.getByLabelText("Durée (heures)"), { target: { value: "20" } });
    fireEvent.change(screen.getByLabelText("Capacité"), { target: { value: "12" } });
    fireEvent.change(screen.getByLabelText("Prix (TND, facultatif)"), {
      target: { value: "90" },
    });
    fireEvent.change(screen.getByLabelText("Statut"), { target: { value: "published" } });
    fireEvent.click(screen.getByRole("button", { name: "Créer la formation" }));

    expect(await screen.findByText("La formation a été créée.")).toBeVisible();
    expect(await screen.findByText(/2 \/ 12 inscrits actifs/)).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/training/courses"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("lets employers record a hiring outcome for their applications", async () => {
    const application = {
      id: "application-1",
      job_offer_id: "offer-1",
      job_title: "Analyste",
      location: "Tunis",
      status: "reviewing",
      created_at: "2026-10-01T10:00:00Z",
      updated_at: "2026-10-02T10:00:00Z",
      candidate_name: "Candidate",
      candidate_location: "Sfax",
      candidate_skills: ["SQL"],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(async (input: string, init?: RequestInit) => {
        if (input.endsWith("/employer/applications")) {
          return jsonResponse([application]);
        }
        if (input.endsWith("/status") && init?.method === "PUT") {
          return jsonResponse({ ...application, status: "hired" });
        }
        throw new Error(`Unexpected API request: ${input}`);
      }),
    );
    render(<EmployerApplicationsPage token="token" />);

    const statusSelect = await screen.findByRole("combobox", {
      name: "Statut de la candidature de Candidate",
    });
    fireEvent.change(statusSelect, { target: { value: "hired" } });

    await waitFor(() => {
      expect(screen.getByText("Recrutée")).toBeVisible();
    });
    expect(screen.getByText("Décision clôturée et enregistrée.")).toBeVisible();
  });
});
