from datetime import datetime
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import Role


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
