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

export type JobApplicationStatus =
  | "submitted"
  | "reviewing"
  | "interview"
  | "hired"
  | "rejected";

export type JobApplication = {
  id: string;
  job_offer_id: string;
  job_title: string;
  location: string;
  status: JobApplicationStatus;
  created_at: string;
  updated_at: string;
};

export type EmployerApplication = JobApplication & {
  candidate_name: string | null;
  candidate_location: string | null;
  candidate_skills: string[];
};

export type CourseStatus = "draft" | "published" | "archived";
export type CourseDeliveryMode = "online" | "in_person" | "hybrid";
export type CourseEnrollmentStatus = "enrolled" | "completed" | "withdrawn";

export type TrainingCourse = {
  id: string;
  title: string;
  summary: string;
  skills: string[];
  delivery_mode: CourseDeliveryMode;
  location: string | null;
  starts_on: string | null;
  ends_on: string | null;
  duration_hours: number;
  capacity: number;
  price_tnd: string | null;
  status: CourseStatus;
  created_at: string;
  updated_at: string;
  enrollment_count: number;
  completed_count: number;
};

export type TrainingCourseDraft = Omit<
  TrainingCourse,
  "id" | "provider_id" | "created_at" | "updated_at" | "enrollment_count" | "completed_count"
>;

export type CourseEnrollment = {
  id: string;
  course_id: string;
  course_title: string;
  status: CourseEnrollmentStatus;
  created_at: string;
  updated_at: string;
};

export type ProviderCourseEnrollment = CourseEnrollment & {
  candidate_name: string | null;
  candidate_location: string | null;
  candidate_skills: string[];
};

