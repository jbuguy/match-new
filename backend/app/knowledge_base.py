"""Document ingestion and hybrid retrieval for sourced assistant knowledge."""

import hashlib
import logging
import math
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    delete,
    select,
    text,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.database import Base


logger = logging.getLogger(__name__)
MAX_VECTOR_DIMENSIONS = 2000
POSTGRES_VECTOR_DIMENSIONS = 384
EMBEDDING_BATCH_SIZE = 32


class EmbeddingVector(TypeDecorator[list[float] | None]):
    """Use pgvector in PostgreSQL and JSON arrays in lightweight test databases."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector())
        return dialect.type_descriptor(JSON())


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    external_id: Mapped[str] = mapped_column(String(240), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(300), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(240), nullable=True)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    language: Mapped[str] = mapped_column(String(12), default="und", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    document_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    ingestion_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunks_document_index"),
        Index("ix_knowledge_chunks_document_id", "document_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingVector(), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(240), nullable=True)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")


class KnowledgeBaseError(Exception):
    """Base class for invalid knowledge input or retrieval configuration."""


class EmbeddingServiceError(KnowledgeBaseError):
    """The configured embedding service could not produce a valid response."""


@dataclass(frozen=True)
class KnowledgeHit:
    document_id: str
    chunk_id: str
    title: str
    content: str
    source: str
    source_url: str | None
    category: str | None
    country: str | None
    region: str | None
    published_at: datetime | None
    source_updated_at: datetime | None
    metadata: dict[str, Any]
    score: float


def _integer_setting(name: str, default: int, minimum: int, maximum: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as error:
        raise KnowledgeBaseError(f"{name} must be an integer.") from error
    if not minimum <= value <= maximum:
        raise KnowledgeBaseError(f"{name} must be between {minimum} and {maximum}.")
    return value


def _float_setting(name: str, default: float, minimum: float, maximum: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = float(raw_value)
    except ValueError as error:
        raise KnowledgeBaseError(f"{name} must be a number.") from error
    if not minimum <= value <= maximum:
        raise KnowledgeBaseError(f"{name} must be between {minimum} and {maximum}.")
    return value


def split_text(text_value: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    if chunk_size < 1 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("Chunk size must be positive and overlap must be smaller than size.")
    normalized = re.sub(r"\s+", " ", text_value).strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind(" ", start + chunk_size // 2, end)
            if boundary > start:
                end = boundary
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(normalized):
            break
        start = max(start + 1, end - chunk_overlap)
    return chunks


def _embedding_config() -> tuple[str, str, str | None, int | None] | None:
    base_url = os.getenv("MAHARA_EMBEDDING_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        return None
    provider = os.getenv("MAHARA_EMBEDDING_PROVIDER", "openai-compatible").strip().casefold()
    if provider != "openai-compatible":
        raise EmbeddingServiceError(
            "MAHARA_EMBEDDING_PROVIDER currently supports only 'openai-compatible'."
        )
    model = os.getenv("MAHARA_EMBEDDING_MODEL", "").strip()
    if not model:
        raise EmbeddingServiceError(
            "MAHARA_EMBEDDING_MODEL is required when the embedding service is configured."
        )
    try:
        endpoint = httpx.URL(f"{base_url}/v1/embeddings")
    except httpx.InvalidURL as error:
        raise EmbeddingServiceError("MAHARA_EMBEDDING_BASE_URL must be a valid HTTP URL.") from error
    if endpoint.scheme not in {"http", "https"} or not endpoint.host:
        raise EmbeddingServiceError("MAHARA_EMBEDDING_BASE_URL must be a valid HTTP URL.")
    api_key = os.getenv("MAHARA_EMBEDDING_API_KEY", "").strip() or None
    dimensions_setting = os.getenv("MAHARA_EMBEDDING_DIMENSIONS", "").strip()
    dimensions = POSTGRES_VECTOR_DIMENSIONS
    if dimensions_setting:
        try:
            configured_dimensions = int(dimensions_setting)
        except ValueError as error:
            raise EmbeddingServiceError(
                "MAHARA_EMBEDDING_DIMENSIONS must be an integer."
            ) from error
        if not 1 <= configured_dimensions <= MAX_VECTOR_DIMENSIONS:
            raise EmbeddingServiceError(
                f"MAHARA_EMBEDDING_DIMENSIONS must be between 1 and {MAX_VECTOR_DIMENSIONS}."
            )
        if configured_dimensions != POSTGRES_VECTOR_DIMENSIONS:
            raise EmbeddingServiceError(
                "MAHARA_EMBEDDING_DIMENSIONS must be 384 to match the pgvector schema."
            )
    return str(endpoint), model, api_key, dimensions


def embedding_service_configured() -> bool:
    return bool(os.getenv("MAHARA_EMBEDDING_BASE_URL", "").strip())


async def generate_embeddings(texts: Sequence[str]) -> tuple[list[list[float]], str]:
    if not texts:
        return [], ""
    config = _embedding_config()
    if config is None:
        raise EmbeddingServiceError("The embedding service is not configured.")
    endpoint, model, api_key, expected_dimensions = config
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    embeddings: list[list[float] | None] = [None] * len(texts)
    timeout = _float_setting("MAHARA_EMBEDDING_TIMEOUT_SECONDS", 30.0, 0.1, 300.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for batch_start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
                batch = list(texts[batch_start : batch_start + EMBEDDING_BATCH_SIZE])
                payload = {"model": model, "input": batch}
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                body = response.json()
                data = body.get("data") if isinstance(body, dict) else None
                if not isinstance(data, list) or len(data) != len(batch):
                    raise EmbeddingServiceError(
                        "Embedding service returned a mismatched number of vectors."
                    )
                for item in data:
                    if not isinstance(item, dict):
                        raise EmbeddingServiceError(
                            "Embedding service returned an invalid vector entry."
                        )
                    index = item.get("index")
                    vector = item.get("embedding")
                    if (
                        isinstance(index, bool)
                        or not isinstance(index, int)
                        or not 0 <= index < len(batch)
                        or not isinstance(vector, list)
                        or not vector
                        or any(
                            isinstance(value, bool)
                            or not isinstance(value, (int, float))
                            or not math.isfinite(value)
                            for value in vector
                        )
                    ):
                        raise EmbeddingServiceError(
                            "Embedding service returned an invalid vector."
                        )
                    if expected_dimensions is not None and len(vector) != expected_dimensions:
                        raise EmbeddingServiceError(
                            "Embedding vector length differs from "
                            "MAHARA_EMBEDDING_DIMENSIONS."
                        )
                    if len(vector) > MAX_VECTOR_DIMENSIONS:
                        raise EmbeddingServiceError(
                            f"Embedding vectors cannot exceed {MAX_VECTOR_DIMENSIONS} values."
                        )
                    output_index = batch_start + index
                    if embeddings[output_index] is not None:
                        raise EmbeddingServiceError(
                            "Embedding service returned a duplicate vector index."
                        )
                    embeddings[output_index] = [float(value) for value in vector]
    except EmbeddingServiceError:
        raise
    except httpx.TimeoutException as error:
        logger.warning("Embedding service timed out.")
        raise EmbeddingServiceError("The embedding service timed out.") from error
    except httpx.HTTPStatusError as error:
        logger.error("Embedding service returned HTTP %s.", error.response.status_code)
        raise EmbeddingServiceError("The embedding service rejected the request.") from error
    except (httpx.RequestError, ValueError) as error:
        logger.error("Could not reach or decode the embedding service (%s).", type(error).__name__)
        raise EmbeddingServiceError("The embedding service is unavailable.") from error

    if any(vector is None for vector in embeddings):
        raise EmbeddingServiceError("Embedding service omitted one or more vectors.")
    result = [vector for vector in embeddings if vector is not None]
    dimensions = len(result[0])
    if any(len(vector) != dimensions for vector in result):
        raise EmbeddingServiceError("Embedding service returned inconsistent vector lengths.")
    return result, model


def _required_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} cannot be empty.")
    return normalized


def _source_updated_at(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


async def ingest_document(
    session: Session,
    *,
    external_id: str,
    title: str,
    content: str,
    source: str,
    source_url: str | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    country: str | None = None,
    region: str | None = None,
    occupation: str | None = None,
    skills: list[str] | None = None,
    language: str = "und",
    published_at: datetime | None = None,
    source_updated_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> KnowledgeDocument:
    external_id = _required_text(external_id, "external_id")
    title = _required_text(title, "title")
    content = _required_text(content, "content")
    source = _required_text(source, "source")
    content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    existing = session.scalar(
        select(KnowledgeDocument).where(KnowledgeDocument.external_id == external_id)
    )
    if (
        existing is not None
        and existing.content_sha256 == content_sha256
        and existing.status == "ready"
    ):
        existing.title = title
        existing.source = source
        existing.source_url = source_url
        existing.category = category
        existing.subcategory = subcategory
        existing.country = country
        existing.region = region
        existing.occupation = occupation
        existing.skills = skills or []
        existing.language = language
        existing.published_at = published_at
        existing.source_updated_at = _source_updated_at(source_updated_at)
        existing.document_metadata = metadata or {}
        existing.ingestion_error = None
        if existing.status == "failed":
            existing.status = "ready"
        session.commit()
        return existing

    chunk_size = _integer_setting("MAHARA_RAG_CHUNK_SIZE", 1000, 100, 10000)
    chunk_overlap = _integer_setting(
        "MAHARA_RAG_CHUNK_OVERLAP", 120, 0, chunk_size - 1
    )
    chunks = split_text(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    document = existing or KnowledgeDocument(
        external_id=external_id,
        title=title,
        content=content,
        source=source,
        content_sha256=content_sha256,
        status="pending",
    )
    document.title = title
    document.content = content
    document.source = source
    document.source_url = source_url
    document.category = category
    document.subcategory = subcategory
    document.country = country
    document.region = region
    document.occupation = occupation
    document.skills = skills or []
    document.language = language
    document.published_at = published_at
    document.source_updated_at = _source_updated_at(source_updated_at)
    document.document_metadata = metadata or {}
    document.content_sha256 = content_sha256
    document.status = "pending"
    document.ingestion_error = None
    session.add(document)
    session.commit()

    embeddings: list[list[float]] | None = None
    embedding_model: str | None = None
    if chunks and embedding_service_configured():
        try:
            embeddings, embedding_model = await generate_embeddings(chunks)
        except EmbeddingServiceError as error:
            document.status = "failed"
            document.ingestion_error = str(error)[:2000]
            session.commit()
            raise

    session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))
    for index, chunk_content in enumerate(chunks):
        embedding = embeddings[index] if embeddings is not None else None
        session.add(
            KnowledgeChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk_content,
                content_sha256=hashlib.sha256(chunk_content.encode("utf-8")).hexdigest(),
                embedding=embedding,
                embedding_model=embedding_model,
                embedding_dimensions=len(embedding) if embedding is not None else None,
            )
        )
    document.status = "ready"
    document.ingestion_error = None
    session.commit()
    session.refresh(document)
    return document


def ingest_file_content(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix in {".txt", ".md", ".markdown"}:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise KnowledgeBaseError(f"Could not read UTF-8 document {path.name}.") from error
    if suffix == ".pdf":
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
        except (OSError, ValueError, PdfReadError) as error:
            raise KnowledgeBaseError(f"Could not extract text from PDF {path.name}.") from error
        return "\n\n".join(pages)
    raise KnowledgeBaseError("Only UTF-8 text, Markdown, and PDF documents are supported.")


async def ingest_file(
    session: Session,
    path: Path,
    *,
    external_id: str,
    source: str,
    title: str | None = None,
    source_url: str | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    country: str | None = None,
    region: str | None = None,
    occupation: str | None = None,
    skills: list[str] | None = None,
    language: str = "und",
    published_at: datetime | None = None,
    source_updated_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> KnowledgeDocument:
    content = ingest_file_content(path)
    file_metadata = read_document_metadata(path)
    return await ingest_document(
        session,
        external_id=external_id,
        title=title or path.stem,
        content=content,
        source=source,
        source_url=source_url,
        category=category,
        subcategory=subcategory,
        country=country,
        region=region,
        occupation=occupation,
        skills=skills,
        language=language,
        published_at=published_at,
        source_updated_at=source_updated_at,
        metadata={**file_metadata, **(metadata or {})},
    )


def delete_document(session: Session, external_id: str) -> bool:
    document = session.scalar(
        select(KnowledgeDocument).where(KnowledgeDocument.external_id == external_id)
    )
    if document is None:
        return False
    session.delete(document)
    session.commit()
    return True


def _query_terms(query: str) -> list[str]:
    terms = re.findall(r"[\w]{2,}", query.casefold(), flags=re.UNICODE)
    return list(dict.fromkeys(terms))


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        return -1.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return -1.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def _hit_from_row(
    row: Any,
    score: float,
) -> KnowledgeHit:
    document = row.document if hasattr(row, "document") else row[1]
    chunk = row.chunk if hasattr(row, "chunk") else row[0]
    return KnowledgeHit(
        document_id=document.external_id,
        chunk_id=chunk.id,
        title=document.title,
        content=chunk.content,
        source=document.source,
        source_url=document.source_url,
        category=document.category,
        country=document.country,
        region=document.region,
        published_at=document.published_at,
        source_updated_at=document.source_updated_at,
        metadata=document.document_metadata or {},
        score=score,
    )


def _sqlite_hybrid_search(
    session: Session,
    *,
    query: str,
    query_embedding: list[float] | None,
    embedding_model: str | None,
    top_k: int,
    similarity_threshold: float,
    category: str | None,
    country: str | None,
) -> list[KnowledgeHit]:
    statement = (
        select(KnowledgeChunk, KnowledgeDocument)
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .where(KnowledgeDocument.status == "ready")
    )
    if category:
        statement = statement.where(KnowledgeDocument.category == category)
    if country:
        statement = statement.where(KnowledgeDocument.country == country)
    rows = session.execute(statement).all()
    terms = _query_terms(query)
    candidates: list[tuple[float, KnowledgeHit]] = []
    for chunk, document in rows:
        content_lower = chunk.content.casefold()
        matched_terms = sum(1 for term in terms if term in content_lower)
        keyword_score = matched_terms / len(terms) if terms else 0.0
        vector_score = -1.0
        if (
            query_embedding is not None
            and chunk.embedding is not None
            and chunk.embedding_model == embedding_model
        ):
            vector_score = _cosine_similarity(query_embedding, chunk.embedding)
        if vector_score < similarity_threshold and keyword_score == 0:
            continue
        combined_score = max(0.0, vector_score) * 0.7 + keyword_score * 0.3
        if vector_score < similarity_threshold:
            combined_score = keyword_score * 0.3
        candidates.append(
            (combined_score, _hit_from_row((chunk, document), combined_score))
        )
    candidates.sort(key=lambda result: result[0], reverse=True)
    return [hit for _, hit in candidates[:top_k]]


def _postgres_hybrid_search(
    session: Session,
    *,
    query: str,
    query_embedding: list[float] | None,
    embedding_model: str | None,
    top_k: int,
    similarity_threshold: float,
    category: str | None,
    country: str | None,
) -> list[KnowledgeHit]:
    filters = ["d.status = 'ready'"]
    params: dict[str, Any] = {"limit": max(top_k * 4, 20)}
    if category:
        filters.append("d.category = :category")
        params["category"] = category
    if country:
        filters.append("d.country = :country")
        params["country"] = country
    where_clause = " AND ".join(filters)
    ranks: dict[str, dict[str, Any]] = {}
    timeout_seconds = _float_setting(
        "MAHARA_RAG_RETRIEVAL_TIMEOUT_SECONDS", 5.0, 0.1, 120.0
    )
    session.execute(
        text("SELECT set_config('statement_timeout', :timeout, true)"),
        {"timeout": f"{round(timeout_seconds * 1000)}ms"},
    )

    if query_embedding is not None and embedding_model is not None:
        params.update(
            {
                "embedding": "[" + ",".join(format(value, ".9g") for value in query_embedding) + "]",
                "embedding_model": embedding_model,
            }
        )
        vector_rows = session.execute(
            text(
                f"""
                SELECT c.id AS chunk_id, c.content, d.external_id AS document_id,
                       d.title, d.source, d.source_url, d.category, d.country,
                       d.region, d.published_at, d.source_updated_at,
                       d.document_metadata, 1 - (c.embedding <=> CAST(:embedding AS vector))
                           AS similarity
                FROM knowledge_chunks c
                JOIN knowledge_documents d ON d.id = c.document_id
                WHERE {where_clause}
                  AND c.embedding IS NOT NULL
                  AND c.embedding_model = :embedding_model
                  AND c.embedding_dimensions = :embedding_dimensions
                ORDER BY c.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
                """
            ),
            {
                **params,
                "embedding_dimensions": len(query_embedding),
            },
        ).mappings()
        vector_rank = 0
        for row in vector_rows:
            similarity = float(row["similarity"])
            if similarity < similarity_threshold:
                continue
            vector_rank += 1
            ranks[row["chunk_id"]] = {
                "row": row,
                "vector_rank": vector_rank,
                "keyword_rank": None,
                "similarity": similarity,
            }

    terms = _query_terms(query)
    if terms:
        tsquery = " | ".join(f"{term}:*" for term in terms)
        keyword_rows = session.execute(
            text(
                f"""
                SELECT c.id AS chunk_id, c.content, d.external_id AS document_id,
                       d.title, d.source, d.source_url, d.category, d.country,
                       d.region, d.published_at, d.source_updated_at,
                       d.document_metadata,
                       ts_rank_cd(to_tsvector('simple', c.content),
                                  to_tsquery('simple', :terms)) AS keyword_score
                FROM knowledge_chunks c
                JOIN knowledge_documents d ON d.id = c.document_id
                WHERE {where_clause}
                  AND to_tsvector('simple', c.content) @@ to_tsquery('simple', :terms)
                ORDER BY keyword_score DESC
                LIMIT :limit
                """
            ),
            {**params, "terms": tsquery},
        ).mappings()
        for rank, row in enumerate(keyword_rows, start=1):
            current = ranks.get(row["chunk_id"])
            if current is None:
                current = {
                    "row": row,
                    "vector_rank": None,
                    "keyword_rank": rank,
                    "similarity": None,
                }
                ranks[row["chunk_id"]] = current
            else:
                current["keyword_rank"] = rank
                current["row"] = row

    vector_weight = _float_setting("MAHARA_RAG_VECTOR_WEIGHT", 0.7, 0.0, 1.0)
    keyword_weight = 1.0 - vector_weight
    scored: list[tuple[float, KnowledgeHit]] = []
    for result in ranks.values():
        vector_rank = result["vector_rank"]
        keyword_rank = result["keyword_rank"]
        score = 0.0
        if vector_rank is not None:
            score += vector_weight / (60 + vector_rank)
        if keyword_rank is not None:
            score += keyword_weight / (60 + keyword_rank)
        row = result["row"]
        scored.append(
            (
                score,
                KnowledgeHit(
                    document_id=row["document_id"],
                    chunk_id=row["chunk_id"],
                    title=row["title"],
                    content=row["content"],
                    source=row["source"],
                    source_url=row["source_url"],
                    category=row["category"],
                    country=row["country"],
                    region=row["region"],
                    published_at=row["published_at"],
                    source_updated_at=row["source_updated_at"],
                    metadata=row["document_metadata"] or {},
                    score=score,
                ),
            )
        )
    scored.sort(key=lambda item: item[0], reverse=True)
    return [hit for _, hit in scored[:top_k]]


async def search_knowledge(
    session: Session,
    query: str,
    *,
    top_k: int | None = None,
    similarity_threshold: float | None = None,
    category: str | None = None,
    country: str | None = None,
) -> list[KnowledgeHit]:
    if not query.strip():
        return []
    result_limit = (
        _integer_setting("MAHARA_RAG_TOP_K", 5, 1, 20)
        if top_k is None
        else top_k
    )
    if not 1 <= result_limit <= 20:
        raise KnowledgeBaseError("top_k must be between 1 and 20.")
    threshold = (
        similarity_threshold
        if similarity_threshold is not None
        else _float_setting("MAHARA_RAG_SIMILARITY_THRESHOLD", 0.3, -1.0, 1.0)
    )
    if not -1.0 <= threshold <= 1.0:
        raise KnowledgeBaseError("Similarity threshold must be between -1 and 1.")

    query_embedding: list[float] | None = None
    embedding_model: str | None = None
    if embedding_service_configured():
        try:
            embeddings, embedding_model = await generate_embeddings([query])
            query_embedding = embeddings[0]
        except EmbeddingServiceError as error:
            logger.warning(
                "Semantic retrieval failed; falling back to keyword search (%s).",
                error,
            )

    if session.get_bind().dialect.name == "postgresql":
        return _postgres_hybrid_search(
            session,
            query=query,
            query_embedding=query_embedding,
            embedding_model=embedding_model,
            top_k=result_limit,
            similarity_threshold=threshold,
            category=category,
            country=country,
        )
    return _sqlite_hybrid_search(
        session,
        query=query,
        query_embedding=query_embedding,
        embedding_model=embedding_model,
        top_k=result_limit,
        similarity_threshold=threshold,
        category=category,
        country=country,
    )


def read_document_metadata(path: Path) -> dict[str, Any]:
    return {
        "filename": path.name,
        "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "file_modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
    }
