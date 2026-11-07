"""Persist candidate roadmap step progress."""

from alembic import op
import sqlalchemy as sa

revision = "0005_candidate_roadmap_progress"
down_revision = "0004_candidate_assistant_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_roadmap_steps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("skill_key", sa.String(length=60), nullable=False),
        sa.Column("skill", sa.String(length=60), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "skill_key", name="uq_candidate_roadmap_user_skill"),
    )
    op.create_index(
        "ix_candidate_roadmap_steps_user_id",
        "candidate_roadmap_steps",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_candidate_roadmap_steps_user_id", table_name="candidate_roadmap_steps")
    op.drop_table("candidate_roadmap_steps")