export type AdminIndicators = {
  start_date: string | null;
  end_date: string | null;
  candidate_registrations: number;
  organisations: number;
  published_job_offers: number;
  applications_total: number;
  applications_by_status: { status: JobApplicationStatus; count: number }[];
  closed_applications: number;
  hired_applications: number;
  hire_rate_percent: number | null;
  top_skills: { skill: string; offer_count: number }[];
  published_courses: number;
  active_enrollments: number;
  course_completions: number;
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

export type CandidateInterviewRole = Pick<
  JobOffer,
  "id" | "title" | "description" | "location" | "required_skills"
>;

export type InterviewCompetency = {
  id: string;
  name: string;
  description: string;
  category: "hard" | "soft" | "communication";
  associated_skill: string | null;
  assessment_criteria: string[];
  required_proficiency_level: number | null;
  importance_weight: number | null;
  mandatory: boolean;
  source: "job_offer" | "platform_guidance";
  candidate_evidence: "self_reported" | "gap" | "not_assessed";
};

export type CandidateInterviewPreparationProfile = {
  role: CandidateInterviewRole;
  required_competencies: InterviewCompetency[];
  suggested_competencies: InterviewCompetency[];
  proficiency_levels: { level: number; name: string; description: string }[];
};

export type TechnicalAssessmentQuestion = {
  id: string;
  type: "knowledge" | "practical" | "scenario";
  format: "multiple_choice" | "short_answer" | "text_exercise";
  skill: string;
  prompt: string;
  options: { id: string; label: string }[];
  criteria: { id: string; label: string }[];
};

export type TechnicalAssessmentEvaluation = {
  score: number;
  max_score: number;
  criteria_scores: {
    criterion_id: string;
    label: string;
    score: number;
    max_score: number;
  }[];
  explanation: string;
  strengths: string[];
  weaknesses: string[];
  suggested_improvements: string[];
  method: "deterministic" | "llm";
};

export type CandidateTechnicalAssessment = {
  id: string;
  offer_id: string;
  offer_title: string;
  skill: string;
  status: "in_progress" | "completed";
  questions: TechnicalAssessmentQuestion[];
  answers: {
    question_id: string;
    answer: string;
    evaluation: TechnicalAssessmentEvaluation;
    created_at: string;
  }[];
  created_at: string;
  updated_at: string;
};

export type CandidateBehavioralAssessment = {
  id: string;
  offer_id: string;
  offer_title: string;
  competency_id: string;
  competency_name: string;
  status: "in_progress" | "completed";
  questions: {
    id: string;
    type: "behavioral" | "situational";
    format: "star_text" | "text_answer";
    competency_id: string;
    competency_name: string;
    prompt: string;
    criteria: { id: string; label: string }[];
    star_components: { id: string; label: string }[];
  }[];
  answers: {
    question_id: string;
    answer: string;
    evaluation: TechnicalAssessmentEvaluation & {
      star_scores: Record<string, { score: number; max_score: number; evidence: string }>;
    };
    created_at: string;
  }[];
  created_at: string;
  updated_at: string;
};

export type CandidateInterviewTranscription = {
  id: string;
  assessment_type: "technical" | "behavioral";
  assessment_id: string;
  question_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  transcript: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
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

export function uploadCandidateCv(token: string, file: File): Promise<CandidateProfile> {
  const form = new FormData();
  form.append("file", file, file.name);
  return authenticatedRequest(token, "/candidate/profile/cv", {
    method: "POST",
    body: form,
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

export function fetchCandidateInterviewRoles(
  token: string,
): Promise<CandidateInterviewRole[]> {
  return authenticatedRequest(token, "/candidate/interview-prep/roles");
}

export function fetchCandidateInterviewPreparationProfile(
  token: string,
  offerId: string,
): Promise<CandidateInterviewPreparationProfile> {
  return authenticatedRequest(
    token,
    `/candidate/interview-prep/profiles/${encodeURIComponent(offerId)}`,
  );
}

export function startCandidateTechnicalAssessment(
  token: string,
  offerId: string,
  skill: string,
): Promise<CandidateTechnicalAssessment> {
  return authenticatedRequest(token, "/candidate/interview-prep/assessments", {
    method: "POST",
    body: JSON.stringify({ offer_id: offerId, skill }),
  });
}

export function submitCandidateTechnicalAssessmentAnswer(
  token: string,
  assessmentId: string,
  answer: { question_id: string; answer?: string; selected_option_id?: string },
): Promise<CandidateTechnicalAssessment> {
  return authenticatedRequest(
    token,
    `/candidate/interview-prep/assessments/${encodeURIComponent(assessmentId)}/answers`,
    {
      method: "POST",
      body: JSON.stringify(answer),
    },
  );
}

export function startCandidateBehavioralAssessment(
  token: string,
  offerId: string,
  competencyId: string,
): Promise<CandidateBehavioralAssessment> {
  return authenticatedRequest(token, "/candidate/interview-prep/behavioral-assessments", {
    method: "POST",
    body: JSON.stringify({ offer_id: offerId, skill: competencyId }),
  });
}

export function submitCandidateBehavioralAssessmentAnswer(
  token: string,
  assessmentId: string,
  questionId: string,
  answer: string,
): Promise<CandidateBehavioralAssessment> {
  return authenticatedRequest(
    token,
    `/candidate/interview-prep/behavioral-assessments/${encodeURIComponent(assessmentId)}/answers`,
    {
      method: "POST",
      body: JSON.stringify({ question_id: questionId, answer }),
    },
  );
}

export function uploadCandidateInterviewAudio(
  token: string,
  assessmentType: "technical" | "behavioral",
  assessmentId: string,
  questionId: string,
  audio: Blob,
): Promise<CandidateInterviewTranscription> {
  const form = new FormData();
  form.append("audio", audio, "interview-answer.webm");
  return authenticatedRequest(
    token,
    `/candidate/interview-prep/${assessmentType}-assessments/${encodeURIComponent(assessmentId)}` +
      `/questions/${encodeURIComponent(questionId)}/transcription`,
    {
      method: "POST",
      body: form,
    },
  );
}

export function fetchCandidateInterviewTranscription(
  token: string,
  transcriptionId: string,
): Promise<CandidateInterviewTranscription> {
  return authenticatedRequest(
    token,
    `/candidate/interview-prep/transcriptions/${encodeURIComponent(transcriptionId)}`,
  );
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

export function applyToJob(token: string, offerId: string): Promise<JobApplication> {
  return authenticatedRequest(token, `/candidate/applications/${offerId}`, {
    method: "POST",
  });
}

export function fetchCandidateApplications(token: string): Promise<JobApplication[]> {
  return authenticatedRequest(token, "/candidate/applications");
}

export function fetchEmployerApplications(token: string): Promise<EmployerApplication[]> {
  return authenticatedRequest(token, "/employer/applications");
}

export function updateEmployerApplicationStatus(
  token: string,
  applicationId: string,
  status: Exclude<JobApplicationStatus, "submitted">,
): Promise<JobApplication> {
  return authenticatedRequest(token, `/employer/applications/${applicationId}/status`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });
}

export function fetchAdminIndicators(
  token: string,
  startDate: string,
  endDate: string,
): Promise<AdminIndicators> {
  const query = new URLSearchParams();
  if (startDate) query.set("start_date", startDate);
  if (endDate) query.set("end_date", endDate);
  const queryString = query.toString();
  const suffix = queryString ? `?${queryString}` : "";
  return authenticatedRequest(token, `/admin/indicators${suffix}`);
}

export function fetchTrainingCourses(token: string): Promise<TrainingCourse[]> {
  return authenticatedRequest(token, "/training/courses");
}

export function createTrainingCourse(
  token: string,
  course: TrainingCourseDraft,
): Promise<TrainingCourse> {
  return authenticatedRequest(token, "/training/courses", {
    method: "POST",
    body: JSON.stringify(course),
  });
}

export function updateTrainingCourse(
  token: string,
  courseId: string,
  course: TrainingCourseDraft,
): Promise<TrainingCourse> {
  return authenticatedRequest(token, `/training/courses/${courseId}`, {
    method: "PUT",
    body: JSON.stringify(course),
  });
}

export function fetchProviderCourseEnrollments(
  token: string,
  courseId: string,
): Promise<ProviderCourseEnrollment[]> {
  return authenticatedRequest(token, `/training/courses/${courseId}/enrollments`);
}

export function updateCourseEnrollmentStatus(
  token: string,
  enrollmentId: string,
  status: CourseEnrollmentStatus,
): Promise<ProviderCourseEnrollment> {
  return authenticatedRequest(token, `/training/enrollments/${enrollmentId}/status`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });
}

export function fetchPublishedCourses(token: string): Promise<TrainingCourse[]> {
  return authenticatedRequest(token, "/candidate/courses");
}

export function fetchCandidateEnrollments(token: string): Promise<CourseEnrollment[]> {
  return authenticatedRequest(token, "/candidate/enrollments");
}

export function enrollInCourse(token: string, courseId: string): Promise<CourseEnrollment> {
  return authenticatedRequest(token, `/candidate/courses/${courseId}/enroll`, {
    method: "POST",
  });
}
