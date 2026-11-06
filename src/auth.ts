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
  const body: unknown = await response.json().catch(() => null);
  if (
    typeof body === "object" &&
    body !== null &&
    "detail" in body &&
    typeof body.detail === "string"
  ) {
    return new ApiError(body.detail, response.status);
  }
  return new ApiError("Le service est momentanément indisponible.", response.status);
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

export async function fetchCurrentUser(token: string): Promise<AuthUser> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return (await response.json()) as AuthUser;
}
