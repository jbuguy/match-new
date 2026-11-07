"""Add onboarding fields to candidate profiles."""

from alembic import op
import sqlalchemy as sa

revision = "0003_candidate_profile_details"
down_revision = "0002_candidate_profiles_job_offers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "candidate_profiles",
        sa.Column("full_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("phone", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("location", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("education", sa.String(length=5000), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("experience", sa.String(length=5000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("candidate_profiles", "experience")
    op.drop_column("candidate_profiles", "education")
    op.drop_column("candidate_profiles", "location")
    op.drop_column("candidate_profiles", "phone")
    op.drop_column("candidate_profiles", "full_name")
