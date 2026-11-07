export type Role =
  | "candidate"
  | "employer"
  | "ministry_admin"
  | "training_provider"
  | "operator";

export type AuthUser = {
  id: string;
  email: string;
  role: Role;
};

export type CandidateProfile = {
  user_id: string;
  skills: string[];
  full_name: string | null;
  phone: string | null;
  location: string | null;
  education: string | null;
  experience: string | null;
  updated_at: string | null;
};

export type CandidateProfileDraft = Omit<CandidateProfile, "user_id" | "updated_at">;
export type CandidateAssistantMessage = {
  role: "user" | "assistant";
  content: string;
};
export type CandidateAssistantReply = {
  reply: string;
  profile_updates: Partial<CandidateProfileDraft>;
};
export type CandidateAssistantSession = {
  id: string;
  title: string;
  messages: CandidateAssistantMessage[];
  created_at: string;
  updated_at: string;
};
export type CandidateAssistantSessionSummary = Omit<CandidateAssistantSession, "messages">;

export type JobOffer = {
  id: string;
  title: string;
  description: string;
  location: string;
  required_skills: string[];
  created_at: string;
};

export type JobMatch = JobOffer & {
  match_score: number;
  matched_skills: string[];
  missing_skills: string[];
};

export type CandidateRoadmapStep = {
  skill: string;
  skill_key: string;
  required_by: string[];
  offer_count: number;
  completed: boolean;
};

export type CandidateRoadmap = {
  steps: CandidateRoadmapStep[];
  completed_steps: number;
  total_steps: number;
  progress_percent: number;
};

type LoginResponse = {
  access_token: string;
  user: AuthUser;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export const demoAccounts: { role: Role; label: string; email: string }[] = [
  { role: "candidate", label: "Candidat", email: "candidate@demo.maharamatch.test" },
  { role: "employer", label: "Employeur", email: "employer@demo.maharamatch.test" },
  { role: "ministry_admin", label: "Administration", email: "ministry@demo.maharamatch.test" },
  {
    role: "training_provider",
    label: "Organisme de formation",
    email: "provider@demo.maharamatch.test",
  },
  { role: "operator", label: "Opérations", email: "operator@demo.maharamatch.test" },
];

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  const messageByStatus: Record<number, string> = {
    401: "Adresse e-mail ou mot de passe incorrect, ou session expirée.",
    403: "Votre rôle ne permet pas d’accéder à cette ressource.",
    409: "Un compte existe déjà avec cette adresse e-mail.",
    422: "Vérifiez les informations saisies.",
    502: "Le service d’assistance a renvoyé une réponse invalide.",
    503: "Le service est momentanément indisponible.",
  };
  const payload: unknown = await response.json().catch(() => undefined);
  const detail =
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload &&
    typeof payload.detail === "string"
      ? payload.detail
      : undefined;
  const message =
    response.status >= 500 && detail
      ? detail
      : messageByStatus[response.status] ??
        detail ??
        "Une erreur est survenue. Veuillez réessayer.";
  return new ApiError(message, response.status);
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return (await response.json()) as LoginResponse;
}

export async function registerCandidate(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return (await response.json()) as LoginResponse;
}

export async function fetchCurrentUser(token: string): Promise<AuthUser> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return (await response.json()) as AuthUser;
}

async function authenticatedRequest<T>(
  token: string,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return (await response.json()) as T;
}

export function fetchCandidateProfile(token: string): Promise<CandidateProfile> {
  return authenticatedRequest(token, "/candidate/profile");
}

export function updateCandidateSkills(
  token: string,
  skills: string[],
): Promise<CandidateProfile> {
  return updateCandidateProfile(token, { skills });
}

export function updateCandidateProfile(
  token: string,
  profile: Partial<CandidateProfileDraft>,
): Promise<CandidateProfile> {
  return authenticatedRequest(token, "/candidate/profile", {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}

export function sendCandidateAssistantMessage(
  token: string,
  messages: CandidateAssistantMessage[],
): Promise<CandidateAssistantReply> {
  return authenticatedRequest(token, "/candidate/assistant/chat", {
    method: "POST",
    body: JSON.stringify({ messages }),
  });
}

export function fetchCandidateAssistantSessions(
  token: string,
): Promise<CandidateAssistantSessionSummary[]> {
  return authenticatedRequest(token, "/candidate/assistant/sessions");
}

export function fetchCandidateAssistantSession(
  token: string,
  sessionId: string,
): Promise<CandidateAssistantSession> {
  return authenticatedRequest(token, `/candidate/assistant/sessions/${sessionId}`);
}

export function createCandidateAssistantSession(
  token: string,
): Promise<CandidateAssistantSession> {
  return authenticatedRequest(token, "/candidate/assistant/sessions", {
    method: "POST",
  });
}

export function sendCandidateAssistantSessionMessage(
  token: string,
  sessionId: string,
  content: string,
): Promise<CandidateAssistantSession> {
  return authenticatedRequest(token, `/candidate/assistant/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function deleteCandidateAssistantSession(
  token: string,
  sessionId: string,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/candidate/assistant/sessions/${sessionId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
}

export function transcribeCandidateAudio(token: string, audio: Blob): Promise<{ text: string }> {
  const form = new FormData();
  form.append("audio", audio, "recording.webm");
  return authenticatedRequest(token, "/candidate/assistant/transcriptions", {
    method: "POST",
    body: form,
  });
}

export async function synthesizeCandidateSpeech(token: string, text: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/candidate/assistant/speech`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return response.blob();
}

export function fetchCandidateMatches(token: string): Promise<JobMatch[]> {
  return authenticatedRequest(token, "/candidate/matches");
}

export function fetchCandidateRoadmap(token: string): Promise<CandidateRoadmap> {
  return authenticatedRequest(token, "/candidate/roadmap");
}

export function updateCandidateRoadmapStep(
  token: string,
  skill: string,
  completed: boolean,
): Promise<CandidateRoadmap> {
  return authenticatedRequest(token, "/candidate/roadmap/steps", {
    method: "PUT",
    body: JSON.stringify({ skill, completed }),
  });
}

export function fetchEmployerOffers(token: string): Promise<JobOffer[]> {
  return authenticatedRequest(token, "/employer/offers");
}

export function createEmployerOffer(
  token: string,
  offer: Omit<JobOffer, "id" | "created_at">,
): Promise<JobOffer> {
  return authenticatedRequest(token, "/employer/offers", {
    method: "POST",
    body: JSON.stringify(offer),
  });
}
