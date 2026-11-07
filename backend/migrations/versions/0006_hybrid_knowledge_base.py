"""Add sourced assistant knowledge documents and vector-searchable chunks."""

from alembic import op
import sqlalchemy as sa
from typing import Any

revision = "0006_hybrid_knowledge_base"
down_revision = "0005_candidate_roadmap_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect_name = op.get_context().dialect.name
    embedding_type: sa.types.TypeEngine[Any] = (
        sa.Text() if dialect_name == "postgresql" else sa.JSON()
    )
    if dialect_name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("external_id", sa.String(length=240), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=300), nullable=False),
        sa.Column("source_url", sa.String(length=2000), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("subcategory", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=80), nullable=True),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("occupation", sa.String(length=240), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("language", sa.String(length=12), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("document_metadata", sa.JSON(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("ingestion_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_knowledge_documents_category", "knowledge_documents", ["category"])
    op.create_index("ix_knowledge_documents_country", "knowledge_documents", ["country"])
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("embedding", embedding_type, nullable=True),
        sa.Column("embedding_model", sa.String(length=240), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunks_document_index"),
    )
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    if dialect_name == "postgresql":
        op.execute(
            "ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(384) "
            "USING embedding::vector(384)"
        )
        op.execute(
            "CREATE INDEX ix_knowledge_chunks_embedding_hnsw "
            "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
        )
        op.execute(
            "CREATE INDEX ix_knowledge_chunks_content_fts "
            "ON knowledge_chunks USING gin (to_tsvector('simple', content))"
        )


def downgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP INDEX ix_knowledge_chunks_content_fts")
        op.execute("DROP INDEX ix_knowledge_chunks_embedding_hnsw")
    op.drop_index("ix_knowledge_chunks_document_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index("ix_knowledge_documents_country", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_category", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
