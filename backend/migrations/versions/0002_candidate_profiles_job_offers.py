"""Add candidate skills and employer job offers."""

from alembic import op
import sqlalchemy as sa

revision = "0002_candidate_profiles_job_offers"
down_revision = "0001_auth_roles_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_profiles",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "job_offers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("employer_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=5000), nullable=False),
        sa.Column("location", sa.String(length=120), nullable=False),
        sa.Column("required_skills", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["employer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_job_offers_employer_created",
        "job_offers",
        ["employer_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_offers_employer_created", table_name="job_offers")
    op.drop_table("job_offers")
    op.drop_table("candidate_profiles")
