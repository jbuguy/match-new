from datetime import date, datetime
from decimal import Decimal
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import (
    CourseDeliveryMode,
    CourseEnrollmentStatus,
    CourseStatus,
    JobApplicationStatus,
    Role,
)


def normalize_skills(value: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for skill in value:
        clean_skill = skill.strip()
        if not clean_skill:
            continue
        if len(clean_skill) > 60:
            raise ValueError("Each skill must be 60 characters or fewer.")
        key = clean_skill.casefold()
        if len(key) > 60:
            raise ValueError("Each normalized skill must be 60 characters or fewer.")
        if key not in seen:
            normalized.append(clean_skill)
            seen.add(key)
    return normalized


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().casefold()


class CandidateRegistrationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=1024)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address.")
        return normalized


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: Role


class OrganisationProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    website: str | None = Field(default=None, max_length=500)
    sector: str | None = Field(default=None, max_length=120)
    size: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=3000)
    phone: str | None = Field(default=None, max_length=40)
    contact_email: str | None = Field(default=None, max_length=320)
    location: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        clean = value.strip()
        if len(clean) < 2:
            raise ValueError("Organisation name must contain at least two characters.")
        return clean

    @field_validator("website")
    @classmethod
    def validate_website(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        clean = value.strip()
        if not clean.startswith(("https://", "http://")):
            raise ValueError("Website must start with http:// or https://.")
        return clean


class OrganisationProfileResponse(OrganisationProfileUpdate):
    id: str
    organisation_type: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class AuditEventResponse(BaseModel):
    id: str
    action: str
    resource_type: str | None
    actor_role: Role | None
    created_at: datetime


class CandidateProfileUpdate(BaseModel):
    skills: list[str] | None = Field(default=None, max_length=30)
    full_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=120)
    education: str | None = Field(default=None, max_length=5000)
    experience: str | None = Field(default=None, max_length=5000)

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, value: list[str] | None) -> list[str] | None:
        return normalize_skills(value) if value is not None else None

    @field_validator("full_name", "phone", "location", "education", "experience")
    @classmethod
    def trim_profile_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def require_profile_field(self) -> "CandidateProfileUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one profile field must be provided.")
        return self


class CandidateProfileResponse(BaseModel):
    user_id: str
    skills: list[str]
    full_name: str | None = None
    phone: str | None = None
    location: str | None = None
    education: str | None = None
    experience: str | None = None
    updated_at: datetime | None = None


class AssistantMessage(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=3000)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in {"user", "assistant"}:
            raise ValueError("Message role must be user or assistant.")
        return value

    @field_validator("content")
    @classmethod
    def trim_content(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Message content cannot be blank.")
        return clean


class CandidateAssistantRequest(BaseModel):
    messages: list[AssistantMessage] = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def require_user_message_last(self) -> "CandidateAssistantRequest":
        if self.messages[-1].role != "user":
            raise ValueError("The last assistant message must be from the candidate.")
        return self


class CandidateProfileDraft(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=120)
    education: str | None = Field(default=None, max_length=5000)
    experience: str | None = Field(default=None, max_length=5000)
    skills: list[str] | None = Field(default=None, max_length=30)


class CandidateAssistantResponse(BaseModel):
    reply: str = Field(min_length=1, max_length=3000)
    profile_updates: CandidateProfileDraft = Field(default_factory=CandidateProfileDraft)


class CandidateAssistantSpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)

    @field_validator("text")
    @classmethod
    def trim_text(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Text cannot be blank.")
        return clean


class CandidateAssistantSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    messages: list[AssistantMessage]
    created_at: datetime
    updated_at: datetime


class CandidateAssistantSessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class CandidateAssistantMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=3000)

    @field_validator("content")
    @classmethod
    def trim_content(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Message content cannot be blank.")
        return clean


class CandidateAssistantSessionRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Conversation title cannot be blank.")
        return clean


class JobOfferCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=10, max_length=5000)
    location: str = Field(min_length=2, max_length=120)
    required_skills: list[str] = Field(min_length=1, max_length=30)

    @field_validator("title", "description", "location")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("required_skills")
    @classmethod
    def clean_skills(cls, value: list[str]) -> list[str]:
        normalized = normalize_skills(value)
        if not normalized:
            raise ValueError("At least one required skill is needed.")
        return normalized

    @model_validator(mode="after")
    def reject_blank_text(self) -> "JobOfferCreate":
        if not self.title or not self.description or not self.location:
            raise ValueError("Title, description, and location cannot be blank.")
        return self


class JobOfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    location: str
    required_skills: list[str]
    created_at: datetime


class JobMatchResponse(JobOfferResponse):
    match_score: int
    matched_skills: list[str]
    missing_skills: list[str]


class JobApplicationResponse(BaseModel):
    id: str
    job_offer_id: str
    job_title: str
    location: str
    status: JobApplicationStatus
    created_at: datetime
    updated_at: datetime


class EmployerApplicationResponse(JobApplicationResponse):
    candidate_name: str | None
    candidate_location: str | None
    candidate_skills: list[str]


class JobApplicationStatusUpdate(BaseModel):
    status: JobApplicationStatus


class TrainingCourseFields(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    summary: str = Field(min_length=10, max_length=5000)
    skills: list[str] = Field(min_length=1, max_length=30)
    delivery_mode: CourseDeliveryMode
    location: str | None = Field(default=None, max_length=120)
    starts_on: date | None = None
    ends_on: date | None = None
    duration_hours: int = Field(ge=1, le=2000)
    capacity: int = Field(ge=1, le=10000)
    price_tnd: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    status: CourseStatus = CourseStatus.DRAFT

    @field_validator("title", "summary")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("location")
    @classmethod
    def trim_location(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("skills")
    @classmethod
    def clean_course_skills(cls, value: list[str]) -> list[str]:
        normalized = normalize_skills(value)
        if not normalized:
            raise ValueError("At least one course skill is required.")
        return normalized

    @model_validator(mode="after")
    def validate_course_details(self) -> "TrainingCourseFields":
        if not self.title or not self.summary:
            raise ValueError("Title and summary cannot be blank.")
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("Course end date must be on or after its start date.")
        if (
            self.delivery_mode in {CourseDeliveryMode.IN_PERSON, CourseDeliveryMode.HYBRID}
            and not self.location
        ):
            raise ValueError("A location is required for in-person or hybrid courses.")
        return self


class TrainingCourseCreate(TrainingCourseFields):
    pass


class TrainingCourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    summary: str
    skills: list[str]
    delivery_mode: CourseDeliveryMode
    location: str | None
    starts_on: date | None
    ends_on: date | None
    duration_hours: int
    capacity: int
    price_tnd: Decimal | None
    status: CourseStatus
    created_at: datetime
    updated_at: datetime
    enrollment_count: int = 0
    completed_count: int = 0


class CourseEnrollmentResponse(BaseModel):
    id: str
    course_id: str
    course_title: str
    status: CourseEnrollmentStatus
    created_at: datetime
    updated_at: datetime


class ProviderCourseEnrollmentResponse(CourseEnrollmentResponse):
    candidate_name: str | None
    candidate_location: str | None
    candidate_skills: list[str]


class CourseEnrollmentStatusUpdate(BaseModel):
    status: CourseEnrollmentStatus


class SkillDemandIndicator(BaseModel):
    skill: str
    offer_count: int


class ApplicationStatusIndicator(BaseModel):
    status: JobApplicationStatus
    count: int


class AdminIndicatorsResponse(BaseModel):
    start_date: date | None
    end_date: date | None
    candidate_registrations: int
    organisations: int
    published_job_offers: int
    applications_total: int
    applications_by_status: list[ApplicationStatusIndicator]
    closed_applications: int
    hired_applications: int
    hire_rate_percent: float | None
    top_skills: list[SkillDemandIndicator]
    published_courses: int
    active_enrollments: int
    course_completions: int


class CandidateRoadmapStepResponse(BaseModel):
    skill: str
    skill_key: str
    required_by: list[str]
    offer_count: int
    completed: bool


class CandidateRoadmapResponse(BaseModel):
    steps: list[CandidateRoadmapStepResponse]
    completed_steps: int
    total_steps: int
    progress_percent: int


class CandidateRoadmapStepUpdate(BaseModel):
    skill: str = Field(min_length=1, max_length=60)
    completed: bool

    @field_validator("skill")
    @classmethod
    def trim_skill(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Skill cannot be blank.")
        return clean


class CandidateInterviewRoleResponse(BaseModel):
    id: str
    title: str
    description: str
    location: str
    required_skills: list[str]


class InterviewCompetencyResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    associated_skill: str | None
    assessment_criteria: list[str]
    required_proficiency_level: int | None
    importance_weight: float | None
    mandatory: bool
    source: str
    candidate_evidence: str


class InterviewProficiencyLevelResponse(BaseModel):
    level: int
    name: str
    description: str


class CandidateInterviewPreparationProfileResponse(BaseModel):
    role: CandidateInterviewRoleResponse
    required_competencies: list[InterviewCompetencyResponse]
    suggested_competencies: list[InterviewCompetencyResponse]
    proficiency_levels: list[InterviewProficiencyLevelResponse]


class TechnicalAssessmentStartRequest(BaseModel):
    offer_id: str = Field(min_length=1, max_length=36)
    skill: str = Field(min_length=1, max_length=60)

    @field_validator("offer_id", "skill")
    @classmethod
    def trim_assessment_target(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("An offer and skill are required.")
        return clean


class TechnicalAssessmentAnswerRequest(BaseModel):
    question_id: str = Field(min_length=1, max_length=20)
    answer: str | None = Field(default=None, max_length=10000)
    selected_option_id: str | None = Field(default=None, max_length=20)

    @field_validator("answer")
    @classmethod
    def trim_assessment_answer(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip()
        return clean or None

    @field_validator("selected_option_id")
    @classmethod
    def trim_option_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip()
        return clean or None

    @model_validator(mode="after")
    def require_one_answer_format(self) -> "TechnicalAssessmentAnswerRequest":
        if (self.answer is None) == (self.selected_option_id is None):
            raise ValueError("Provide either a text answer or one selected option.")
        return self


class TechnicalAssessmentOptionResponse(BaseModel):
    id: str
    label: str


class TechnicalAssessmentCriterionResponse(BaseModel):
    id: str
    label: str


class TechnicalAssessmentQuestionResponse(BaseModel):
    id: str
    type: Literal["knowledge", "practical", "scenario"]
    format: Literal["multiple_choice", "short_answer", "text_exercise"]
    skill: str
    prompt: str
    options: list[TechnicalAssessmentOptionResponse] = Field(default_factory=list)
    criteria: list[TechnicalAssessmentCriterionResponse] = Field(default_factory=list)


class TechnicalAssessmentCriterionScoreResponse(BaseModel):
    criterion_id: str
    label: str
    score: int
    max_score: int


class TechnicalAssessmentEvaluationResponse(BaseModel):
    score: int
    max_score: int
    criteria_scores: list[TechnicalAssessmentCriterionScoreResponse]
    explanation: str
    strengths: list[str]
    weaknesses: list[str]
    suggested_improvements: list[str]
    method: Literal["deterministic", "llm"]


class TechnicalAssessmentAnswerResponse(BaseModel):
    question_id: str
    answer: str
    evaluation: TechnicalAssessmentEvaluationResponse
    created_at: datetime


class CandidateTechnicalAssessmentResponse(BaseModel):
    id: str
    offer_id: str
    offer_title: str
    skill: str
    status: Literal["in_progress", "completed"]
    questions: list[TechnicalAssessmentQuestionResponse]
    answers: list[TechnicalAssessmentAnswerResponse]
    created_at: datetime
    updated_at: datetime


class BehavioralAssessmentQuestionResponse(BaseModel):
    id: str
    type: Literal["behavioral", "situational"]
    format: Literal["star_text", "text_answer"]
    competency_id: str
    competency_name: str
    prompt: str
    criteria: list[TechnicalAssessmentCriterionResponse]
    star_components: list[TechnicalAssessmentCriterionResponse]


class BehavioralSTARScoreResponse(BaseModel):
    score: int
    max_score: int
    evidence: str


class BehavioralAssessmentEvaluationResponse(BaseModel):
    score: int
    max_score: int
    criteria_scores: list[TechnicalAssessmentCriterionScoreResponse]
    star_scores: dict[str, BehavioralSTARScoreResponse]
    explanation: str
    strengths: list[str]
    weaknesses: list[str]
    suggested_improvements: list[str]
    method: Literal["llm"]


class BehavioralAssessmentAnswerResponse(BaseModel):
    question_id: str
    answer: str
    evaluation: BehavioralAssessmentEvaluationResponse
    created_at: datetime


class CandidateBehavioralAssessmentResponse(BaseModel):
    id: str
    offer_id: str
    offer_title: str
    competency_id: str
    competency_name: str
    status: Literal["in_progress", "completed"]
    questions: list[BehavioralAssessmentQuestionResponse]
    answers: list[BehavioralAssessmentAnswerResponse]
    created_at: datetime
    updated_at: datetime


class CandidateInterviewTranscriptionResponse(BaseModel):
    id: str
    assessment_type: Literal["technical", "behavioral"]
    assessment_id: str
    question_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    transcript: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
