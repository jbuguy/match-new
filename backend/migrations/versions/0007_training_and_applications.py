"""Persist training courses, enrollments, and job applications."""

from alembic import op
import sqlalchemy as sa

revision = "0007_training_and_applications"
down_revision = "0006_hybrid_knowledge_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_applications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("job_offer_id", sa.String(length=36), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "submitted",
                "reviewing",
                "interview",
                "hired",
                "rejected",
                name="job_application_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_offer_id"], ["job_offers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id", "job_offer_id", name="uq_application_candidate_offer"),
    )
    op.create_index(
        "ix_job_applications_offer_created",
        "job_applications",
        ["job_offer_id", "created_at"],
    )
    op.create_index(
        "ix_job_applications_status_created",
        "job_applications",
        ["status", "created_at"],
    )

    op.create_table(
        "training_courses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.String(length=5000), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column(
            "delivery_mode",
            sa.Enum(
                "online",
                "in_person",
                "hybrid",
                name="course_delivery_mode",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("duration_hours", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("price_tnd", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "published",
                "archived",
                name="course_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["provider_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_training_courses_provider_status",
        "training_courses",
        ["provider_id", "status"],
    )
    op.create_index(
        "ix_training_courses_status_created",
        "training_courses",
        ["status", "created_at"],
    )

    op.create_table(
        "course_enrollments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("course_id", sa.String(length=36), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "enrolled",
                "completed",
                "withdrawn",
                name="course_enrollment_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["training_courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id", "course_id", name="uq_enrollment_candidate_course"),
    )
    op.create_index(
        "ix_course_enrollments_course_status",
        "course_enrollments",
        ["course_id", "status"],
    )
    op.create_index(
        "ix_course_enrollments_candidate_created",
        "course_enrollments",
        ["candidate_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_course_enrollments_candidate_created",
        table_name="course_enrollments",
    )
    op.drop_index(
        "ix_course_enrollments_course_status",
        table_name="course_enrollments",
    )
    op.drop_table("course_enrollments")
    op.drop_index("ix_training_courses_status_created", table_name="training_courses")
    op.drop_index("ix_training_courses_provider_status", table_name="training_courses")
    op.drop_table("training_courses")
    op.drop_index("ix_job_applications_status_created", table_name="job_applications")
    op.drop_index("ix_job_applications_offer_created", table_name="job_applications")
    op.drop_table("job_applications")
