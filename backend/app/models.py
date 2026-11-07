from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(str, Enum):
    CANDIDATE = "candidate"
    EMPLOYER = "employer"
    MINISTRY_ADMIN = "ministry_admin"
    TRAINING_PROVIDER = "training_provider"
    OPERATOR = "operator"


class OrganisationType(str, Enum):
    EMPLOYER = "employer"
    TRAINING_PROVIDER = "training_provider"


class JobApplicationStatus(str, Enum):
    SUBMITTED = "submitted"
    REVIEWING = "reviewing"
    INTERVIEW = "interview"
    HIRED = "hired"
    REJECTED = "rejected"


class CourseStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CourseDeliveryMode(str, Enum):
    ONLINE = "online"
    IN_PERSON = "in_person"
    HYBRID = "hybrid"


class CourseEnrollmentStatus(str, Enum):
    ENROLLED = "enrolled"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        SqlEnum(
            Role,
            name="user_role",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    memberships: Mapped[list["OrganisationMembership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    organisation_type: Mapped[OrganisationType] = mapped_column(
        SqlEnum(
            OrganisationType,
            name="organisation_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    memberships: Mapped[list["OrganisationMembership"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )


class OrganisationMembership(Base):
    __tablename__ = "organisation_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organisation_id", name="uq_membership_user_organisation"),
        Index("ix_membership_organisation_id", "organisation_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organisation_id: Mapped[str] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="memberships")
    organisation: Mapped[Organisation] = relationship(back_populates="memberships")


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    education: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    experience: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CandidateRoadmapStep(Base):
    __tablename__ = "candidate_roadmap_steps"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_key", name="uq_candidate_roadmap_user_skill"),
        Index("ix_candidate_roadmap_steps_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    skill_key: Mapped[str] = mapped_column(String(60), nullable=False)
    skill: Mapped[str] = mapped_column(String(60), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CandidateAssistantSession(Base):
    __tablename__ = "candidate_assistant_sessions"
    __table_args__ = (
        Index("ix_candidate_assistant_sessions_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    messages: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class JobOffer(Base):
    __tablename__ = "job_offers"
    __table_args__ = (Index("ix_job_offers_employer_created", "employer_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    employer_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(5000), nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    required_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class JobApplication(Base):
    __tablename__ = "job_applications"
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_offer_id", name="uq_application_candidate_offer"),
        Index("ix_job_applications_offer_created", "job_offer_id", "created_at"),
        Index("ix_job_applications_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    job_offer_id: Mapped[str] = mapped_column(
        ForeignKey("job_offers.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[JobApplicationStatus] = mapped_column(
        SqlEnum(
            JobApplicationStatus,
            name="job_application_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=JobApplicationStatus.SUBMITTED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class TrainingCourse(Base):
    __tablename__ = "training_courses"
    __table_args__ = (
        Index("ix_training_courses_provider_status", "provider_id", "status"),
        Index("ix_training_courses_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    provider_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(String(5000), nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    delivery_mode: Mapped[CourseDeliveryMode] = mapped_column(
        SqlEnum(
            CourseDeliveryMode,
            name="course_delivery_mode",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        nullable=False,
    )
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    starts_on: Mapped[date | None] = mapped_column(nullable=True)
    ends_on: Mapped[date | None] = mapped_column(nullable=True)
    duration_hours: Mapped[int] = mapped_column(nullable=False)
    capacity: Mapped[int] = mapped_column(nullable=False)
    price_tnd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[CourseStatus] = mapped_column(
        SqlEnum(
            CourseStatus,
            name="course_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=CourseStatus.DRAFT,
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (
        UniqueConstraint("candidate_id", "course_id", name="uq_enrollment_candidate_course"),
        Index("ix_course_enrollments_course_status", "course_id", "status"),
        Index("ix_course_enrollments_candidate_created", "candidate_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("training_courses.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[CourseEnrollmentStatus] = mapped_column(
        SqlEnum(
            CourseEnrollmentStatus,
            name="course_enrollment_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=CourseEnrollmentStatus.ENROLLED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AuditEvent(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_created_at", "created_at"),
        Index("ix_audit_log_action", "action"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_role: Mapped[Role | None] = mapped_column(
        SqlEnum(
            Role,
            name="audit_actor_role",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


@event.listens_for(AuditEvent, "before_update")
def prevent_audit_event_update(mapper: object, connection: object, target: AuditEvent) -> None:
    raise RuntimeError("Audit events are append-only and cannot be updated.")


@event.listens_for(AuditEvent, "before_delete")
def prevent_audit_event_delete(mapper: object, connection: object, target: AuditEvent) -> None:
    raise RuntimeError("Audit events are append-only and cannot be deleted.")
