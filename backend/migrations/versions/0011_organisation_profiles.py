"""Add editable employer organisation profile details."""

from alembic import op
import sqlalchemy as sa

revision = "0011_organisation_profiles"
down_revision = "0010_interview_transcriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organisations", sa.Column("website", sa.String(length=500), nullable=True))
    op.add_column("organisations", sa.Column("sector", sa.String(length=120), nullable=True))
    op.add_column("organisations", sa.Column("size", sa.String(length=80), nullable=True))
    op.add_column("organisations", sa.Column("description", sa.String(length=3000), nullable=True))
    op.add_column("organisations", sa.Column("phone", sa.String(length=40), nullable=True))
    op.add_column("organisations", sa.Column("contact_email", sa.String(length=320), nullable=True))
    op.add_column("organisations", sa.Column("location", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("organisations", "location")
    op.drop_column("organisations", "contact_email")
    op.drop_column("organisations", "phone")
    op.drop_column("organisations", "description")
    op.drop_column("organisations", "size")
    op.drop_column("organisations", "sector")
    op.drop_column("organisations", "website")
