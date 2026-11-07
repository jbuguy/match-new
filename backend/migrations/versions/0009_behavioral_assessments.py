"""Persist candidate behavioral interview assessments and feedback."""

from alembic import op
import sqlalchemy as sa

revision = "0009_behavioral_assessments"
down_revision = "0008_technical_assessments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_behavioral_assessments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("job_offer_id", sa.String(length=36), nullable=False),
        sa.Column("competency_id", sa.String(length=60), nullable=False),
        sa.Column("competency_name", sa.String(length=120), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "in_progress",
                "completed",
                name="behavioral_assessment_status",
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
    )
    op.create_index(
        "ix_candidate_behavioral_assessments_candidate_created",
        "candidate_behavioral_assessments",
        ["candidate_id", "created_at"],
    )
    op.create_table(
        "candidate_behavioral_assessment_answers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("assessment_id", sa.String(length=36), nullable=False),
        sa.Column("question_id", sa.String(length=20), nullable=False),
        sa.Column("answer", sa.String(length=10000), nullable=False),
        sa.Column("evaluation", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["candidate_behavioral_assessments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_id",
            "question_id",
            name="uq_behavioral_assessment_answer_question",
        ),
    )
    op.create_index(
        "ix_candidate_behavioral_assessment_answers_assessment",
        "candidate_behavioral_assessment_answers",
        ["assessment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candidate_behavioral_assessment_answers_assessment",
        table_name="candidate_behavioral_assessment_answers",
    )
    op.drop_table("candidate_behavioral_assessment_answers")
    op.drop_index(
        "ix_candidate_behavioral_assessments_candidate_created",
        table_name="candidate_behavioral_assessments",
    )
    op.drop_table("candidate_behavioral_assessments")
