"""Persist candidate interview transcription jobs and transcripts."""

from alembic import op
import sqlalchemy as sa

revision = "0010_interview_transcriptions"
down_revision = "0009_behavioral_assessments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_interview_transcriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("assessment_type", sa.String(length=20), nullable=False),
        sa.Column("assessment_id", sa.String(length=36), nullable=False),
        sa.Column("question_id", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "processing",
                "completed",
                "failed",
                name="interview_transcription_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("transcript", sa.String(length=10000), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candidate_interview_transcriptions_candidate_created",
        "candidate_interview_transcriptions",
        ["candidate_id", "created_at"],
    )
    op.create_index(
        "ix_candidate_interview_transcriptions_assessment_question",
        "candidate_interview_transcriptions",
        ["assessment_type", "assessment_id", "question_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candidate_interview_transcriptions_assessment_question",
        table_name="candidate_interview_transcriptions",
    )
    op.drop_index(
        "ix_candidate_interview_transcriptions_candidate_created",
        table_name="candidate_interview_transcriptions",
    )
    op.drop_table("candidate_interview_transcriptions")
