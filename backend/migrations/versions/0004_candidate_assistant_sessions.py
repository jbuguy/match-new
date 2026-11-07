"""Persist candidate assistant conversation sessions."""

from alembic import op
import sqlalchemy as sa

revision = "0004_candidate_assistant_sessions"
down_revision = "0003_candidate_profile_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_assistant_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("messages", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candidate_assistant_sessions_user_updated",
        "candidate_assistant_sessions",
        ["user_id", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candidate_assistant_sessions_user_updated",
        table_name="candidate_assistant_sessions",
    )
    op.drop_table("candidate_assistant_sessions")
